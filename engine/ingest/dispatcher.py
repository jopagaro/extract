"""
Ingest dispatcher — the main entry point for ingesting raw files into a project.

The dispatcher:
1. Scans the project raw/ directory for files not yet in the file registry
2. Routes each file to the appropriate ingest category based on extension
   and parent folder name
3. Records the result in the file registry and returns an IngestResult

Routing logic (see _route_file for details):
- Parent folder names like "collars", "assays", "surveys" provide strong hints
- File extensions provide a secondary signal
- Photo, video, and document formats are routed to their own categories
- Unknown files are recorded but not parsed
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.core.ids import run_id as make_run_id
from engine.core.logging import get_logger
from engine.core.paths import project_raw
from engine.io.file_registry import (
    FileRegistryEntry,
    get_new_files,
    is_already_ingested,
    load_registry,
    register_file,
    save_registry,
)

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class IngestResult:
    """Summary of a single ingest run."""

    project_id: str
    """The project that was ingested."""

    run_id: str
    """The run ID for this ingest."""

    files_found: int = 0
    """Total number of raw files found (new + previously ingested)."""

    files_ingested: int = 0
    """Number of new files successfully ingested in this run."""

    files_skipped: int = 0
    """Files that were already in the registry (skipped)."""

    files_failed: int = 0
    """Files that raised an error during ingest."""

    warnings: list[str] = field(default_factory=list)
    """Non-fatal warnings accumulated during ingest."""

    errors: list[str] = field(default_factory=list)
    """Error messages for files that failed."""

    ingested_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    """ISO-8601 timestamp when this ingest run completed."""

    entries: list[FileRegistryEntry] = field(default_factory=list)
    """The new FileRegistryEntry objects created during this run."""


# ---------------------------------------------------------------------------
# File routing
# ---------------------------------------------------------------------------

# Folder-name hints → ingest category
_FOLDER_CATEGORY_MAP: dict[str, str] = {
    # Drillhole sub-folders
    "collars": "drillhole_collar",
    "collar": "drillhole_collar",
    "drillhole_collars": "drillhole_collar",
    "assays": "drillhole_assay",
    "assay": "drillhole_assay",
    "geochemistry": "drillhole_assay",
    "geochem": "drillhole_assay",
    "surveys": "drillhole_survey",
    "survey": "drillhole_survey",
    "downhole_survey": "drillhole_survey",
    "lithology": "drillhole_lithology",
    "lith": "drillhole_lithology",
    "geotech": "drillhole_geotech",
    "qaqc": "drillhole_qaqc",
    "qa_qc": "drillhole_qaqc",
    "intervals": "drillhole_assay",
    # Technical reports
    "reports": "technical_report",
    "technical_reports": "technical_report",
    "documents": "technical_report",
    "docs": "technical_report",
    "pdfs": "technical_report",
    "ni43-101": "technical_report",
    "jorc": "technical_report",
    # CAD
    "cad": "cad",
    "dwg": "cad",
    "dxf": "cad",
    "3d": "cad",
    "models": "cad",
    # GIS
    "gis": "gis",
    "spatial": "gis",
    "shapefiles": "gis",
    "geotiff": "gis",
    "raster": "gis",
    # Financial
    "financials": "financial",
    "financial": "financial",
    "economics": "financial",
    # Photos
    "photos": "photo",
    "photo": "photo",
    "images": "photo",
    "photography": "photo",
    # Video
    "video": "video",
    "videos": "video",
    "footage": "video",
}

# Extension → default category (used when folder hint is absent)
_EXTENSION_CATEGORY_MAP: dict[str, str] = {
    # Drillhole data
    ".csv": "drillhole_assay",   # default — folder hint overrides
    # Excel
    ".xlsx": "excel_data",
    ".xls": "excel_data",
    # Technical reports
    ".pdf": "technical_report",
    ".docx": "technical_report",
    ".doc": "technical_report",
    ".pptx": "technical_report",
    ".ppt": "technical_report",
    # CAD
    ".dxf": "cad",
    ".dwg": "cad",
    ".obj": "cad",
    ".stl": "cad",
    ".gltf": "cad",
    ".glb": "cad",
    ".omf": "cad",
    # GIS
    ".geojson": "gis",
    ".json": "gis",
    ".shp": "gis",
    ".gpkg": "gis",
    ".kml": "gis",
    ".kmz": "gis",
    ".tif": "gis",
    ".tiff": "gis",
    # Photos
    ".jpg": "photo",
    ".jpeg": "photo",
    ".png": "photo",
    ".heic": "photo",
    ".bmp": "photo",
    ".tga": "photo",
    # Video
    ".mp4": "video",
    ".mov": "video",
    ".avi": "video",
    ".mkv": "video",
    ".wmv": "video",
    # YAML / JSON config / data
    ".yaml": "config",
    ".yml": "config",
}


def _route_file(file_path: Path, project_id: str) -> str:
    """
    Determine the ingest category for a file.

    Routing priority:
    1. Parent folder name (e.g. ``collars/`` → ``"drillhole_collar"``)
    2. File extension

    A folder hint takes precedence because the same extension (e.g. ``.csv``)
    can represent very different datasets depending on where it lives.

    Parameters
    ----------
    file_path:
        Absolute path to the file.
    project_id:
        Project identifier (used to resolve raw/ root for relative path).

    Returns
    -------
    str
        Category string, e.g. ``"drillhole_collar"``, ``"technical_report"``,
        ``"cad"``, ``"gis"``, ``"photo"``, ``"video"``, ``"unknown"``.
    """
    # Walk up the path's parents (relative to raw/) for folder hints
    raw_root = project_raw(project_id)
    try:
        rel = file_path.relative_to(raw_root)
        parts = rel.parts[:-1]  # exclude the filename itself
    except ValueError:
        parts = file_path.parts[:-1]

    for part in reversed(parts):
        folder_lower = part.lower().replace("-", "_").replace(" ", "_")
        if folder_lower in _FOLDER_CATEGORY_MAP:
            return _FOLDER_CATEGORY_MAP[folder_lower]

    # Fall back to extension
    ext = file_path.suffix.lower()
    return _EXTENSION_CATEGORY_MAP.get(ext, "unknown")


# ---------------------------------------------------------------------------
# Single-file ingest
# ---------------------------------------------------------------------------

def ingest_file(
    project_id: str,
    file_path: Path,
    run_id: str,
) -> dict[str, Any]:
    """
    Ingest a single raw file into the project.

    Routes the file to its category, creates a :class:`FileRegistryEntry`,
    and returns a result dict. Does not persist the registry — the caller
    is responsible for calling :func:`save_registry` after the full run.

    Parameters
    ----------
    project_id:
        Project identifier.
    file_path:
        Absolute path to the raw file.
    run_id:
        ID of the current ingest run.

    Returns
    -------
    dict
        Keys: ``status`` (``"ingested"`` or ``"failed"``), ``category``,
        ``entry`` (:class:`FileRegistryEntry` or None), ``error`` (str or None).
    """
    category = _route_file(file_path, project_id)
    try:
        entry = register_file(project_id, file_path, run_id, category=category)
        log.info(
            "Ingested %s → category=%s source_id=%s",
            file_path.name, category, entry.source_id,
        )
        return {
            "status": "ingested",
            "category": category,
            "entry": entry,
            "error": None,
        }
    except Exception as exc:
        log.warning("Failed to ingest %s: %s", file_path, exc)
        return {
            "status": "failed",
            "category": category,
            "entry": None,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Full project ingest
# ---------------------------------------------------------------------------

def ingest_project(
    project_id: str,
    run_id: str | None = None,
) -> IngestResult:
    """
    Scan all raw/ subdirectories and ingest new files into the project.

    Already-ingested files (matched by SHA-256 hash) are skipped.
    The file registry is updated atomically after all files are processed.

    Parameters
    ----------
    project_id:
        Project identifier.
    run_id:
        ID for this ingest run. If None, a new run ID is generated.

    Returns
    -------
    IngestResult
    """
    if run_id is None:
        run_id = make_run_id(project_id)

    log.info("Starting ingest for project=%s run=%s", project_id, run_id)

    result = IngestResult(project_id=project_id, run_id=run_id)

    # Load existing registry so we can preserve prior entries
    existing_entries = load_registry(project_id)
    known_hashes = {e.file_hash for e in existing_entries}
    new_entries: list[FileRegistryEntry] = []

    # Find all files in raw/
    raw_root = project_raw(project_id)
    if not raw_root.exists():
        result.warnings.append(
            f"Raw directory does not exist: {raw_root}. "
            "Nothing to ingest."
        )
        return result

    all_files = [
        f for f in sorted(raw_root.rglob("*"))
        if f.is_file() and not f.name.startswith(".")
    ]
    result.files_found = len(all_files)

    for file_path in all_files:
        # Check if already ingested (by hash)
        try:
            from engine.core.hashing import hash_file
            fhash = hash_file(file_path)
        except Exception as exc:
            result.files_failed += 1
            result.errors.append(f"Could not hash {file_path}: {exc}")
            continue

        if fhash in known_hashes:
            result.files_skipped += 1
            log.debug("Skipping already-ingested file: %s", file_path.name)
            continue

        file_result = ingest_file(project_id, file_path, run_id)

        if file_result["status"] == "ingested":
            result.files_ingested += 1
            entry = file_result["entry"]
            new_entries.append(entry)
            result.entries.append(entry)
            known_hashes.add(entry.file_hash)
        else:
            result.files_failed += 1
            result.errors.append(
                f"{file_path.name}: {file_result['error']}"
            )

    # Persist updated registry (existing + new)
    if new_entries:
        all_entries = existing_entries + new_entries
        try:
            save_registry(project_id, all_entries)
            log.info(
                "Registry updated: %d total entries (%d new)",
                len(all_entries), len(new_entries),
            )
        except Exception as exc:
            result.errors.append(f"Failed to save registry: {exc}")
            log.error("Failed to save registry: %s", exc)

    result.ingested_at = datetime.now(timezone.utc).isoformat()
    log.info(
        "Ingest complete — found=%d ingested=%d skipped=%d failed=%d",
        result.files_found,
        result.files_ingested,
        result.files_skipped,
        result.files_failed,
    )
    return result

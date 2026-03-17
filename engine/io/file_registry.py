"""
File registry — tracks which raw files have been ingested into a project.

The registry is stored as a JSON array in:
    <project_normalized>/metadata/source_manifest.json

Each entry records the file path (relative to raw/), its SHA-256 hash,
size, extension, ingest category, and when it was ingested.

Usage pattern:
    1. On each ingest run, call get_new_files() to find files not yet registered.
    2. For each new file, call register_file() to create a FileRegistryEntry.
    3. When done, call save_registry() to persist the updated list.
    4. is_already_ingested() can be used as a quick guard before parsing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.core.hashing import hash_file
from engine.core.ids import source_id
from engine.core.paths import project_normalized, project_raw
from engine.core.manifests import read_json, write_json


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class FileRegistryEntry:
    """A record of a raw file that has been ingested into the project."""

    source_id: str
    """Stable ID derived from file path + hash (e.g. ``src_a3f2b1c4``)."""

    file_path: str
    """Path relative to the project ``raw/`` directory (POSIX separators)."""

    file_hash: str
    """SHA-256 hex digest of the file contents at time of ingest."""

    file_size_bytes: int
    """File size in bytes at time of ingest."""

    extension: str
    """Lowercase file extension including leading dot (e.g. ``".csv"``)."""

    category: str
    """
    Ingest category assigned by the dispatcher, e.g.
    ``"drillhole_collar"``, ``"technical_report"``, ``"gis"``.
    """

    ingested_at: str
    """ISO-8601 UTC timestamp when this entry was created."""

    run_id: str
    """ID of the ingest run that created this entry."""


# ---------------------------------------------------------------------------
# Registry serialisation helpers
# ---------------------------------------------------------------------------

def _entry_to_dict(entry: FileRegistryEntry) -> dict[str, Any]:
    return {
        "source_id": entry.source_id,
        "file_path": entry.file_path,
        "file_hash": entry.file_hash,
        "file_size_bytes": entry.file_size_bytes,
        "extension": entry.extension,
        "category": entry.category,
        "ingested_at": entry.ingested_at,
        "run_id": entry.run_id,
    }


def _entry_from_dict(d: dict[str, Any]) -> FileRegistryEntry:
    return FileRegistryEntry(
        source_id=d.get("source_id", ""),
        file_path=d.get("file_path", ""),
        file_hash=d.get("file_hash", ""),
        file_size_bytes=int(d.get("file_size_bytes", 0)),
        extension=d.get("extension", ""),
        category=d.get("category", "unknown"),
        ingested_at=d.get("ingested_at", ""),
        run_id=d.get("run_id", ""),
    )


def _registry_path(project_id: str) -> Path:
    return project_normalized(project_id) / "metadata" / "source_manifest.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register_file(
    project_id: str,
    file_path: Path,
    run_id: str,
    category: str = "unknown",
) -> FileRegistryEntry:
    """
    Hash a raw file and create a :class:`FileRegistryEntry` for it.

    The entry is *not* persisted here — call :func:`save_registry` after
    collecting all entries for the run.

    Parameters
    ----------
    project_id:
        Project identifier.
    file_path:
        Absolute path to the raw file.
    run_id:
        ID of the current ingest run.
    category:
        Ingest category string (set by the dispatcher). Defaults to "unknown".

    Returns
    -------
    FileRegistryEntry
    """
    file_path = Path(file_path)
    raw_root = project_raw(project_id)

    # Compute relative path for storage
    try:
        rel_path = file_path.relative_to(raw_root).as_posix()
    except ValueError:
        rel_path = file_path.as_posix()

    file_hash = hash_file(file_path)
    file_size = file_path.stat().st_size
    extension = file_path.suffix.lower()
    sid = source_id(rel_path, file_hash)

    return FileRegistryEntry(
        source_id=sid,
        file_path=rel_path,
        file_hash=file_hash,
        file_size_bytes=file_size,
        extension=extension,
        category=category,
        ingested_at=datetime.now(timezone.utc).isoformat(),
        run_id=run_id,
    )


def load_registry(project_id: str) -> list[FileRegistryEntry]:
    """
    Load the file registry for a project from its source_manifest.json.

    Returns an empty list if no registry exists yet.

    Parameters
    ----------
    project_id:
        Project identifier.

    Returns
    -------
    list[FileRegistryEntry]
    """
    path = _registry_path(project_id)
    data = read_json(path)
    entries_raw = data.get("files", [])
    return [_entry_from_dict(e) for e in entries_raw]


def save_registry(project_id: str, entries: list[FileRegistryEntry]) -> None:
    """
    Write the file registry to source_manifest.json for a project.

    Overwrites the existing registry. Wrap existing + new entries
    before calling if you want to keep prior entries.

    Parameters
    ----------
    project_id:
        Project identifier.
    entries:
        List of :class:`FileRegistryEntry` objects to persist.
    """
    path = _registry_path(project_id)
    payload: dict[str, Any] = {
        "project_id": project_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(entries),
        "files": [_entry_to_dict(e) for e in entries],
    }
    write_json(path, payload)


def is_already_ingested(project_id: str, file_path: Path) -> bool:
    """
    Check whether a file has already been ingested by comparing its hash
    against entries in the registry.

    A file is considered already-ingested if its SHA-256 hash matches any
    entry in the registry (path changes are ignored — content is canonical).

    Parameters
    ----------
    project_id:
        Project identifier.
    file_path:
        Absolute path to the file to check.

    Returns
    -------
    bool
    """
    try:
        current_hash = hash_file(Path(file_path))
    except (OSError, FileNotFoundError):
        return False

    entries = load_registry(project_id)
    existing_hashes = {e.file_hash for e in entries}
    return current_hash in existing_hashes


def get_new_files(project_id: str) -> list[Path]:
    """
    Scan the project's ``raw/`` directory and return files that have not
    yet been ingested (i.e. not present in the registry by hash).

    Skips hidden files (starting with ``.``) and directories.

    Parameters
    ----------
    project_id:
        Project identifier.

    Returns
    -------
    list[Path]
        Absolute paths of raw files not yet in the registry.
    """
    raw_root = project_raw(project_id)
    if not raw_root.exists():
        return []

    entries = load_registry(project_id)
    known_hashes = {e.file_hash for e in entries}

    new_files: list[Path] = []
    for file_path in sorted(raw_root.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.name.startswith("."):
            continue
        try:
            fhash = hash_file(file_path)
        except (OSError, PermissionError):
            continue
        if fhash not in known_hashes:
            new_files.append(file_path)

    return new_files

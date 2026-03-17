"""
Project-level source registry.

This module provides a higher-level API over ``engine.io.file_registry``
for querying the ingested files in a project.

The registry answers questions like:
  - "What technical reports have been ingested?"
  - "Are there any drillhole collar files?"
  - "What was the most recently ingested file?"
  - "How many files of each category do we have?"

The underlying data is the ``source_manifest.json`` written by the ingest
dispatcher. This module reads and queries it — it does not write to it.

Writes are handled exclusively by ``engine.io.file_registry.save_registry``
(called by the ingest dispatcher) to keep a single point of truth.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.core.logging import get_logger
from engine.io.file_registry import FileRegistryEntry, load_registry

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Category groupings — logical buckets used in queries
# ---------------------------------------------------------------------------

_DRILLHOLE_CATEGORIES = frozenset({
    "drillhole_collar",
    "drillhole_assay",
    "drillhole_survey",
    "drillhole_lithology",
    "drillhole_geotech",
    "drillhole_qaqc",
})

_DOCUMENT_CATEGORIES = frozenset({
    "technical_report",
    "excel_data",
})

_GIS_CATEGORIES = frozenset({"gis"})
_CAD_CATEGORIES = frozenset({"cad"})
_PHOTO_CATEGORIES = frozenset({"photo"})
_VIDEO_CATEGORIES = frozenset({"video"})
_FINANCIAL_CATEGORIES = frozenset({"financial"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all_sources(project_id: str) -> list[FileRegistryEntry]:
    """Return every ingested file entry for a project."""
    return load_registry(project_id)


def get_sources_by_category(
    project_id: str,
    category: str,
) -> list[FileRegistryEntry]:
    """Return all entries with the given ingest category."""
    return [e for e in load_registry(project_id) if e.category == category]


def get_sources_by_categories(
    project_id: str,
    categories: set[str] | frozenset[str],
) -> list[FileRegistryEntry]:
    """Return entries whose category is one of the given set."""
    return [e for e in load_registry(project_id) if e.category in categories]


def get_technical_reports(project_id: str) -> list[FileRegistryEntry]:
    """Return all ingested PDF/DOCX/PPTX technical report files."""
    return get_sources_by_categories(project_id, _DOCUMENT_CATEGORIES)


def get_drillhole_files(project_id: str) -> list[FileRegistryEntry]:
    """Return all ingested drillhole data files (collars, assays, surveys, etc.)."""
    return get_sources_by_categories(project_id, _DRILLHOLE_CATEGORIES)


def get_collar_files(project_id: str) -> list[FileRegistryEntry]:
    return get_sources_by_category(project_id, "drillhole_collar")


def get_assay_files(project_id: str) -> list[FileRegistryEntry]:
    return get_sources_by_category(project_id, "drillhole_assay")


def get_survey_files(project_id: str) -> list[FileRegistryEntry]:
    return get_sources_by_category(project_id, "drillhole_survey")


def get_gis_files(project_id: str) -> list[FileRegistryEntry]:
    return get_sources_by_categories(project_id, _GIS_CATEGORIES)


def get_cad_files(project_id: str) -> list[FileRegistryEntry]:
    return get_sources_by_categories(project_id, _CAD_CATEGORIES)


def get_financial_files(project_id: str) -> list[FileRegistryEntry]:
    return get_sources_by_categories(project_id, _FINANCIAL_CATEGORIES)


def count_by_category(project_id: str) -> dict[str, int]:
    """
    Return a dict mapping each category to the number of ingested files.

    Useful for the project overview display in the CLI and UI.
    """
    counts: dict[str, int] = {}
    for entry in load_registry(project_id):
        counts[entry.category] = counts.get(entry.category, 0) + 1
    return dict(sorted(counts.items()))


def has_category(project_id: str, category: str) -> bool:
    """Return True if at least one file of the given category has been ingested."""
    return any(e.category == category for e in load_registry(project_id))


def has_technical_reports(project_id: str) -> bool:
    return bool(get_technical_reports(project_id))


def has_drillhole_data(project_id: str) -> bool:
    return bool(get_drillhole_files(project_id))


def source_summary(project_id: str) -> dict[str, Any]:
    """
    Return a human-readable summary dict of what's been ingested.

    Used by the CLI project overview and health check.
    """
    all_entries = load_registry(project_id)
    if not all_entries:
        return {
            "project_id": project_id,
            "total_files": 0,
            "categories": {},
            "has_technical_reports": False,
            "has_drillhole_data": False,
            "most_recent_ingest": None,
        }

    categories = count_by_category(project_id)
    most_recent = max(all_entries, key=lambda e: e.ingested_at).ingested_at

    return {
        "project_id": project_id,
        "total_files": len(all_entries),
        "categories": categories,
        "has_technical_reports": has_technical_reports(project_id),
        "has_drillhole_data": has_drillhole_data(project_id),
        "most_recent_ingest": most_recent,
    }

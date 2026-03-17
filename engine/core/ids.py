"""
ID generation for runs, sources, and entities.

IDs are designed to be:
- Human readable (include a meaningful prefix and date)
- Sortable (date first)
- Collision-resistant (include a short hash or UUID suffix)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from engine.core.hashing import short_hash


def run_id(project_id: str, sequence: int | None = None) -> str:
    """
    Generate a run ID in the format: YYYY-MM-DD_run_NNN

    If sequence is not provided, a short random suffix is used.
    Example: 2026-03-13_run_001
    """
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if sequence is not None:
        return f"{date}_run_{sequence:03d}"
    return f"{date}_run_{short_hash(str(uuid.uuid4()))}"


def source_id(file_path: str, file_hash: str) -> str:
    """
    Generate a stable source ID from the file path and its hash.
    Used in the source registry to uniquely identify ingested files.
    """
    return f"src_{short_hash(file_path + file_hash)}"


def entity_id(entity_type: str, name: str) -> str:
    """
    Generate a stable entity ID from type and name.
    Example: entity_type='drillhole', name='DH-001' → 'dh_a3f2b1c4'
    """
    prefix = entity_type[:4].lower().replace(" ", "_")
    return f"{prefix}_{short_hash(entity_type + name)}"


def uuid4() -> str:
    """Return a standard UUID4 string."""
    return str(uuid.uuid4())

"""
Project manifest — the authoritative state record for a project.

The manifest is stored at:
    <project>/normalized/metadata/project_metadata.json

It records:
  - What the project is (name, company, primary element, location)
  - What stage of processing it is at (status, last run, completion)
  - When it was created and last modified
  - Schema version so we can detect and migrate stale manifests

The manifest is the first thing the engine reads and the last thing it
updates. It is a thin envelope — the deep data lives in the normalized/
layer. Think of it as the project's "cover page".

We deliberately keep it flat JSON (not YAML) so it can be read at a glance
in a file browser and diff'd cleanly in git.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.core.constants import PROJECT_METADATA_FILENAME, SCHEMA_VERSION
from engine.core.enums import ProjectStatus
from engine.core.logging import get_logger
from engine.core.manifests import read_json, write_json
from engine.core.paths import project_normalized

log = get_logger(__name__)


@dataclass
class ProjectMetadata:
    """
    The project manifest record.

    This is the canonical identity + status record for a mining project.
    Everything downstream reads from here before reaching into normalized/.
    """

    # ---- Identity -----------------------------------------------------------
    project_id: str
    name: str = ""
    company: str = ""
    location: str = ""
    primary_element: str = ""
    mine_type: str = ""
    study_level: str = ""

    # ---- Status -------------------------------------------------------------
    status: str = ProjectStatus.SCAFFOLD_ONLY.value
    last_run_id: str | None = None
    last_ingested_at: str | None = None
    last_normalised_at: str | None = None
    last_analysed_at: str | None = None

    # ---- Provenance ---------------------------------------------------------
    schema_version: str = SCHEMA_VERSION
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # ---- Counts (informational, updated by engine) --------------------------
    raw_file_count: int = 0
    run_count: int = 0

    notes: str = ""

    # =========================================================================

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProjectMetadata":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in known})

    def touch(self) -> None:
        """Update the updated_at timestamp to now."""
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Read / write
# ---------------------------------------------------------------------------

def _manifest_path(project_id: str) -> Path:
    return project_normalized(project_id) / "metadata" / PROJECT_METADATA_FILENAME


def read_project_metadata(project_id: str) -> ProjectMetadata:
    """
    Load the project manifest.

    Returns a default ``ProjectMetadata`` if no file exists — this is the
    case for a freshly scaffolded project before first write.
    """
    path = _manifest_path(project_id)
    data = read_json(path)
    if not data:
        return ProjectMetadata(project_id=project_id)
    return ProjectMetadata.from_dict(data)


def write_project_metadata(meta: ProjectMetadata) -> Path:
    """
    Write the project manifest to disk.

    Creates parent directories if needed. Updates *updated_at* before writing.
    Returns the path written.
    """
    meta.touch()
    path = _manifest_path(meta.project_id)
    write_json(path, meta.to_dict())
    log.debug("Project metadata written: %s", path)
    return path


def update_project_metadata(project_id: str, **updates: Any) -> ProjectMetadata:
    """
    Load, update specified fields, and write the project manifest.

    Only recognised ``ProjectMetadata`` field names are applied; unknown keys
    are logged as warnings and ignored.

    Common usage
    ------------
    >>> update_project_metadata("karoua_gold", status="analyzing", last_run_id="2026-03-14_run_001")
    """
    meta = read_project_metadata(project_id)
    known = set(meta.__dataclass_fields__)
    for key, value in updates.items():
        if key in known:
            object.__setattr__(meta, key, value)
        else:
            log.warning("Ignoring unknown metadata field '%s'", key)
    write_project_metadata(meta)
    return meta


def set_project_status(project_id: str, status: ProjectStatus) -> ProjectMetadata:
    """Convenience: update the project status and write the manifest."""
    return update_project_metadata(project_id, status=status.value)

"""
Project creation.

The single entry point for creating a new mining project.

``create_project()`` performs all required setup in a single atomic-ish
sequence:
  1. Validate the project_id (slug rules)
  2. Check the project doesn't already exist
  3. Initialise the folder structure from the template
  4. Write the initial project_metadata.json
  5. Write the initial project_config.yaml

Nothing is written until all validation passes. If any directory creation
fails partway through, the partially created folder tree is left on disk
(not rolled back) — the user can call ``repair_project_structure()`` to
complete it. This keeps the code simple and avoids the complexity of an
atomic filesystem transaction.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from engine.core.enums import ProjectStatus
from engine.core.errors import ProjectAlreadyExistsError
from engine.core.logging import get_logger
from engine.core.paths import project_root
from engine.project.init_structure import init_project_structure
from engine.project.project_config import ProjectConfig, write_project_config
from engine.project.project_manifest import ProjectMetadata, write_project_metadata

log = get_logger(__name__)

# Project IDs must be lowercase slugs: letters, digits, hyphens, underscores
# 2–64 characters. No leading/trailing hyphens or underscores.
_PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]{0,62}[a-z0-9]$|^[a-z0-9]$")


def create_project(
    project_id: str,
    *,
    name: str = "",
    company: str = "",
    location: str = "",
    primary_element: str = "",
    mine_type: str = "",
    study_level: str = "",
    jurisdiction: str = "",
    notes: str = "",
    exist_ok: bool = False,
) -> tuple[ProjectMetadata, ProjectConfig]:
    """
    Create a new mining project.

    Parameters
    ----------
    project_id:
        Unique identifier for the project. Must match ``[a-z0-9][a-z0-9_-]+``.
        This becomes the folder name under ``mining_projects/``.
    name:
        Human-readable project name (e.g. "Karoua Gold Project").
    company:
        Owner / operator company name.
    location:
        Country or region (free text).
    primary_element:
        Primary payable element symbol (e.g. "Au", "Cu").
    mine_type:
        One of the ``MineType`` enum values (e.g. "open_pit").
    study_level:
        One of the ``StudyLevel`` enum values (e.g. "pea").
    jurisdiction:
        YAML slug for the applicable fiscal regime (e.g. "canada", "ghana").
    notes:
        Optional free-text notes written to both manifest and config.
    exist_ok:
        If True and the project already exists, return the existing metadata
        rather than raising. Useful for re-entrant scripts.

    Returns
    -------
    tuple[ProjectMetadata, ProjectConfig]
        The written manifest and config objects.

    Raises
    ------
    ValueError
        If *project_id* fails slug validation.
    ProjectAlreadyExistsError
        If the project already exists and *exist_ok* is False.
    """
    # ---- Validation ---------------------------------------------------------
    validate_project_id(project_id)

    root = project_root(project_id)
    if root.exists():
        if exist_ok:
            log.info("Project %s already exists — returning existing metadata", project_id)
            from engine.project.project_manifest import read_project_metadata
            from engine.project.project_config import read_project_config
            return read_project_metadata(project_id), read_project_config(project_id)
        raise ProjectAlreadyExistsError(
            f"Project '{project_id}' already exists at {root}. "
            "Use exist_ok=True to suppress this error."
        )

    log.info("Creating project: %s", project_id)

    # ---- Step 1: folder structure -------------------------------------------
    init_project_structure(project_id)

    # ---- Step 2: project manifest -------------------------------------------
    meta = ProjectMetadata(
        project_id=project_id,
        name=name or project_id.replace("_", " ").replace("-", " ").title(),
        company=company,
        location=location,
        primary_element=primary_element,
        mine_type=mine_type,
        study_level=study_level,
        status=ProjectStatus.SCAFFOLD_ONLY.value,
        notes=notes,
    )
    write_project_metadata(meta)

    # ---- Step 3: project config ---------------------------------------------
    config = ProjectConfig(
        project_id=project_id,
        name=meta.name,
        company=company,
        location=location,
        primary_element=primary_element,
        mine_type=mine_type or "open_pit",
        study_level=study_level or "unknown",
        jurisdiction=jurisdiction,
        notes=notes,
    )
    write_project_config(config)

    log.info(
        "Project created successfully | id=%s name=%s element=%s",
        project_id, meta.name, primary_element or "not set",
    )
    return meta, config


def validate_project_id(project_id: str) -> None:
    """
    Raise ``ValueError`` if *project_id* is not a valid slug.

    Valid slugs are lowercase alphanumeric strings optionally containing
    hyphens and underscores, between 1 and 64 characters.
    """
    if not project_id:
        raise ValueError("project_id cannot be empty.")
    if not _PROJECT_ID_RE.match(project_id):
        raise ValueError(
            f"Invalid project_id: '{project_id}'. "
            "Must be lowercase letters, digits, hyphens, or underscores "
            "(1–64 characters, no leading/trailing separators)."
        )


def project_exists(project_id: str) -> bool:
    """Return True if the project folder exists on disk."""
    return project_root(project_id).exists()

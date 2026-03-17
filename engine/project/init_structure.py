"""
Project structure initialiser.

Creates the canonical folder layout for a mining project by mirroring the
_project_template/ directory tree into <projects_root>/<project_id>/.

Design principles:
- Idempotent: safe to call on an existing project — only missing folders
  are created, nothing is overwritten or deleted.
- Template-driven: the folder list is derived entirely from the template
  directory on disk, not hardcoded here, so extending the template
  automatically extends all new projects.
- No data: only folders (and placeholder README files) are copied, never
  real data files. .gitkeep files are skipped; they exist only for git.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from engine.core.logging import get_logger
from engine.core.paths import get_project_template_root, project_root

log = get_logger(__name__)


def init_project_structure(project_id: str) -> list[Path]:
    """
    Create the full folder tree for *project_id* from the project template.

    Walks every directory in ``_project_template/`` and creates the
    corresponding directory under ``<projects_root>/<project_id>/``.
    Existing directories are left untouched.

    Parameters
    ----------
    project_id:
        The project identifier (used as the folder name under projects_root).

    Returns
    -------
    list[Path]
        Absolute paths of every directory that was created (not pre-existing).
    """
    template_root = get_project_template_root()
    dest_root = project_root(project_id)

    if not template_root.exists():
        log.warning("Project template not found at %s — creating minimal structure", template_root)
        return _create_minimal_structure(project_id)

    created: list[Path] = []

    # Ensure the project root itself exists
    if not dest_root.exists():
        dest_root.mkdir(parents=True)
        created.append(dest_root)

    # Walk template dirs (skip .gitkeep and hidden files; dirs only)
    for template_dir in sorted(template_root.rglob("*")):
        if not template_dir.is_dir():
            continue
        # Compute relative path from template root
        rel = template_dir.relative_to(template_root)
        dest_dir = dest_root / rel
        if not dest_dir.exists():
            dest_dir.mkdir(parents=True, exist_ok=True)
            created.append(dest_dir)
            log.debug("Created directory: %s", dest_dir)

    # Copy the template README if it exists and destination doesn't have one yet
    template_readme = template_root / "README.md"
    dest_readme = dest_root / "README.md"
    if template_readme.exists() and not dest_readme.exists():
        shutil.copy2(template_readme, dest_readme)

    log.info(
        "Project structure initialised | project=%s dirs_created=%d",
        project_id, len(created),
    )
    return created


def repair_project_structure(project_id: str) -> list[Path]:
    """
    Add any directories that are missing from an existing project.

    Calls ``init_project_structure`` — since it is idempotent, this is safe.
    Intended for use after the template gains new subdirectories.

    Returns
    -------
    list[Path]
        Paths of newly created (previously missing) directories.
    """
    log.info("Repairing project structure for project=%s", project_id)
    return init_project_structure(project_id)


def list_project_directories(project_id: str) -> list[Path]:
    """
    Return all directories that exist under a project root.
    Useful for auditing and repair checking.
    """
    root = project_root(project_id)
    if not root.exists():
        return []
    return sorted(d for d in root.rglob("*") if d.is_dir())


# ---------------------------------------------------------------------------
# Fallback: minimal structure when template is missing
# ---------------------------------------------------------------------------

_MINIMAL_DIRS = [
    "raw/technical_reports",
    "raw/drilling/collars",
    "raw/drilling/assays",
    "raw/drilling/surveys",
    "normalized/metadata",
    "normalized/drilling",
    "normalized/geology",
    "normalized/economics/assumptions",
    "normalized/economics/model_inputs",
    "normalized/interpreted/risk",
    "normalized/staging/entity_extraction/geological_facts",
    "normalized/staging/entity_extraction/economic_facts",
    "normalized/staging/extracted_tables",
    "runs",
    "outputs",
]


def _create_minimal_structure(project_id: str) -> list[Path]:
    """Create the bare minimum folder structure when template is unavailable."""
    root = project_root(project_id)
    created: list[Path] = []
    for rel in _MINIMAL_DIRS:
        d = root / rel
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(d)
    return created

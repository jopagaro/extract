"""
Project bootstrap.

``bootstrap_project()`` is the full first-run initialisation sequence for
a project. It wraps ``create_project()`` and adds:

  - An initial run record (so the run log exists from day one)
  - An environment snapshot (Python / package versions for reproducibility)
  - A welcome log event marking the project as ready

This is what ``mip new`` calls. You can also call it programmatically from
tests or from the API layer.

Existing projects
-----------------
If the project already exists, ``bootstrap_project()`` is idempotent: it
returns the existing metadata without modifying anything. Pass
``force_reinit=True`` to re-run the environment snapshot and log a new
bootstrap event against an existing project.
"""

from __future__ import annotations

from typing import Any

from engine.core.enums import ProjectStatus
from engine.core.ids import run_id as make_run_id
from engine.core.logging import get_logger
from engine.project.create_project import create_project, project_exists
from engine.project.project_config import ProjectConfig
from engine.project.project_manifest import ProjectMetadata, update_project_metadata
from engine.runs.environment_snapshot import write_environment_snapshot
from engine.runs.run_logger import log_event
from engine.runs.run_manager import complete_run, create_run, start_run

log = get_logger(__name__)


def bootstrap_project(
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
    force_reinit: bool = False,
) -> tuple[ProjectMetadata, ProjectConfig]:
    """
    Fully initialise a new project or return the existing one.

    Parameters
    ----------
    project_id:
        Unique slug identifier for the project.
    name, company, location, primary_element, mine_type, study_level,
    jurisdiction, notes:
        Passed directly to ``create_project()``.
    force_reinit:
        If True and the project already exists, runs the environment
        snapshot and logs a re-bootstrap event even though no folders
        are created.

    Returns
    -------
    tuple[ProjectMetadata, ProjectConfig]
    """
    already_existed = project_exists(project_id)

    # Create or retrieve project
    meta, config = create_project(
        project_id,
        name=name,
        company=company,
        location=location,
        primary_element=primary_element,
        mine_type=mine_type,
        study_level=study_level,
        jurisdiction=jurisdiction,
        notes=notes,
        exist_ok=True,
    )

    if already_existed and not force_reinit:
        log.info("Project %s already bootstrapped — nothing to do.", project_id)
        return meta, config

    # ---- Create the bootstrap run record ------------------------------------
    boot_run_id = make_run_id(project_id)
    create_run(project_id, boot_run_id, config={"type": "bootstrap"})
    start_run(project_id, boot_run_id)

    # ---- Environment snapshot -----------------------------------------------
    try:
        write_environment_snapshot(project_id, boot_run_id)
    except Exception as exc:
        log.warning("Could not write environment snapshot: %s", exc)

    # ---- Log bootstrap event ------------------------------------------------
    action = "re-bootstrapped" if already_existed else "bootstrapped"
    log_event(
        project_id,
        boot_run_id,
        "project.bootstrap.complete",
        f"Project {action}: {meta.name}",
        data={
            "project_id": project_id,
            "name": meta.name,
            "primary_element": meta.primary_element,
            "study_level": meta.study_level,
        },
    )

    complete_run(project_id, boot_run_id, notes=f"Bootstrap run — {action}")

    # ---- Update status to INGESTING (ready to receive data) -----------------
    meta = update_project_metadata(
        project_id,
        status=ProjectStatus.INGESTING.value,
        last_run_id=boot_run_id,
    )

    log.info(
        "Project bootstrap complete | id=%s run=%s",
        project_id, boot_run_id,
    )
    return meta, config

"""
Projects router — CRUD for mining projects.

Endpoints:
  GET    /projects              list all projects
  POST   /projects              create a new project
  GET    /projects/{project_id} get a single project
  DELETE /projects/{project_id} delete a project and all its data
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.models.project import ProjectCreate, ProjectList, ProjectResponse
from engine.core.paths import get_projects_root, project_metadata_file, project_root

router = APIRouter(prefix="/projects", tags=["projects"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    """Turn a project name into a safe folder-name ID."""
    import re
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug or "project"


def _load_metadata(project_id: str) -> dict:
    meta_file = project_metadata_file(project_id)
    if not meta_file.exists():
        return {}
    with meta_file.open() as f:
        return json.load(f)


def _save_metadata(project_id: str, data: dict) -> None:
    meta_file = project_metadata_file(project_id)
    meta_file.parent.mkdir(parents=True, exist_ok=True)
    with meta_file.open("w") as f:
        json.dump(data, f, indent=2)


def _build_response(project_id: str, meta: dict) -> ProjectResponse:
    root = project_root(project_id)
    raw_dir = root / "raw" / "documents"
    file_count = len(list(raw_dir.glob("*"))) if raw_dir.exists() else 0
    runs_dir = root / "runs"
    run_count = len([d for d in runs_dir.iterdir() if d.is_dir()]) if runs_dir.exists() else 0

    return ProjectResponse(
        id=project_id,
        name=meta.get("name", project_id),
        description=meta.get("description"),
        commodity=meta.get("commodity"),
        study_type=meta.get("study_type", "PEA"),
        created_at=meta.get("created_at", ""),
        status=meta.get("status", "empty"),
        file_count=file_count,
        run_count=run_count,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=ProjectList)
def list_projects() -> ProjectList:
    """Return all projects found in the projects root."""
    root = get_projects_root()
    if not root.exists():
        return ProjectList(projects=[], total=0)

    projects = []
    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        meta = _load_metadata(folder.name)
        if not meta:
            continue  # skip folders that aren't managed projects
        projects.append(_build_response(folder.name, meta))

    return ProjectList(projects=projects, total=len(projects))


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(body: ProjectCreate) -> ProjectResponse:
    """Create a new project folder and metadata file."""
    root = get_projects_root()
    base_id = _slugify(body.name)
    project_id = base_id
    counter = 1
    while (root / project_id).exists():
        project_id = f"{base_id}_{counter}"
        counter += 1

    # Create the folder structure from the project template
    template_root = Path(__file__).resolve().parent.parent.parent / "_project_template"
    dest = root / project_id
    if template_root.exists():
        shutil.copytree(template_root, dest)
    else:
        dest.mkdir(parents=True, exist_ok=True)

    meta = {
        "id": project_id,
        "name": body.name,
        "description": body.description,
        "commodity": body.commodity,
        "study_type": body.study_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "empty",
    }
    _save_metadata(project_id, meta)
    return _build_response(project_id, meta)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str) -> ProjectResponse:
    meta = _load_metadata(project_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return _build_response(project_id, meta)


@router.patch("/{project_id}", response_model=ProjectResponse)
def rename_project(project_id: str, body: dict) -> ProjectResponse:
    """Update the display name of a project."""
    meta = _load_metadata(project_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be empty")
    meta["name"] = name
    _save_metadata(project_id, meta)
    return _build_response(project_id, meta)


@router.post("/{project_id}/archive", status_code=204)
def archive_project(project_id: str) -> None:
    """Move a project into the _archive subfolder. Hidden from main list but not deleted."""
    src = project_root(project_id)
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    archive_dir = get_projects_root() / "_archive"
    archive_dir.mkdir(exist_ok=True)
    dest = archive_dir / project_id
    if dest.exists():
        # Avoid collision — suffix with timestamp
        from datetime import datetime, timezone
        dest = archive_dir / f"{project_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    shutil.move(str(src), str(dest))


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str) -> None:
    """Permanently delete a project and all its data."""
    root = project_root(project_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    shutil.rmtree(root)

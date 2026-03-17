"""
Reports router — read generated report content.

Endpoints:
  GET /projects/{project_id}/reports               list available reports
  GET /projects/{project_id}/reports/{run_id}      get full report content for a run
  GET /projects/{project_id}/reports/{run_id}/sections/{section}  get one section
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.core.paths import project_root, run_root

router = APIRouter(tags=["reports"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ReportSummary(BaseModel):
    run_id: str
    project_id: str
    available_sections: list[str]
    status: str


class ReportContent(BaseModel):
    run_id: str
    project_id: str
    sections: dict[str, object]


class ReportList(BaseModel):
    project_id: str
    reports: list[ReportSummary]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project_exists(project_id: str) -> None:
    if not project_root(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")


def _get_run_sections(project_id: str, run_id: str) -> dict[str, object]:
    """Load all JSON output files from a run directory."""
    rdir = run_root(project_id, run_id)
    sections = {}
    for jf in sorted(rdir.glob("*.json")):
        if jf.name == "run_status.json":
            continue
        section_name = jf.stem.replace(f"{run_id}_", "")
        try:
            with jf.open() as f:
                sections[section_name] = json.load(f)
        except Exception:
            sections[section_name] = {"error": "Could not parse section file"}
    return sections


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/reports", response_model=ReportList)
def list_reports(project_id: str) -> ReportList:
    """List all runs that have completed output files."""
    _project_exists(project_id)
    runs_dir = project_root(project_id) / "runs"
    if not runs_dir.exists():
        return ReportList(project_id=project_id, reports=[], total=0)

    reports = []
    for run_dir in sorted(runs_dir.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        status_file = run_dir / "run_status.json"
        if not status_file.exists():
            continue
        with status_file.open() as f:
            status_data = json.load(f)
        if status_data.get("status") != "complete":
            continue
        sections = list(_get_run_sections(project_id, run_dir.name).keys())
        reports.append(ReportSummary(
            run_id=run_dir.name,
            project_id=project_id,
            available_sections=sections,
            status="complete",
        ))

    return ReportList(project_id=project_id, reports=reports, total=len(reports))


@router.get("/projects/{project_id}/reports/{run_id}", response_model=ReportContent)
def get_report(project_id: str, run_id: str) -> ReportContent:
    """Get the full content of a completed report run."""
    _project_exists(project_id)
    rdir = run_root(project_id, run_id)
    if not rdir.exists():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    sections = _get_run_sections(project_id, run_id)
    if not sections:
        raise HTTPException(status_code=404, detail="No report output found for this run. Analysis may still be running.")

    return ReportContent(run_id=run_id, project_id=project_id, sections=sections)


@router.get("/projects/{project_id}/reports/{run_id}/sections/{section_name}")
def get_report_section(project_id: str, run_id: str, section_name: str) -> object:
    """Get a single named section from a report run."""
    _project_exists(project_id)
    rdir = run_root(project_id, run_id)
    # Try exact filename match first, then partial
    candidates = list(rdir.glob(f"*{section_name}*.json"))
    candidates = [c for c in candidates if c.name != "run_status.json"]
    if not candidates:
        raise HTTPException(status_code=404, detail=f"Section '{section_name}' not found in run '{run_id}'")
    with candidates[0].open() as f:
        return json.load(f)

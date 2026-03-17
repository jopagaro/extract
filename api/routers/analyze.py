"""
Analyze router — trigger and monitor analysis runs.

Endpoints:
  POST /projects/{project_id}/analyze              start a new analysis run
  GET  /projects/{project_id}/runs                 list all runs
  GET  /projects/{project_id}/runs/{run_id}        get run status and results summary
"""

from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from engine.core.paths import project_root, run_root

router = APIRouter(tags=["analyze"])

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    force: bool = False  # re-run even if outputs already exist


class RunStatus(BaseModel):
    run_id: str
    project_id: str
    status: str  # pending | running | complete | failed
    started_at: str | None = None
    completed_at: str | None = None
    step: str | None = None
    error: str | None = None
    output_files: list[str] = []


class RunList(BaseModel):
    project_id: str
    runs: list[RunStatus]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project_exists(project_id: str) -> None:
    if not project_root(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")


def _load_run_status(project_id: str, run_id: str) -> dict:
    status_file = run_root(project_id, run_id) / "run_status.json"
    if not status_file.exists():
        return {}
    with status_file.open() as f:
        return json.load(f)


def _save_run_status(project_id: str, run_id: str, data: dict) -> None:
    rdir = run_root(project_id, run_id)
    rdir.mkdir(parents=True, exist_ok=True)
    status_file = rdir / "run_status.json"
    with status_file.open("w") as f:
        json.dump(data, f, indent=2)


def _generate_run_id() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")


def _collect_output_files(project_id: str, run_id: str) -> list[str]:
    rdir = run_root(project_id, run_id)
    if not rdir.exists():
        return []
    return [f.name for f in rdir.glob("*.json")]


# ---------------------------------------------------------------------------
# Background analysis worker
# ---------------------------------------------------------------------------

def _run_analysis_in_background(project_id: str, run_id: str) -> None:
    """
    Background thread that calls the engine's extraction pipeline.
    Writes run_status.json at each stage so the UI can poll progress.
    """
    def update(step: str, status: str = "running", error: str | None = None) -> None:
        current = _load_run_status(project_id, run_id)
        current["step"] = step
        current["status"] = status
        if error:
            current["error"] = error
        if status in ("complete", "failed"):
            current["completed_at"] = datetime.now(timezone.utc).isoformat()
        _save_run_status(project_id, run_id, current)

    try:
        update("loading_documents")

        # Collect staged section files (text extracted from raw documents)
        sections_dir = project_root(project_id) / "normalized" / "sections"
        section_files = list(sections_dir.glob("*.txt")) if sections_dir.exists() else []

        if not section_files:
            # No pre-extracted sections — build a combined text from raw files
            raw_dir = project_root(project_id) / "raw" / "documents"
            raw_files = list(raw_dir.glob("*")) if raw_dir.exists() else []
            if not raw_files:
                update("failed", status="failed", error="No files found in project library. Upload documents first.")
                return
            # For now, we can only process text/csv files directly without a PDF parser
            text_parts = []
            for rf in raw_files:
                if rf.suffix.lower() in {".txt", ".md", ".csv"}:
                    try:
                        text_parts.append(rf.read_text(errors="replace"))
                    except Exception:
                        pass
            if not text_parts:
                update("failed", status="failed", error="No text-extractable files found. PDF/DOCX parsing requires the ingest pipeline (mip ingest add). Upload .txt or .csv files to test the analysis flow.")
                return
            project_data = "\n\n---\n\n".join(text_parts)
        else:
            project_data = "\n\n---\n\n".join(sf.read_text(errors="replace") for sf in section_files)

        update("extracting_facts")

        # Call the engine's LLM extraction
        from engine.llm.extraction.extract_project_facts import extract_project_facts

        async def _run() -> dict:
            response = await extract_project_facts(project_data[:40000], run_id=run_id)
            return response.content if hasattr(response, "content") else {}

        result = asyncio.run(_run())

        # Write output
        output_dir = project_root(project_id) / "normalized" / "interpreted" / "project_facts"
        output_dir.mkdir(parents=True, exist_ok=True)
        out_file = output_dir / f"{run_id}_project_facts.json"
        with out_file.open("w") as f:
            json.dump(result, f, indent=2)

        # Also copy to run dir for easy retrieval
        run_out = run_root(project_id, run_id) / "project_facts.json"
        with run_out.open("w") as f:
            json.dump(result, f, indent=2)

        update("complete", status="complete")

    except Exception as exc:
        update("failed", status="failed", error=str(exc))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/analyze", response_model=RunStatus, status_code=202)
def start_analysis(
    project_id: str,
    body: AnalyzeRequest = AnalyzeRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> RunStatus:
    """
    Kick off a new analysis run for the project.
    Returns immediately with a run_id; poll /runs/{run_id} for status.
    """
    _project_exists(project_id)
    run_id = _generate_run_id()
    now = datetime.now(timezone.utc).isoformat()

    status_data = {
        "run_id": run_id,
        "project_id": project_id,
        "status": "pending",
        "started_at": now,
        "completed_at": None,
        "step": "queued",
        "error": None,
    }
    _save_run_status(project_id, run_id, status_data)

    # Launch in a real thread so asyncio.run() inside works cleanly
    t = threading.Thread(
        target=_run_analysis_in_background,
        args=(project_id, run_id),
        daemon=True,
    )
    t.start()

    return RunStatus(**status_data, output_files=[])


@router.get("/projects/{project_id}/runs", response_model=RunList)
def list_runs(project_id: str) -> RunList:
    """List all runs for a project, newest first."""
    _project_exists(project_id)
    runs_dir = project_root(project_id) / "runs"
    if not runs_dir.exists():
        return RunList(project_id=project_id, runs=[], total=0)

    runs = []
    for run_dir in sorted(runs_dir.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        data = _load_run_status(project_id, run_dir.name)
        if not data:
            continue
        outputs = _collect_output_files(project_id, run_dir.name)
        runs.append(RunStatus(**data, output_files=outputs))

    return RunList(project_id=project_id, runs=runs, total=len(runs))


@router.get("/projects/{project_id}/runs/{run_id}", response_model=RunStatus)
def get_run(project_id: str, run_id: str) -> RunStatus:
    """Get the status of a specific run."""
    _project_exists(project_id)
    data = _load_run_status(project_id, run_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    outputs = _collect_output_files(project_id, run_id)
    return RunStatus(**data, output_files=outputs)

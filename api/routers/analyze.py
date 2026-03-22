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
    force: bool = False


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
    with (rdir / "run_status.json").open("w") as f:
        json.dump(data, f, indent=2)


def _generate_run_id() -> str:
    return datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")


def _collect_output_files(project_id: str, run_id: str) -> list[str]:
    rdir = run_root(project_id, run_id)
    if not rdir.exists():
        return []
    return [f.name for f in rdir.glob("*.json")]


def _save_section(project_id: str, run_id: str, section_key: str, data: dict) -> None:
    rdir = run_root(project_id, run_id)
    rdir.mkdir(parents=True, exist_ok=True)
    with (rdir / f"{section_key}.json").open("w") as f:
        json.dump(data, f, indent=2)


def _extract_response_data(response) -> dict:
    """Safely extract dict from LLMResponse or DualLLMResponse."""
    if hasattr(response, "merged"):
        return response.merged or {}
    if hasattr(response, "structured") and response.structured:
        return response.structured
    if hasattr(response, "content"):
        return {"text": response.content}
    return {}


# ---------------------------------------------------------------------------
# Full analysis pipeline
# ---------------------------------------------------------------------------

def _run_analysis_in_background(project_id: str, run_id: str) -> None:
    """
    Full consulting report pipeline:
      1. Load documents
      2. Extract structured project facts
      3. Write executive summary, geology, economics, and risk sections
      4. Save data sources notice
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
        # ── Step 1: Load documents ──────────────────────────────────────────
        update("Loading documents")

        raw_dir = project_root(project_id) / "raw" / "documents"
        raw_files = [f for f in raw_dir.glob("*") if f.is_file()] if raw_dir.exists() else []
        if not raw_files:
            update("failed", status="failed",
                   error="No files found. Upload documents first.")
            return

        from engine.core.document_loader import load_document

        text_parts = []
        source_files = []
        load_errors = []
        for rf in raw_files:
            try:
                text = load_document(rf)
                if text and text.strip():
                    text_parts.append(f"[Source: {rf.name}]\n{text}")
                    source_files.append(rf.name)
            except Exception as exc:
                load_errors.append(f"{rf.name}: {exc}")

        if not text_parts:
            detail = "No readable content found in uploaded files."
            if load_errors:
                detail += " Errors: " + "; ".join(load_errors[:3])
            update("failed", status="failed", error=detail)
            return

        project_data = "\n\n---\n\n".join(text_parts)
        truncated = project_data[:50000]

        # ── Step 2: Extract project facts ──────────────────────────────────
        update("Extracting project facts")

        from engine.llm.extraction.extract_project_facts import extract_project_facts

        async def _extract() -> dict:
            r = await extract_project_facts(truncated, run_id=run_id)
            return _extract_response_data(r)

        facts = asyncio.run(_extract())
        _save_section(project_id, run_id, "01_project_facts", facts)

        facts_str = json.dumps(facts, indent=2)
        combined = f"PROJECT FACTS:\n{facts_str}\n\nSOURCE DOCUMENTS:\n{truncated}"

        # ── Step 2.5: Extract economic assumptions + mine plan in parallel ──
        update("Extracting economic data")

        from engine.llm.extraction.extract_economic_assumptions import extract_economic_assumptions
        from engine.llm.extraction.extract_mine_plan_inputs import extract_mine_plan_inputs

        async def _extract_econ() -> tuple[dict, dict]:
            econ, mine = await asyncio.gather(
                extract_economic_assumptions(truncated, run_id=run_id),
                extract_mine_plan_inputs(truncated, run_id=run_id),
            )
            return _extract_response_data(econ), _extract_response_data(mine)

        econ_assumptions, mine_plan = asyncio.run(_extract_econ())

        # ── Step 2.6: Run DCF model (non-fatal — falls back to LLM-only) ───
        update("Running economics model")

        dcf_output: dict | None = None
        try:
            import dataclasses
            from engine.economics.input_builder import build_input_book_from_llm
            from engine.economics.dcf_model import run_dcf
            from engine.economics.sensitivity_runner import run_sensitivity

            input_book = build_input_book_from_llm(
                project_id=project_id,
                economic_assumptions=econ_assumptions,
                mine_plan=mine_plan,
                project_facts=facts,
            )
            if input_book:
                cash_flows, summary = run_dcf(input_book)
                sensitivity = run_sensitivity(input_book)
                dcf_output = {
                    "model_ran": True,
                    "assumptions_notes": input_book.notes,
                    "summary": summary.to_dict(),
                    "cash_flow_table": [dataclasses.asdict(cf) for cf in cash_flows],
                    "sensitivity": sensitivity.to_dict(),
                }
            else:
                dcf_output = {
                    "model_ran": False,
                    "reason": "Insufficient data to build economics model from source documents.",
                }
        except Exception as dcf_exc:
            import traceback
            dcf_output = {
                "model_ran": False,
                "reason": f"DCF model error: {dcf_exc}",
            }

        _save_section(project_id, run_id, "06_dcf_model", dcf_output)

        # ── Step 3: Write specialist sections in parallel ──────────────────
        update("Writing report sections")

        from engine.llm.reporting.write_geology_section import write_geology_section
        from engine.llm.reporting.write_economics_section import write_economics_section
        from engine.llm.reporting.write_risk_section import write_risk_section

        dcf_context = (
            "COMPUTED DCF MODEL:\n" + json.dumps(dcf_output, indent=2)
            if dcf_output and dcf_output.get("model_ran")
            else None
        )

        async def _write_sections() -> tuple[dict, dict, dict]:
            geology, economics, risks = await asyncio.gather(
                write_geology_section(combined, run_id=run_id),
                write_economics_section(combined, run_id=run_id, extra_context=dcf_context),
                write_risk_section(combined, run_id=run_id),
            )
            return (
                _extract_response_data(geology),
                _extract_response_data(economics),
                _extract_response_data(risks),
            )

        geology, economics, risks = asyncio.run(_write_sections())

        _save_section(project_id, run_id, "03_geology", geology)
        _save_section(project_id, run_id, "04_economics", economics)
        _save_section(project_id, run_id, "05_risks", risks)

        # ── Step 4: Assemble narrative synthesis ────────────────────────────
        update("Writing analyst narrative")

        from engine.llm.reporting.assemble_report_sections import assemble_report_sections

        assembly_input = json.dumps({
            "project_facts": facts,
            "geology": geology,
            "economics": economics,
            "risks": risks,
            "dcf_model": dcf_output,
            "source_files": source_files,
        }, indent=2)

        async def _assemble() -> dict:
            r = await assemble_report_sections(assembly_input, run_id=run_id)
            return _extract_response_data(r)

        assembly = asyncio.run(_assemble())
        _save_section(project_id, run_id, "07_assembly", assembly)

        # ── Step 5: Save data sources notice ───────────────────────────────
        update("Finalising report")

        sources_notice = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "source_files": source_files,
            "file_count": len(source_files),
            "notice": (
                "This report was generated by AI from the source documents listed above. "
                "All figures and conclusions should be verified against the original documents. "
                "This report does not constitute investment advice or a formal technical study."
            ),
            "data_coverage": {
                "project_facts": bool(facts),
                "geology": bool(geology),
                "economics": bool(economics),
                "risks": bool(risks),
                "dcf_model_ran": bool(dcf_output and dcf_output.get("model_ran")),
                "narrative_assembled": bool(assembly),
            }
        }
        _save_section(project_id, run_id, "00_data_sources", sources_notice)

        update("Complete", status="complete")

    except Exception as exc:
        import traceback
        update("failed", status="failed", error=f"{exc}\n{traceback.format_exc()[:500]}")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/analyze", response_model=RunStatus, status_code=202)
def start_analysis(
    project_id: str,
    body: AnalyzeRequest = AnalyzeRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> RunStatus:
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

    t = threading.Thread(
        target=_run_analysis_in_background,
        args=(project_id, run_id),
        daemon=True,
    )
    t.start()

    return RunStatus(**status_data, output_files=[])


@router.get("/projects/{project_id}/runs", response_model=RunList)
def list_runs(project_id: str) -> RunList:
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
    _project_exists(project_id)
    data = _load_run_status(project_id, run_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    outputs = _collect_output_files(project_id, run_id)
    return RunStatus(**data, output_files=outputs)


@router.delete("/projects/{project_id}/runs/{run_id}", status_code=204)
def delete_run(project_id: str, run_id: str) -> None:
    _project_exists(project_id)
    rdir = run_root(project_id, run_id)
    if not rdir.exists():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    import shutil
    shutil.rmtree(rdir)


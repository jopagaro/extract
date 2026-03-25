"""
Portfolio router — cross-project comparison.

Aggregates key metrics from multiple projects into a single response
for side-by-side comparison in the UI.

Endpoints:
  GET /portfolio/compare?ids=id1,id2,id3   return comparison matrix
  GET /portfolio/projects                  return all projects (for selector)
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Query
from pydantic import BaseModel

from engine.core.paths import (
    get_projects_root,
    project_metadata_file,
    project_root,
    run_root,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open() as f:
            return json.load(f)
    except Exception:
        return {}


def _load_list(path: Path) -> list:
    if not path.exists():
        return []
    try:
        with path.open() as f:
            return json.load(f)
    except Exception:
        return []


def _latest_complete_run(project_id: str) -> str | None:
    """Return the run_id of the most recent completed run, or None."""
    runs_dir = project_root(project_id) / "runs"
    if not runs_dir.exists():
        return None
    candidates = []
    for d in runs_dir.iterdir():
        if not d.is_dir():
            continue
        status_file = d / "run_status.json"
        if not status_file.exists():
            continue
        try:
            with status_file.open() as f:
                s = json.load(f)
            if s.get("status") == "complete":
                completed_at = s.get("completed_at", "")
                candidates.append((completed_at, d.name))
        except Exception:
            pass
    if not candidates:
        return None
    return sorted(candidates, reverse=True)[0][1]


def _scalar_search(obj: dict | list, *keys: str) -> str | float | None:
    """
    Recursively search a nested object for any of the given keys,
    returning the first non-null scalar value found.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower().replace(" ", "_").replace("-", "_") in [kk.lower() for kk in keys]:
                if isinstance(v, (str, int, float)) and v not in (None, ""):
                    return v
        for v in obj.values():
            if isinstance(v, (dict, list)):
                result = _scalar_search(v, *keys)
                if result is not None:
                    return result
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                result = _scalar_search(item, *keys)
                if result is not None:
                    return result
    return None


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ProjectMetrics(BaseModel):
    project_id: str
    name: str
    commodity: str | None
    study_type: str | None
    status: str | None
    has_report: bool

    # Resources
    total_resource_mt: float | None
    mi_resource_mt: float | None
    inferred_pct: float | None
    primary_grade: float | None
    grade_unit: str | None
    total_contained: float | None
    metal_unit: str | None

    # Economics (from DCF / report)
    npv_musd: float | None
    irr_pct: float | None
    payback_years: float | None
    initial_capex_musd: float | None
    aisc_per_oz: float | None
    opex_per_tonne: float | None

    # Project facts
    jurisdiction: str | None
    operator: str | None
    mine_life_years: float | None

    # Royalties
    nsr_burden_pct: float | None
    has_stream: bool

    # Portfolio metadata
    file_count: int
    run_count: int
    notes_count: int
    comparables_count: int


class PortfolioComparison(BaseModel):
    projects: list[ProjectMetrics]
    total: int


# ---------------------------------------------------------------------------
# Data aggregation per project
# ---------------------------------------------------------------------------

def _build_metrics(project_id: str) -> ProjectMetrics:
    meta = _load_json(project_metadata_file(project_id))
    root = project_root(project_id)

    # File / run counts
    raw_dir = root / "raw" / "documents"
    file_count = len(list(raw_dir.glob("*"))) if raw_dir.exists() else 0
    runs_dir = root / "runs"
    run_count = len([d for d in runs_dir.iterdir() if d.is_dir()]) if runs_dir.exists() else 0

    # Notes / comparables counts
    notes = _load_list(root / "normalized" / "metadata" / "notes.json")
    comps = _load_list(root / "normalized" / "metadata" / "comparables.json")

    # Resources
    res_rows = _load_list(root / "normalized" / "metadata" / "resources.json")
    measured_mt = sum(r.get("tonnage_mt") or 0 for r in res_rows if r.get("classification") == "Measured")
    indicated_mt = sum(r.get("tonnage_mt") or 0 for r in res_rows if r.get("classification") == "Indicated")
    inferred_mt = sum(r.get("tonnage_mt") or 0 for r in res_rows if r.get("classification") == "Inferred")
    total_mt = measured_mt + indicated_mt + inferred_mt
    inferred_pct = round(inferred_mt / total_mt * 100, 1) if total_mt > 0 else None

    # Best-effort grade from first resource row with a grade
    grade_row = next((r for r in res_rows if r.get("grade_value") is not None), None)
    primary_grade = grade_row.get("grade_value") if grade_row else None
    grade_unit = grade_row.get("grade_unit") if grade_row else None

    metal_units = [r["metal_unit"] for r in res_rows if r.get("metal_unit")]
    metal_unit = max(set(metal_units), key=metal_units.count) if metal_units else None
    total_contained = sum(r.get("contained_metal") or 0 for r in res_rows if r.get("contained_metal") is not None) or None

    # Royalties
    roy_rows = _load_list(root / "normalized" / "metadata" / "royalties.json")
    nsr_rates = [r.get("rate_pct") or 0 for r in roy_rows if r.get("royalty_type") in ("NSR", "GR", "Sliding NSR") and r.get("rate_pct")]
    nsr_burden = round(sum(nsr_rates), 4) if nsr_rates else None
    has_stream = any(r.get("royalty_type") == "Stream" for r in roy_rows)

    # Latest complete run outputs
    run_id = _latest_complete_run(project_id)
    has_report = run_id is not None

    npv_musd = irr_pct = payback_years = None
    initial_capex_musd = aisc_per_oz = opex_per_tonne = None
    jurisdiction = operator = None
    mine_life_years = None

    if run_id:
        rdir = run_root(project_id, run_id)

        # DCF model
        dcf = _load_json(rdir / "06_dcf_model.json")
        if dcf:
            v = _scalar_search(dcf, "npv", "npv_musd", "net_present_value", "npv_base")
            if isinstance(v, (int, float)):
                npv_musd = float(v)
            v = _scalar_search(dcf, "irr", "irr_pct", "internal_rate_of_return")
            if isinstance(v, (int, float)):
                irr_pct = float(v)
            v = _scalar_search(dcf, "payback", "payback_years", "payback_period")
            if isinstance(v, (int, float)):
                payback_years = float(v)

        # Economics section
        econ = _load_json(rdir / "04_economics.json")
        if not econ:
            econ = _load_json(rdir / "07_assembly.json")
        if econ:
            v = _scalar_search(econ, "initial_capex", "capex", "capital_cost", "initial_capital", "upfront_capex")
            if isinstance(v, (int, float)):
                initial_capex_musd = float(v)
            v = _scalar_search(econ, "aisc", "all_in_sustaining_cost", "aisc_per_oz")
            if isinstance(v, (int, float)):
                aisc_per_oz = float(v)
            v = _scalar_search(econ, "opex_per_tonne", "operating_cost_per_tonne", "cash_cost_per_tonne", "opex")
            if isinstance(v, (int, float)):
                opex_per_tonne = float(v)

        # Project facts
        facts = _load_json(rdir / "01_project_facts.json")
        if facts:
            v = _scalar_search(facts, "jurisdiction", "country", "location", "state_province")
            if isinstance(v, str):
                jurisdiction = v
            v = _scalar_search(facts, "operator", "developer", "company", "owner")
            if isinstance(v, str):
                operator = v
            v = _scalar_search(facts, "mine_life", "mine_life_years", "project_life", "life_of_mine")
            if isinstance(v, (int, float)):
                mine_life_years = float(v)

    return ProjectMetrics(
        project_id=project_id,
        name=meta.get("name", project_id),
        commodity=meta.get("commodity"),
        study_type=meta.get("study_type"),
        status=meta.get("status"),
        has_report=has_report,
        total_resource_mt=round(total_mt, 3) if total_mt else None,
        mi_resource_mt=round(measured_mt + indicated_mt, 3) if (measured_mt + indicated_mt) else None,
        inferred_pct=inferred_pct,
        primary_grade=primary_grade,
        grade_unit=grade_unit,
        total_contained=total_contained,
        metal_unit=metal_unit,
        npv_musd=npv_musd,
        irr_pct=irr_pct,
        payback_years=payback_years,
        initial_capex_musd=initial_capex_musd,
        aisc_per_oz=aisc_per_oz,
        opex_per_tonne=opex_per_tonne,
        jurisdiction=jurisdiction,
        operator=operator,
        mine_life_years=mine_life_years,
        nsr_burden_pct=nsr_burden,
        has_stream=has_stream,
        file_count=file_count,
        run_count=run_count,
        notes_count=len(notes),
        comparables_count=len(comps),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/compare", response_model=PortfolioComparison)
def compare_portfolio(
    ids: str = Query(..., description="Comma-separated project IDs"),
) -> PortfolioComparison:
    """
    Aggregate key metrics from multiple projects for side-by-side comparison.
    Pass ids as a comma-separated query parameter: ?ids=project_a,project_b,project_c
    """
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    metrics = []
    for pid in id_list:
        if project_root(pid).exists():
            metrics.append(_build_metrics(pid))
    return PortfolioComparison(projects=metrics, total=len(metrics))


@router.get("/projects")
def portfolio_projects() -> dict:
    """Return all projects with basic metadata for the portfolio selector."""
    root = get_projects_root()
    if not root.exists():
        return {"projects": []}
    projects = []
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or folder.name.startswith("_"):
            continue
        meta = _load_json(project_metadata_file(folder.name))
        if not meta:
            continue
        projects.append({
            "id": folder.name,
            "name": meta.get("name", folder.name),
            "commodity": meta.get("commodity"),
            "study_type": meta.get("study_type"),
            "status": meta.get("status"),
        })
    return {"projects": projects}

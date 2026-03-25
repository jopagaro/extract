"""
Drill Holes router
==================
Endpoints for uploading, querying, and clearing drill hole data.

Endpoints:
  POST   /projects/{id}/drillholes/upload        upload a collars/surveys/assays file
  GET    /projects/{id}/drillholes               fetch the full compiled dataset
  GET    /projects/{id}/drillholes/summary       quick stats (hole count, analytes, etc.)
  DELETE /projects/{id}/drillholes               clear all drill hole data
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from engine.core.paths import project_root

router = APIRouter(tags=["drillholes"])

# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _dh_dir(project_id: str) -> Path:
    return project_root(project_id) / "normalized" / "metadata" / "drillholes"


def _load_dh(project_id: str, name: str) -> list:
    p = _dh_dir(project_id) / f"{name}.json"
    if not p.exists():
        return []
    with p.open() as f:
        return json.load(f)


def _save_dh(project_id: str, name: str, data: list | dict) -> None:
    d = _dh_dir(project_id)
    d.mkdir(parents=True, exist_ok=True)
    with (d / f"{name}.json").open("w") as f:
        json.dump(data, f, indent=2)


def _project_exists(project_id: str) -> None:
    if not project_root(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class UploadResult(BaseModel):
    project_id: str
    table_type: str
    filename: str
    hole_count: int
    row_count: int
    analytes: list[str]
    error: str | None = None


class DrillholeDataset(BaseModel):
    project_id: str
    collars: list[dict]
    surveys: list[dict]
    assays:  list[dict]
    traces:  dict       # {hole_id: [{depth,x,y,z},...]}
    analytes: list[str]
    hole_count: int
    updated_at: str | None


class DrillholeSummary(BaseModel):
    project_id: str
    hole_count: int
    has_surveys: bool
    has_assays: bool
    analytes: list[str]
    assay_stats: dict   # {analyte: {count,min,max,mean,...}}
    total_metres: float
    updated_at: str | None


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/drillholes/upload", response_model=UploadResult, status_code=202)
async def upload_drillhole_file(
    project_id: str,
    file: UploadFile = File(...),
) -> UploadResult:
    """
    Upload a collars, surveys, or assay CSV/XLSX file.
    The table type is auto-detected from column names.
    Uploading a new file of the same type replaces the previous data for that type.
    After each upload, the desurvey computation is re-run and traces are saved.
    """
    _project_exists(project_id)

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".csv", ".xlsx", ".xls"):
        raise HTTPException(status_code=422, detail="Only CSV and Excel files are accepted")

    raw = await file.read()

    # Write to a temp file so we can use pandas
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        tmp_path = Path(tmp.name)

    try:
        from engine.ingest.drillhole_ingest import (
            load_drillhole_file, desurvey_holes,
            get_analyte_columns, compute_assay_stats,
        )

        result = load_drillhole_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    if result.get("error"):
        raise HTTPException(status_code=422, detail=result["error"])

    ttype = result["type"]
    rows  = result["rows"]

    if ttype not in ("collars", "surveys", "assays"):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Could not auto-detect table type from columns: {result['columns'][:10]}. "
                "Expected collar columns (HOLEID, X, Y, Z, DEPTH), "
                "survey columns (HOLEID, DEPTH/AT, AZIMUTH, DIP), or "
                "assay columns (HOLEID, FROM, TO, + analytes)."
            )
        )

    # Merge with existing (for surveys/assays, replace by hole — for collars replace all)
    if ttype == "collars":
        _save_dh(project_id, "collars", rows)
    elif ttype == "surveys":
        existing = {s["hole_id"]: [] for s in _load_dh(project_id, "surveys")}
        for s in _load_dh(project_id, "surveys"):
            existing[s["hole_id"]].append(s)
        new_holes = {s["hole_id"] for s in rows}
        merged = [s for hid, ss in existing.items() for s in ss if hid not in new_holes] + rows
        _save_dh(project_id, "surveys", merged)
    elif ttype == "assays":
        existing_assays = [a for a in _load_dh(project_id, "assays")]
        new_holes = {a["hole_id"] for a in rows}
        merged = [a for a in existing_assays if a["hole_id"] not in new_holes] + rows
        _save_dh(project_id, "assays", merged)

    # Re-run desurveying
    _rebuild_traces(project_id)

    analytes = result.get("analytes", [])
    return UploadResult(
        project_id=project_id,
        table_type=ttype,
        filename=file.filename or "",
        hole_count=result["hole_count"],
        row_count=result["row_count"],
        analytes=analytes,
    )


def _rebuild_traces(project_id: str) -> None:
    from engine.ingest.drillhole_ingest import desurvey_holes
    collars = _load_dh(project_id, "collars")
    surveys = _load_dh(project_id, "surveys")
    if not collars:
        return
    traces = desurvey_holes(collars, surveys)
    _save_dh(project_id, "traces", traces)
    _save_dh(project_id, "meta", {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "hole_count": len(collars),
    })


# ---------------------------------------------------------------------------
# GET full dataset
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/drillholes", response_model=DrillholeDataset)
def get_drillholes(project_id: str) -> DrillholeDataset:
    """Return the full compiled drill hole dataset for visualization."""
    _project_exists(project_id)
    collars  = _load_dh(project_id, "collars")
    surveys  = _load_dh(project_id, "surveys")
    assays   = _load_dh(project_id, "assays")
    traces_raw = _load_dh(project_id, "traces")
    meta     = _load_dh(project_id, "meta") if (_dh_dir(project_id) / "meta.json").exists() else {}
    if isinstance(meta, list):
        meta = {}

    from engine.ingest.drillhole_ingest import get_analyte_columns
    analytes = get_analyte_columns(assays)

    traces: dict = traces_raw if isinstance(traces_raw, dict) else {}

    return DrillholeDataset(
        project_id=project_id,
        collars=collars,
        surveys=surveys,
        assays=assays,
        traces=traces,
        analytes=analytes,
        hole_count=len(collars),
        updated_at=meta.get("updated_at") if isinstance(meta, dict) else None,
    )


# ---------------------------------------------------------------------------
# GET summary
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/drillholes/summary", response_model=DrillholeSummary)
def get_drillhole_summary(project_id: str) -> DrillholeSummary:
    """Return quick statistics for the drill hole dataset."""
    _project_exists(project_id)
    collars = _load_dh(project_id, "collars")
    surveys = _load_dh(project_id, "surveys")
    assays  = _load_dh(project_id, "assays")
    meta    = _load_dh(project_id, "meta") if (_dh_dir(project_id) / "meta.json").exists() else {}
    if isinstance(meta, list):
        meta = {}

    from engine.ingest.drillhole_ingest import get_analyte_columns, compute_assay_stats
    analytes = get_analyte_columns(assays)
    assay_stats = {a: compute_assay_stats(assays, a) for a in analytes[:10]}

    total_m = sum(c.get("depth") or 0 for c in collars)

    return DrillholeSummary(
        project_id=project_id,
        hole_count=len(collars),
        has_surveys=len(surveys) > 0,
        has_assays=len(assays) > 0,
        analytes=analytes,
        assay_stats=assay_stats,
        total_metres=round(total_m, 1),
        updated_at=meta.get("updated_at") if isinstance(meta, dict) else None,
    )


# ---------------------------------------------------------------------------
# DELETE all drill hole data
# ---------------------------------------------------------------------------

@router.delete("/projects/{project_id}/drillholes", status_code=204)
def delete_drillholes(project_id: str) -> None:
    """Remove all drill hole data (collars, surveys, assays, traces) for a project."""
    _project_exists(project_id)
    dh_dir = _dh_dir(project_id)
    for name in ("collars", "surveys", "assays", "traces", "meta"):
        p = dh_dir / f"{name}.json"
        if p.exists():
            p.unlink()

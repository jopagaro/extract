"""
Resources router — project mineral resource classification table.

Stores the M/I/Inf resource breakdown for a project so the platform can
flag classification mismatches against the study stage (e.g. Inferred in FS).

Endpoints:
  GET    /projects/{project_id}/resources
  POST   /projects/{project_id}/resources        add a resource category row
  PATCH  /projects/{project_id}/resources/{row_id}
  DELETE /projects/{project_id}/resources/{row_id}
  GET    /projects/{project_id}/resources/summary  aggregated totals + warnings
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.core.paths import project_root

router = APIRouter(prefix="/projects/{project_id}/resources", tags=["resources"])

CLASSIFICATIONS = {"Measured", "Indicated", "Inferred"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _res_path(project_id: str) -> Path:
    return project_root(project_id) / "normalized" / "metadata" / "resources.json"


def _load_rows(project_id: str) -> list[dict]:
    path = _res_path(project_id)
    if not path.exists():
        return []
    with path.open() as f:
        return json.load(f)


def _save_rows(project_id: str, rows: list[dict]) -> None:
    path = _res_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(rows, f, indent=2)


def _project_exists(project_id: str) -> None:
    if not project_root(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")


def _study_type(project_id: str) -> str | None:
    """Read study_type from project metadata if available."""
    meta = project_root(project_id) / "normalized" / "metadata" / "project.json"
    if not meta.exists():
        return None
    try:
        with meta.open() as f:
            return json.load(f).get("study_type")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ResourceRow(BaseModel):
    classification: str          # Measured | Indicated | Inferred
    domain: str | None = None    # e.g. "oxide", "sulphide", "all domains"
    tonnage_mt: float | None = None          # million tonnes
    grade_value: float | None = None         # e.g. 1.24
    grade_unit: str | None = None            # g/t, %, ppm, lb/t
    contained_metal: float | None = None     # e.g. 2.4
    metal_unit: str | None = None            # Moz, Mlb, kt, Mt
    cut_off_grade: str | None = None         # e.g. "0.3 g/t Au"
    notes: str | None = None


class ResourceRowFull(ResourceRow):
    row_id: str
    created_at: str
    updated_at: str


class ResourceRowCreate(ResourceRow):
    pass


class ResourceRowUpdate(BaseModel):
    classification: str | None = None
    domain: str | None = None
    tonnage_mt: float | None = None
    grade_value: float | None = None
    grade_unit: str | None = None
    contained_metal: float | None = None
    metal_unit: str | None = None
    cut_off_grade: str | None = None
    notes: str | None = None


class ResourceWarning(BaseModel):
    level: str          # "critical" | "caution" | "info"
    message: str


class ResourceSummary(BaseModel):
    project_id: str
    total_tonnage_mt: float | None
    measured_mt: float | None
    indicated_mt: float | None
    inferred_mt: float | None
    inferred_pct: float | None
    metal_unit: str | None
    total_contained: float | None
    measured_indicated_contained: float | None
    inferred_contained: float | None
    warnings: list[ResourceWarning]


# ---------------------------------------------------------------------------
# Classification rules
# ---------------------------------------------------------------------------

# Study stages that cannot use Inferred resources in economic models
_INFERRED_PROHIBITED = {"FS", "PFS"}
# Stages where high Inferred % is a caution (not blocking)
_INFERRED_CAUTION_THRESHOLD = 50.0  # %


def _build_warnings(rows: list[dict], study_type: str | None) -> list[ResourceWarning]:
    warnings: list[ResourceWarning] = []

    inferred_rows = [r for r in rows if r.get("classification") == "Inferred"]
    mi_rows = [r for r in rows if r.get("classification") in ("Measured", "Indicated")]

    has_inferred = len(inferred_rows) > 0
    inferred_mt = sum(r.get("tonnage_mt") or 0 for r in inferred_rows)
    total_mt = sum(r.get("tonnage_mt") or 0 for r in rows)
    inferred_pct = (inferred_mt / total_mt * 100) if total_mt > 0 else 0.0

    if study_type and has_inferred:
        if study_type in _INFERRED_PROHIBITED:
            warnings.append(ResourceWarning(
                level="critical",
                message=(
                    f"This project is classified as {study_type}. Under NI 43-101 and JORC, "
                    f"Inferred resources cannot be used in economic analysis at {study_type} stage. "
                    f"Inferred tonnes must be excluded from the mine plan and DCF model."
                ),
            ))
        elif inferred_pct > _INFERRED_CAUTION_THRESHOLD:
            warnings.append(ResourceWarning(
                level="caution",
                message=(
                    f"Inferred resources make up {inferred_pct:.0f}% of total resources. "
                    f"At PEA stage, Inferred can be included but heavy reliance on Inferred "
                    f"introduces significant geological risk. Upgrade drilling is advisable."
                ),
            ))

    if not rows:
        warnings.append(ResourceWarning(
            level="info",
            message="No resource data entered. Add Measured, Indicated, and Inferred rows to enable classification analysis.",
        ))
    elif not mi_rows and has_inferred:
        warnings.append(ResourceWarning(
            level="caution",
            message="All resources are Inferred — no Measured or Indicated tonnes have been entered. Economic projections cannot be supported at prefeasibility or feasibility level.",
        ))

    return warnings


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ResourceRowFull])
def list_resources(project_id: str) -> list[ResourceRowFull]:
    _project_exists(project_id)
    rows = _load_rows(project_id)
    order = {"Measured": 0, "Indicated": 1, "Inferred": 2}
    rows_sorted = sorted(rows, key=lambda r: order.get(r.get("classification", ""), 99))
    return [ResourceRowFull(**r) for r in rows_sorted]


@router.post("", response_model=ResourceRowFull, status_code=201)
def create_resource_row(project_id: str, body: ResourceRowCreate) -> ResourceRowFull:
    _project_exists(project_id)
    if body.classification not in CLASSIFICATIONS:
        raise HTTPException(
            status_code=422,
            detail=f"classification must be one of: {', '.join(sorted(CLASSIFICATIONS))}"
        )
    now = datetime.now(timezone.utc).isoformat()
    row = {"row_id": str(uuid.uuid4()), **body.model_dump(), "created_at": now, "updated_at": now}
    rows = _load_rows(project_id)
    rows.append(row)
    _save_rows(project_id, rows)
    return ResourceRowFull(**row)


@router.patch("/{row_id}", response_model=ResourceRowFull)
def update_resource_row(project_id: str, row_id: str, body: ResourceRowUpdate) -> ResourceRowFull:
    _project_exists(project_id)
    rows = _load_rows(project_id)
    for row in rows:
        if row["row_id"] == row_id:
            updates = body.model_dump(exclude_unset=True)
            if "classification" in updates and updates["classification"] not in CLASSIFICATIONS:
                raise HTTPException(status_code=422, detail="Invalid classification")
            row.update(updates)
            row["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_rows(project_id, rows)
            return ResourceRowFull(**row)
    raise HTTPException(status_code=404, detail=f"Row '{row_id}' not found")


@router.delete("/{row_id}", status_code=204)
def delete_resource_row(project_id: str, row_id: str) -> None:
    _project_exists(project_id)
    rows = _load_rows(project_id)
    filtered = [r for r in rows if r["row_id"] != row_id]
    if len(filtered) == len(rows):
        raise HTTPException(status_code=404, detail=f"Row '{row_id}' not found")
    _save_rows(project_id, filtered)


@router.get("/summary", response_model=ResourceSummary)
def resource_summary(project_id: str) -> ResourceSummary:
    """Aggregate totals and generate classification warnings."""
    _project_exists(project_id)
    rows = _load_rows(project_id)
    study_type = _study_type(project_id)

    def _sum_mt(cls: str) -> float | None:
        vals = [r["tonnage_mt"] for r in rows if r.get("classification") == cls and r.get("tonnage_mt") is not None]
        return sum(vals) if vals else None

    def _sum_metal(cls_list: list[str]) -> float | None:
        vals = [r["contained_metal"] for r in rows if r.get("classification") in cls_list and r.get("contained_metal") is not None]
        return sum(vals) if vals else None

    measured_mt = _sum_mt("Measured")
    indicated_mt = _sum_mt("Indicated")
    inferred_mt = _sum_mt("Inferred")
    mi_mt = (measured_mt or 0) + (indicated_mt or 0)
    total_mt = mi_mt + (inferred_mt or 0)

    inferred_pct: float | None = None
    if total_mt > 0 and inferred_mt is not None:
        inferred_pct = round(inferred_mt / total_mt * 100, 1)

    # Pick the most common metal_unit across rows
    units = [r["metal_unit"] for r in rows if r.get("metal_unit")]
    metal_unit = max(set(units), key=units.count) if units else None

    return ResourceSummary(
        project_id=project_id,
        total_tonnage_mt=round(total_mt, 3) if total_mt else None,
        measured_mt=measured_mt,
        indicated_mt=indicated_mt,
        inferred_mt=inferred_mt,
        inferred_pct=inferred_pct,
        metal_unit=metal_unit,
        total_contained=_sum_metal(["Measured", "Indicated", "Inferred"]),
        measured_indicated_contained=_sum_metal(["Measured", "Indicated"]),
        inferred_contained=_sum_metal(["Inferred"]),
        warnings=_build_warnings(rows, study_type),
    )

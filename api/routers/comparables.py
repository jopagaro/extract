"""
Comparables router — analyst-curated comparable transactions database.

Each project can have a set of reference M&A deals or project sales
used to benchmark valuation metrics ($/oz, $/lb, EV/resource, etc.).

Endpoints:
  GET    /projects/{project_id}/comparables
  POST   /projects/{project_id}/comparables
  PATCH  /projects/{project_id}/comparables/{comp_id}
  DELETE /projects/{project_id}/comparables/{comp_id}
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.core.paths import project_root

router = APIRouter(prefix="/projects/{project_id}/comparables", tags=["comparables"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _comps_path(project_id: str) -> Path:
    return project_root(project_id) / "normalized" / "metadata" / "comparables.json"


def _load_comps(project_id: str) -> list[dict]:
    path = _comps_path(project_id)
    if not path.exists():
        return []
    with path.open() as f:
        return json.load(f)


def _save_comps(project_id: str, comps: list[dict]) -> None:
    path = _comps_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(comps, f, indent=2)


def _project_exists(project_id: str) -> None:
    if not project_root(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ComparableCreate(BaseModel):
    project_name: str                    # Name of the comparable project / asset
    acquirer: str | None = None          # Buyer (if M&A)
    seller: str | None = None            # Seller / vendor
    commodity: str | None = None         # Primary commodity (gold, copper, lithium…)
    transaction_date: str | None = None  # YYYY or YYYY-MM
    transaction_value_musd: float | None = None   # Total deal value, USD millions
    resource_moz_or_mlb: float | None = None      # Total resource (Moz Au or Mlb Cu etc.)
    price_per_unit_usd: float | None = None       # $/oz or $/lb implied by deal
    study_stage: str | None = None       # PEA / PFS / FS / producing
    jurisdiction: str | None = None
    notes: str | None = None


class ComparableUpdate(BaseModel):
    project_name: str | None = None
    acquirer: str | None = None
    seller: str | None = None
    commodity: str | None = None
    transaction_date: str | None = None
    transaction_value_musd: float | None = None
    resource_moz_or_mlb: float | None = None
    price_per_unit_usd: float | None = None
    study_stage: str | None = None
    jurisdiction: str | None = None
    notes: str | None = None


class Comparable(BaseModel):
    comp_id: str
    project_name: str
    acquirer: str | None = None
    seller: str | None = None
    commodity: str | None = None
    transaction_date: str | None = None
    transaction_value_musd: float | None = None
    resource_moz_or_mlb: float | None = None
    price_per_unit_usd: float | None = None
    study_stage: str | None = None
    jurisdiction: str | None = None
    notes: str | None = None
    created_at: str
    updated_at: str


class ComparableList(BaseModel):
    project_id: str
    comparables: list[Comparable]
    total: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=ComparableList)
def list_comparables(project_id: str) -> ComparableList:
    """Return all comparable transactions for this project."""
    _project_exists(project_id)
    comps = _load_comps(project_id)
    comps_sorted = sorted(comps, key=lambda c: c.get("transaction_date") or "", reverse=True)
    return ComparableList(
        project_id=project_id,
        comparables=[Comparable(**c) for c in comps_sorted],
        total=len(comps_sorted),
    )


@router.post("", response_model=Comparable, status_code=201)
def create_comparable(project_id: str, body: ComparableCreate) -> Comparable:
    """Add a comparable transaction to this project."""
    _project_exists(project_id)
    if not body.project_name.strip():
        raise HTTPException(status_code=422, detail="project_name is required")

    now = datetime.now(timezone.utc).isoformat()
    comp = {
        "comp_id": str(uuid.uuid4()),
        **body.model_dump(),
        "created_at": now,
        "updated_at": now,
    }

    comps = _load_comps(project_id)
    comps.append(comp)
    _save_comps(project_id, comps)
    return Comparable(**comp)


@router.patch("/{comp_id}", response_model=Comparable)
def update_comparable(project_id: str, comp_id: str, body: ComparableUpdate) -> Comparable:
    """Update fields on an existing comparable."""
    _project_exists(project_id)
    comps = _load_comps(project_id)
    for comp in comps:
        if comp["comp_id"] == comp_id:
            updates = body.model_dump(exclude_unset=True)
            comp.update(updates)
            comp["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_comps(project_id, comps)
            return Comparable(**comp)
    raise HTTPException(status_code=404, detail=f"Comparable '{comp_id}' not found")


@router.delete("/{comp_id}", status_code=204)
def delete_comparable(project_id: str, comp_id: str) -> None:
    """Remove a comparable transaction."""
    _project_exists(project_id)
    comps = _load_comps(project_id)
    filtered = [c for c in comps if c["comp_id"] != comp_id]
    if len(filtered) == len(comps):
        raise HTTPException(status_code=404, detail=f"Comparable '{comp_id}' not found")
    _save_comps(project_id, filtered)

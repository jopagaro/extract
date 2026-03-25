"""
Royalties router — royalty and streaming agreement overlay.

Tracks NSR, gross royalty, NPI, stream, and sliding-scale agreements
on a project and computes their aggregate burden on project economics.

Endpoints:
  GET    /projects/{project_id}/royalties
  POST   /projects/{project_id}/royalties
  PATCH  /projects/{project_id}/royalties/{royalty_id}
  DELETE /projects/{project_id}/royalties/{royalty_id}
  GET    /projects/{project_id}/royalties/summary
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.core.paths import project_root

router = APIRouter(prefix="/projects/{project_id}/royalties", tags=["royalties"])

ROYALTY_TYPES = {
    "NSR",           # Net Smelter Return — % of gross revenue after smelter deductions
    "GR",            # Gross Revenue / Gross Royalty — % before any deductions
    "NPI",           # Net Profit Interest — % of net profits
    "Stream",        # Offtake stream — % of production at a fixed purchase price
    "Sliding NSR",   # NSR that steps up as metal price rises
    "Production",    # Fixed $ per unit of metal produced
    "Other",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _path(project_id: str) -> Path:
    return project_root(project_id) / "normalized" / "metadata" / "royalties.json"


def _load(project_id: str) -> list[dict]:
    p = _path(project_id)
    if not p.exists():
        return []
    with p.open() as f:
        return json.load(f)


def _save(project_id: str, rows: list[dict]) -> None:
    p = _path(project_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        json.dump(rows, f, indent=2)


def _project_exists(project_id: str) -> None:
    if not project_root(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RoyaltyCreate(BaseModel):
    royalty_type: str               # NSR | GR | NPI | Stream | Sliding NSR | Production | Other
    holder: str                     # Royalty holder name
    rate_pct: float | None = None   # % rate (NSR, GR, NPI, Sliding NSR)
    metals_covered: str | None = None  # e.g. "Gold, Silver" or "All metals"
    area_covered: str | None = None    # e.g. "All claims" or "Block A only"
    # Stream-specific
    stream_pct: float | None = None          # % of production streamed
    stream_purchase_price: float | None = None  # Fixed purchase price per oz/lb
    stream_purchase_unit: str | None = None     # e.g. "USD/oz", "USD/lb"
    # Sliding scale: list as JSON string for simplicity
    sliding_scale_notes: str | None = None   # e.g. "1% <$1500, 1.5% $1500-2000, 2% >$2000"
    # Production royalty
    production_rate: float | None = None     # $ per unit
    production_unit: str | None = None       # e.g. "USD/oz"
    # Buyback
    buyback_option: bool = False
    buyback_price_musd: float | None = None  # Buyback price in M USD
    # General
    recorded_instrument: str | None = None  # e.g. "Title No. 12345"
    notes: str | None = None


class RoyaltyUpdate(BaseModel):
    royalty_type: str | None = None
    holder: str | None = None
    rate_pct: float | None = None
    metals_covered: str | None = None
    area_covered: str | None = None
    stream_pct: float | None = None
    stream_purchase_price: float | None = None
    stream_purchase_unit: str | None = None
    sliding_scale_notes: str | None = None
    production_rate: float | None = None
    production_unit: str | None = None
    buyback_option: bool | None = None
    buyback_price_musd: float | None = None
    recorded_instrument: str | None = None
    notes: str | None = None


class Royalty(RoyaltyCreate):
    royalty_id: str
    created_at: str
    updated_at: str


class RoyaltyWarning(BaseModel):
    level: str       # critical | caution | info
    message: str


class RoyaltySummary(BaseModel):
    project_id: str
    total_agreements: int
    nsr_equivalent_pct: float | None   # Rough NSR-equivalent sum for NSR/GR agreements
    has_stream: bool
    has_npi: bool
    holders: list[str]
    metals_affected: list[str]
    buyback_options: int
    warnings: list[RoyaltyWarning]


# NSR equivalent thresholds
_CAUTION_NSR_PCT = 2.0   # > 2% total NSR → caution
_HIGH_NSR_PCT    = 3.5   # > 3.5% total NSR → critical


def _build_warnings(rows: list[dict]) -> list[RoyaltyWarning]:
    warnings: list[RoyaltyWarning] = []
    if not rows:
        return warnings

    # Sum NSR-equivalent rates (NSR and GR are roughly comparable; NPI and streams are separate)
    nsr_rates = [
        r.get("rate_pct") or 0
        for r in rows
        if r.get("royalty_type") in ("NSR", "GR", "Sliding NSR")
    ]
    total_nsr = sum(nsr_rates)

    if total_nsr >= _HIGH_NSR_PCT:
        warnings.append(RoyaltyWarning(
            level="critical",
            message=(
                f"Total NSR/GR royalty burden is {total_nsr:.2f}% — this is high and will "
                f"materially reduce project revenue. Projects above ~3.5% combined NSR often "
                f"struggle to achieve viable economics at lower metal prices."
            ),
        ))
    elif total_nsr >= _CAUTION_NSR_PCT:
        warnings.append(RoyaltyWarning(
            level="caution",
            message=(
                f"Total NSR/GR royalty burden is {total_nsr:.2f}%. This is meaningful and "
                f"should be explicitly modelled in the DCF — verify it is reflected in the "
                f"revenue assumptions, not just noted in passing."
            ),
        ))

    streams = [r for r in rows if r.get("royalty_type") == "Stream"]
    for s in streams:
        pct = s.get("stream_pct")
        price = s.get("stream_purchase_price")
        unit = s.get("stream_purchase_unit") or ""
        holder = s.get("holder") or "Unknown"
        if pct and price:
            warnings.append(RoyaltyWarning(
                level="caution",
                message=(
                    f"Stream agreement with {holder}: {pct}% of production at "
                    f"{price} {unit}. Verify the current spot price vs stream price "
                    f"differential is correctly captured in the economic model."
                ),
            ))

    npis = [r for r in rows if r.get("royalty_type") == "NPI"]
    if npis:
        warnings.append(RoyaltyWarning(
            level="info",
            message=(
                f"{len(npis)} NPI agreement(s) present. NPIs are difficult to model precisely — "
                f"confirm whether the reported economics reflect the NPI deduction or treat it "
                f"as an off-balance-sheet item."
            ),
        ))

    sliding = [r for r in rows if r.get("royalty_type") == "Sliding NSR"]
    if sliding:
        warnings.append(RoyaltyWarning(
            level="info",
            message=(
                "Sliding-scale NSR detected. Verify which price tier the base-case DCF uses "
                "and run sensitivity at each step-up threshold."
            ),
        ))

    return warnings


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=list[Royalty])
def list_royalties(project_id: str) -> list[Royalty]:
    _project_exists(project_id)
    rows = _load(project_id)
    return [Royalty(**r) for r in rows]


@router.post("", response_model=Royalty, status_code=201)
def create_royalty(project_id: str, body: RoyaltyCreate) -> Royalty:
    _project_exists(project_id)
    if not body.holder.strip():
        raise HTTPException(status_code=422, detail="holder is required")
    now = datetime.now(timezone.utc).isoformat()
    row = {"royalty_id": str(uuid.uuid4()), **body.model_dump(), "created_at": now, "updated_at": now}
    rows = _load(project_id)
    rows.append(row)
    _save(project_id, rows)
    return Royalty(**row)


@router.patch("/{royalty_id}", response_model=Royalty)
def update_royalty(project_id: str, royalty_id: str, body: RoyaltyUpdate) -> Royalty:
    _project_exists(project_id)
    rows = _load(project_id)
    for row in rows:
        if row["royalty_id"] == royalty_id:
            row.update(body.model_dump(exclude_unset=True))
            row["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save(project_id, rows)
            return Royalty(**row)
    raise HTTPException(status_code=404, detail=f"Royalty '{royalty_id}' not found")


@router.delete("/{royalty_id}", status_code=204)
def delete_royalty(project_id: str, royalty_id: str) -> None:
    _project_exists(project_id)
    rows = _load(project_id)
    filtered = [r for r in rows if r["royalty_id"] != royalty_id]
    if len(filtered) == len(rows):
        raise HTTPException(status_code=404, detail=f"Royalty '{royalty_id}' not found")
    _save(project_id, filtered)


@router.get("/summary", response_model=RoyaltySummary)
def royalty_summary(project_id: str) -> RoyaltySummary:
    _project_exists(project_id)
    rows = _load(project_id)

    nsr_rates = [
        r.get("rate_pct") or 0
        for r in rows
        if r.get("royalty_type") in ("NSR", "GR", "Sliding NSR") and r.get("rate_pct")
    ]
    total_nsr = round(sum(nsr_rates), 4) if nsr_rates else None

    holders = list({r.get("holder") or "" for r in rows if r.get("holder")})

    metals_raw = " ".join(r.get("metals_covered") or "" for r in rows)
    metals = list({m.strip() for m in metals_raw.replace(",", " ").split() if m.strip()})

    return RoyaltySummary(
        project_id=project_id,
        total_agreements=len(rows),
        nsr_equivalent_pct=total_nsr,
        has_stream=any(r.get("royalty_type") == "Stream" for r in rows),
        has_npi=any(r.get("royalty_type") == "NPI" for r in rows),
        holders=sorted(holders),
        metals_affected=sorted(metals),
        buyback_options=sum(1 for r in rows if r.get("buyback_option")),
        warnings=_build_warnings(rows),
    )

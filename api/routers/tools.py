"""
Tools router — unit conversion and sanity checking utilities.

Endpoints:
  GET  /projects/{project_id}/sanity   run sanity checks on a project's data
  POST /tools/convert                  convert between mining units
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.core.paths import project_root, run_root

router = APIRouter(tags=["tools"])

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
    runs_dir = project_root(project_id) / "runs"
    if not runs_dir.exists():
        return None
    candidates = []
    for d in runs_dir.iterdir():
        if not d.is_dir():
            continue
        sf = d / "run_status.json"
        if not sf.exists():
            continue
        try:
            with sf.open() as f:
                s = json.load(f)
            if s.get("status") == "complete":
                candidates.append((s.get("completed_at", ""), d.name))
        except Exception:
            pass
    return sorted(candidates, reverse=True)[0][1] if candidates else None


def _scalar_search(obj: object, *keys: str) -> float | str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():  # type: ignore[union-attr]
            norm = k.lower().replace(" ", "_").replace("-", "_")
            if norm in [kk.lower() for kk in keys]:
                if isinstance(v, (int, float)) and not math.isnan(float(v)):
                    return float(v)
                if isinstance(v, str) and v:
                    return v
        for v in obj.values():  # type: ignore[union-attr]
            if isinstance(v, (dict, list)):
                r = _scalar_search(v, *keys)
                if r is not None:
                    return r
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                r = _scalar_search(item, *keys)
                if r is not None:
                    return r
    return None


# ---------------------------------------------------------------------------
# Sanity check schemas
# ---------------------------------------------------------------------------

class SanityFlag(BaseModel):
    level: str        # critical | warning | info | ok
    category: str     # Resources | Economics | Royalties | Consistency
    field: str
    value: str
    message: str
    expected_range: str | None = None


class SanityResult(BaseModel):
    project_id: str
    has_report: bool
    flags: list[SanityFlag]
    critical_count: int
    warning_count: int
    ok_count: int
    overall: str      # critical | warning | ok | no_data


# Sanity thresholds
_RANGES: dict[str, tuple[float, float, str]] = {
    # (min, max, unit) — values outside trigger a flag
    "irr":            (5.0,   80.0,   "%"),
    "payback":        (0.5,   15.0,   "years"),
    "aisc_gold":      (400,   2800,   "$/oz"),
    "mine_life":      (3.0,   60.0,   "years"),
    "inferred_pct":   (0.0,   90.0,   "%"),    # >90% = very unusual
    "nsr_burden":     (0.0,   5.0,    "%"),
    "gold_grade":     (0.1,   100.0,  "g/t"),  # > 100 g/t is implausible at scale
    "copper_grade":   (0.05,  10.0,   "%"),
    "opex_per_tonne": (5.0,   200.0,  "$/t"),
}

_CAUTION: dict[str, tuple[float, float]] = {
    # (caution_low, caution_high) — within range but still worth flagging
    "irr":           (10.0, 50.0),
    "gold_grade":    (0.3,  20.0),
    "inferred_pct":  (0.0,  60.0),
    "aisc_gold":     (700,  2000),
}


def _flag(
    level: str,
    category: str,
    field: str,
    value: float | str,
    message: str,
    expected_range: str | None = None,
) -> SanityFlag:
    return SanityFlag(
        level=level,
        category=category,
        field=field,
        value=str(value),
        message=message,
        expected_range=expected_range,
    )


def _check_range(
    key: str,
    val: float,
    category: str,
    field_label: str,
) -> SanityFlag | None:
    mn, mx, unit = _RANGES[key]
    if val < mn or val > mx:
        return _flag(
            "critical", category, field_label, f"{val} {unit}",
            f"Value of {val} {unit} is outside the expected range for {field_label}.",
            f"{mn}–{mx} {unit}",
        )
    if key in _CAUTION:
        clo, chi = _CAUTION[key]
        if val < clo or val > chi:
            return _flag(
                "warning", category, field_label, f"{val} {unit}",
                f"{val} {unit} is technically plausible but unusually {'low' if val < clo else 'high'} — verify assumptions.",
                f"Typical: {clo}–{chi} {unit}",
            )
    return _flag("ok", category, field_label, f"{val} {unit}", f"{field_label} is within expected range.")


# ---------------------------------------------------------------------------
# Sanity check endpoint
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/sanity", response_model=SanityResult)
def run_sanity_check(project_id: str) -> SanityResult:
    """
    Run sanity checks on a project's manually entered data and latest report.
    Returns flags at critical / warning / ok / info levels.
    """
    root = project_root(project_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    meta = _load_json(root / "normalized" / "metadata" / "project_metadata.json")
    res_rows = _load_list(root / "normalized" / "metadata" / "resources.json")
    roy_rows = _load_list(root / "normalized" / "metadata" / "royalties.json")
    run_id = _latest_complete_run(project_id)
    has_report = run_id is not None

    flags: list[SanityFlag] = []
    study_type = meta.get("study_type", "PEA")

    # ── Resource checks ──────────────────────────────────────────────────────
    if not res_rows:
        flags.append(_flag("info", "Resources", "Resource table", "empty",
            "No resource data entered. Add rows in the Resources tab to enable grade and tonnage sanity checks."))
    else:
        measured_mt = sum(r.get("tonnage_mt") or 0 for r in res_rows if r.get("classification") == "Measured")
        indicated_mt = sum(r.get("tonnage_mt") or 0 for r in res_rows if r.get("classification") == "Indicated")
        inferred_mt = sum(r.get("tonnage_mt") or 0 for r in res_rows if r.get("classification") == "Inferred")
        total_mt = measured_mt + indicated_mt + inferred_mt

        if total_mt > 0:
            inferred_pct = inferred_mt / total_mt * 100
            f = _check_range("inferred_pct", round(inferred_pct, 1), "Resources", "Inferred %")
            if f:
                if f.level in ("critical", "warning") and inferred_pct > 60:
                    f.message = (
                        f"Inferred resources are {inferred_pct:.0f}% of total. "
                        f"{'At PFS/FS stage this is not permitted.' if study_type in ('PFS','FS') else 'Heavy reliance on Inferred introduces significant geological uncertainty.'}"
                    )
                flags.append(f)

        # Grade checks per row
        for row in res_rows:
            grade = row.get("grade_value")
            unit = (row.get("grade_unit") or "").strip().lower()
            cls = row.get("classification", "")
            if grade is None:
                continue
            if "g/t" in unit or unit in ("g/t au", "g/t gold"):
                f = _check_range("gold_grade", grade, "Resources", f"{cls} gold grade")
                if f:
                    flags.append(f)
            elif "%" in unit and ("cu" in unit or "copper" in unit or "%" == unit):
                f = _check_range("copper_grade", grade, "Resources", f"{cls} copper grade")
                if f:
                    flags.append(f)

        # Contained metal consistency check
        for row in res_rows:
            t = row.get("tonnage_mt")
            g = row.get("grade_value")
            c = row.get("contained_metal")
            unit = (row.get("grade_unit") or "").lower()
            metal_unit = (row.get("metal_unit") or "").lower()
            cls = row.get("classification", "")

            if t and g and c and "g/t" in unit and "oz" in metal_unit:
                expected_moz = t * 1_000_000 * g / 31.1035 / 1_000_000  # Moz
                deviation = abs(expected_moz - c) / max(expected_moz, 0.001)
                if deviation > 0.05:  # >5% discrepancy
                    flags.append(_flag(
                        "warning", "Consistency",
                        f"{cls} contained metal",
                        f"{c} Moz",
                        f"Contained metal ({c} Moz) doesn't match tonnage × grade calculation "
                        f"({expected_moz:.2f} Moz from {t} Mt at {g} g/t). Check figures.",
                    ))
                else:
                    flags.append(_flag("ok", "Consistency", f"{cls} contained metal check",
                        f"{c} Moz", "Contained metal is consistent with tonnage × grade."))

    # ── Royalty checks ───────────────────────────────────────────────────────
    if roy_rows:
        nsr_rates = [r.get("rate_pct") or 0 for r in roy_rows
                     if r.get("royalty_type") in ("NSR", "GR", "Sliding NSR") and r.get("rate_pct")]
        if nsr_rates:
            total_nsr = sum(nsr_rates)
            f = _check_range("nsr_burden", round(total_nsr, 3), "Royalties", "NSR/GR burden")
            if f:
                flags.append(f)

    # ── Economics checks (latest run) ────────────────────────────────────────
    if not has_report:
        flags.append(_flag("info", "Economics", "Report", "none",
            "No completed analysis run yet. Run analysis to enable economic sanity checks."))
    else:
        rdir = run_root(project_id, run_id)  # type: ignore[arg-type]

        dcf = _load_json(rdir / "06_dcf_model.json")
        if dcf:
            irr = _scalar_search(dcf, "irr", "irr_pct", "internal_rate_of_return")
            if isinstance(irr, (int, float)):
                f = _check_range("irr", float(irr), "Economics", "IRR")
                if f:
                    flags.append(f)

            payback = _scalar_search(dcf, "payback", "payback_years", "payback_period")
            if isinstance(payback, (int, float)):
                f = _check_range("payback", float(payback), "Economics", "Payback period")
                if f:
                    flags.append(f)

            npv = _scalar_search(dcf, "npv", "npv_musd", "net_present_value")
            capex = _scalar_search(dcf, "initial_capex", "capex", "capital_cost")
            if isinstance(npv, (int, float)) and isinstance(capex, (int, float)) and capex > 0:
                ratio = float(npv) / float(capex)
                if ratio < 0:
                    flags.append(_flag("critical", "Economics", "NPV", f"${npv}M",
                        f"NPV is negative (${npv}M). Project does not return its capital at the base-case discount rate."))
                elif ratio < 0.5:
                    flags.append(_flag("warning", "Economics", "NPV/Capex ratio", f"{ratio:.2f}x",
                        f"NPV is only {ratio:.2f}x the initial capex — thin margin of safety. Verify discount rate and price assumptions.",
                        "Typical: >1.0x for robust projects"))
                else:
                    flags.append(_flag("ok", "Economics", "NPV/Capex ratio", f"{ratio:.2f}x",
                        f"NPV is {ratio:.2f}× initial capex — reasonable capital return."))

        econ = _load_json(rdir / "04_economics.json")
        if econ:
            aisc = _scalar_search(econ, "aisc", "all_in_sustaining_cost", "aisc_per_oz")
            if isinstance(aisc, (int, float)):
                f = _check_range("aisc_gold", float(aisc), "Economics", "AISC")
                if f:
                    flags.append(f)

            opex = _scalar_search(econ, "opex_per_tonne", "operating_cost_per_tonne", "cash_cost_per_tonne")
            if isinstance(opex, (int, float)):
                f = _check_range("opex_per_tonne", float(opex), "Economics", "Opex per tonne")
                if f:
                    flags.append(f)

        mine_life = _scalar_search(_load_json(rdir / "01_project_facts.json"),
                                   "mine_life", "mine_life_years", "project_life")
        if isinstance(mine_life, (int, float)):
            f = _check_range("mine_life", float(mine_life), "Economics", "Mine life")
            if f:
                flags.append(f)

    critical = sum(1 for f in flags if f.level == "critical")
    warning  = sum(1 for f in flags if f.level == "warning")
    ok_count = sum(1 for f in flags if f.level == "ok")

    overall = ("no_data" if not flags else
               "critical" if critical > 0 else
               "warning" if warning > 0 else "ok")

    return SanityResult(
        project_id=project_id,
        has_report=has_report,
        flags=flags,
        critical_count=critical,
        warning_count=warning,
        ok_count=ok_count,
        overall=overall,
    )


# ---------------------------------------------------------------------------
# Unit conversion endpoint
# ---------------------------------------------------------------------------

CONVERSION_FACTORS: dict[str, dict[str, float]] = {
    # Gold grade
    "g/t":  {"oz/t": 1 / 31.1035, "g/t": 1.0},
    "oz/t": {"g/t": 31.1035, "oz/t": 1.0},
    # Gold mass
    "moz":  {"kg": 31_103.5, "t": 31.1035, "g": 31_103_477.0, "moz": 1.0},
    "g":    {"moz": 1 / 31_103_477.0, "oz": 1 / 31.1035, "g": 1.0},
    "oz":   {"g": 31.1035, "oz": 1.0},
    # Copper grade
    "% cu": {"lb/t": 22.0462, "kg/t": 10.0, "% cu": 1.0},
    "lb/t": {"% cu": 1 / 22.0462, "kg/t": 10 / 22.0462, "lb/t": 1.0},
    "kg/t": {"% cu": 0.1, "lb/t": 2.20462, "kg/t": 1.0},
    # Mass
    "t":    {"short ton": 1.10231, "long ton": 0.984207, "kg": 1000.0, "t": 1.0},
    "mt":   {"short ton": 1_102_311.0, "long ton": 984_207.0, "kt": 1000.0, "mt": 1.0},
    "kt":   {"mt": 0.001, "t": 1000.0, "mlb": 2.20462, "kt": 1.0},
    "mlb":  {"kt": 0.453592, "t": 453.592, "mlb": 1.0},
    "short ton": {"t": 0.907185, "short ton": 1.0},
    # Cost
    "$/oz": {"$/g": 1 / 31.1035, "$/oz": 1.0},
    "$/g":  {"$/oz": 31.1035, "$/g": 1.0},
    "$/t":  {"$/lb": 1 / 2204.62, "$/t": 1.0},
    "$/lb": {"$/t": 2204.62, "$/lb": 1.0},
    # Currency scale
    "musd": {"kusd": 1000.0, "usd": 1_000_000.0, "musd": 1.0},
    "kusd": {"musd": 0.001, "usd": 1000.0, "kusd": 1.0},
}


class ConvertRequest(BaseModel):
    value: float
    from_unit: str
    to_unit: str


class ConvertResponse(BaseModel):
    value: float
    from_unit: str
    to_unit: str
    result: float
    formula: str


# ---------------------------------------------------------------------------
# Jurisdiction risk endpoints
# ---------------------------------------------------------------------------

@router.get("/tools/jurisdiction/{jurisdiction_name}")
def lookup_jurisdiction(jurisdiction_name: str) -> dict:
    """
    Look up jurisdiction risk profile by name (fuzzy matched).
    Returns 404 if no match found.
    """
    from engine.market.jurisdiction_risk import get_jurisdiction_risk
    result = get_jurisdiction_risk(jurisdiction_name)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No jurisdiction profile found for '{jurisdiction_name}'. "
                   f"Try a country name, region, or common alias.",
        )
    return result


@router.get("/tools/jurisdictions")
def list_all_jurisdictions() -> dict:
    """Return a summary list of all jurisdictions in the database."""
    from engine.market.jurisdiction_risk import list_jurisdictions
    items = list_jurisdictions()
    return {"jurisdictions": items, "total": len(items)}


@router.get("/projects/{project_id}/jurisdiction-risk")
def get_project_jurisdiction_risk(project_id: str) -> dict:
    """
    Auto-detect jurisdiction from the project's latest run facts and return
    the matching risk profile.  Returns {"not_found": true} if no match.
    """
    root = project_root(project_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    # Try the cached file first (saved during analysis)
    run_id = _latest_complete_run(project_id)
    if run_id:
        cached = _load_json(run_root(project_id, run_id) / "12_jurisdiction_risk.json")
        if cached and not cached.get("not_found"):
            return cached

    # Fall back to live lookup from project facts
    facts: dict = {}
    if run_id:
        facts = _load_json(run_root(project_id, run_id) / "01_project_facts.json")

    from engine.market.jurisdiction_risk import detect_jurisdiction, get_jurisdiction_risk
    jurisdiction = detect_jurisdiction(facts)
    if not jurisdiction:
        return {"not_found": True, "reason": "No jurisdiction detected in project facts"}

    result = get_jurisdiction_risk(jurisdiction)
    if result is None:
        return {
            "not_found": True,
            "query": jurisdiction,
            "reason": f"No profile found for '{jurisdiction}'",
        }
    return result


@router.post("/tools/convert", response_model=ConvertResponse)
def convert_units(body: ConvertRequest) -> ConvertResponse:
    """Convert a numeric value between mining units."""
    fu = body.from_unit.lower().strip()
    tu = body.to_unit.lower().strip()

    if fu == tu:
        return ConvertResponse(value=body.value, from_unit=fu, to_unit=tu,
                               result=body.value, formula=f"1 {fu} = 1 {tu}")

    row = CONVERSION_FACTORS.get(fu)
    if not row or tu not in row:
        raise HTTPException(
            status_code=422,
            detail=f"No conversion available from '{fu}' to '{tu}'. "
                   f"Supported from '{fu}': {list(row.keys()) if row else 'not found'}"
        )

    factor = row[tu]
    result = body.value * factor
    return ConvertResponse(
        value=body.value,
        from_unit=fu,
        to_unit=tu,
        result=round(result, 8),
        formula=f"1 {fu} = {factor} {tu}",
    )

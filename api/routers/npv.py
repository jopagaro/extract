"""
NPV Refresh router — on-demand commodity price update for DCF estimates.

Endpoint:
  POST /projects/{project_id}/npv-refresh

Fetches current commodity prices via yfinance, compares to prices used in the
last completed run, and interpolates a new NPV from the stored sensitivity curve.
Non-fatal — if the DCF didn't run or sensitivity data is absent, returns the
last-known values with an explanatory note.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from engine.core.paths import project_root, project_runs
from engine.market.live_prices import get_commodity_prices

logger = logging.getLogger(__name__)

router = APIRouter(tags=["npv"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_latest_completed_run(project_id: str) -> str | None:
    """Return the run_id of the most recent completed run, or None."""
    runs_dir = project_runs(project_id)
    if not runs_dir.exists():
        return None
    candidates = []
    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir():
            continue
        status_file = run_dir / "run_status.json"
        if not status_file.exists():
            continue
        try:
            status = json.loads(status_file.read_text())
            if status.get("status") == "complete":
                candidates.append((run_dir.name, status.get("completed_at", "")))
        except Exception:
            continue
    if not candidates:
        return None
    # Sort by completed_at descending; run_id is already lexicographically sortable
    candidates.sort(key=lambda x: (x[1], x[0]), reverse=True)
    return candidates[0][0]


def _load_run_json(project_id: str, run_id: str, filename: str) -> dict | None:
    path = project_runs(project_id) / run_id / filename
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _interpolate_npv(points: list[dict], price_change_pct: float) -> float | None:
    """
    Linearly interpolate NPV from sensitivity points for the commodity_price axis.
    points: list of {axis, change_percent, npv_musd, ...}
    price_change_pct: the % price change to look up
    """
    price_points = sorted(
        [p for p in points if p.get("axis") == "commodity_price"],
        key=lambda p: p["change_percent"],
    )
    if len(price_points) < 2:
        return None

    # Clamp to range
    if price_change_pct <= price_points[0]["change_percent"]:
        return price_points[0].get("npv_musd")
    if price_change_pct >= price_points[-1]["change_percent"]:
        return price_points[-1].get("npv_musd")

    # Find bracketing points
    for i in range(len(price_points) - 1):
        lo, hi = price_points[i], price_points[i + 1]
        lo_pct, hi_pct = lo["change_percent"], hi["change_percent"]
        if lo_pct <= price_change_pct <= hi_pct:
            lo_npv = lo.get("npv_musd")
            hi_npv = hi.get("npv_musd")
            if lo_npv is None or hi_npv is None:
                return None
            t = (price_change_pct - lo_pct) / (hi_pct - lo_pct)
            return round(lo_npv + t * (hi_npv - lo_npv), 2)

    return None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/npv-refresh")
def refresh_npv(project_id: str) -> dict:
    """
    Fetch current commodity prices and estimate the new NPV using the stored
    sensitivity curve from the last completed DCF run.

    Returns:
        new_npv_musd        — interpolated NPV at current prices (null if unavailable)
        last_npv_musd       — NPV from the last run
        npv_delta_pct       — % change in NPV (null if unavailable)
        new_irr_pct         — null (future: re-run IRR)
        last_irr_pct        — IRR from last run
        commodity           — primary commodity detected
        current_price       — live price
        last_price          — price at time of last run (from market intelligence)
        price_change_pct    — % price change since last run
        refreshed_at        — ISO timestamp
        error               — explanatory note if data is missing
    """
    if not project_root(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    refreshed_at = datetime.now(timezone.utc).isoformat()
    result: dict = {
        "new_npv_musd": None,
        "last_npv_musd": None,
        "npv_delta_pct": None,
        "new_irr_pct": None,
        "last_irr_pct": None,
        "commodity": None,
        "current_price": None,
        "last_price": None,
        "price_change_pct": None,
        "refreshed_at": refreshed_at,
        "error": None,
    }

    # 1. Find latest completed run
    run_id = _find_latest_completed_run(project_id)
    if run_id is None:
        result["error"] = "No completed analysis run found for this project."
        return result

    # 2. Load DCF model output
    dcf = _load_run_json(project_id, run_id, "06_dcf_model.json")
    if dcf is None or not dcf.get("model_ran"):
        result["error"] = dcf.get("reason") if dcf else "DCF model output not found."
        return result

    summary = dcf.get("summary", {})
    sensitivity = dcf.get("sensitivity", {})
    result["last_npv_musd"] = summary.get("npv_musd")
    result["last_irr_pct"]  = summary.get("irr_percent")

    # 3. Detect commodity from project facts
    facts = _load_run_json(project_id, run_id, "01_project_facts.json")
    commodity_str = (facts or {}).get("commodity", "gold") or "gold"
    result["commodity"] = commodity_str

    # 4. Get price at time of last analysis (from stored market intelligence)
    mi = _load_run_json(project_id, run_id, "02_market_intelligence.json")
    last_price: float | None = None
    if mi:
        prices_at_run = (mi.get("commodity_prices") or {}).get("prices", {})
        for kw, data in prices_at_run.items():
            if data.get("price") is not None:
                last_price = data["price"]
                commodity_str = kw
                result["commodity"] = kw
                break

    result["last_price"] = last_price

    # 5. Fetch current commodity prices
    try:
        live = get_commodity_prices(commodity_str)
        current_price: float | None = None
        for kw, data in live.get("prices", {}).items():
            if data.get("price") is not None:
                current_price = data["price"]
                if not result["commodity"]:
                    result["commodity"] = kw
                break
        result["current_price"] = current_price
    except Exception as exc:
        logger.warning("Live price fetch failed: %s", exc)
        result["error"] = f"Could not fetch live commodity prices: {exc}"
        return result

    if current_price is None:
        result["error"] = "Live commodity price not available."
        return result

    # 6. Compute % price change and interpolate NPV
    if last_price is not None and last_price > 0:
        price_change_pct = round((current_price - last_price) / last_price * 100, 2)
        result["price_change_pct"] = price_change_pct

        sensitivity_points = sensitivity.get("points", [])
        if sensitivity_points:
            new_npv = _interpolate_npv(sensitivity_points, price_change_pct)
            result["new_npv_musd"] = new_npv

            if new_npv is not None and result["last_npv_musd"] is not None:
                last_npv = result["last_npv_musd"]
                if last_npv != 0:
                    result["npv_delta_pct"] = round((new_npv - last_npv) / abs(last_npv) * 100, 2)
        else:
            result["error"] = (
                "Sensitivity data not available — NPV cannot be re-estimated. "
                "Re-run analysis to generate sensitivity curves."
            )
    else:
        # No last_price means we can't compute a delta, but current_price is available
        result["error"] = (
            "No market intelligence from previous run. "
            "Re-run analysis to establish a price baseline."
        )

    return result

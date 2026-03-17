"""
Breakeven analyzer.

Finds the commodity price, CAPEX multiplier, OPEX multiplier,
or recovery at which NPV = 0.
Uses bisection — no external dependencies.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from engine.core.logging import get_logger
from engine.economics.dcf_model import run_dcf
from engine.economics.models import EconomicsInputBook

log = get_logger(__name__)


def _npv_at_price(inputs: EconomicsInputBook, price: float, commodity: str) -> float:
    modified = deepcopy(inputs)
    modified.commodity_prices = [
        replace(p, price=price) if p.commodity.lower() == commodity.lower() else p
        for p in modified.commodity_prices
    ]
    _, summary = run_dcf(modified)
    return summary.npv_musd


def _bisect(f, low: float, high: float, tolerance: float = 0.01, max_iter: int = 200) -> float | None:
    """Find x where f(x) = 0 using bisection."""
    f_low = f(low)
    f_high = f(high)
    if f_low * f_high > 0:
        return None  # no sign change — no solution in range
    for _ in range(max_iter):
        mid = (low + high) / 2.0
        f_mid = f(mid)
        if abs(f_mid) < tolerance or (high - low) / 2 < tolerance:
            return mid
        if f_low * f_mid < 0:
            high = mid
        else:
            low = mid
            f_low = f_mid
    return None


def breakeven_price(
    inputs: EconomicsInputBook,
    commodity: str,
    *,
    price_low: float = 1.0,
    price_high: float = 10_000.0,
) -> float | None:
    """
    Find the commodity price at which after-tax NPV = 0.
    Returns None if no breakeven exists in the search range.
    """
    log.info("Breakeven price analysis | commodity=%s", commodity)
    result = _bisect(
        lambda p: _npv_at_price(inputs, p, commodity),
        price_low,
        price_high,
    )
    return round(result, 2) if result is not None else None


def breakeven_capex_multiplier(inputs: EconomicsInputBook) -> float | None:
    """
    Find the CAPEX multiplier at which NPV = 0.
    e.g. 1.35 means CAPEX can increase 35% before the project breaks even.
    """
    def npv_at_capex(mult: float) -> float:
        modified = deepcopy(inputs)
        modified.capex_items = [
            replace(i, amount=i.amount * mult) for i in modified.capex_items
        ]
        _, summary = run_dcf(modified)
        return summary.npv_musd

    return _bisect(npv_at_capex, 0.1, 5.0)


def breakeven_opex_multiplier(inputs: EconomicsInputBook) -> float | None:
    """
    Find the OPEX multiplier at which NPV = 0.
    """
    def npv_at_opex(mult: float) -> float:
        modified = deepcopy(inputs)
        opex = modified.opex_assumptions
        modified.opex_assumptions = replace(
            opex,
            mining_cost_per_tonne_ore=opex.mining_cost_per_tonne_ore * mult,
            processing_cost_per_tonne_ore=opex.processing_cost_per_tonne_ore * mult,
            ganda_cost_per_tonne_ore=opex.ganda_cost_per_tonne_ore * mult,
        )
        _, summary = run_dcf(modified)
        return summary.npv_musd

    return _bisect(npv_at_opex, 0.1, 5.0)


def run_breakeven_analysis(inputs: EconomicsInputBook) -> dict:
    """
    Run all breakeven analyses and return a summary dict.
    """
    primary_commodity = (
        inputs.production_schedule[0].commodity
        if inputs.production_schedule else "primary"
    )
    base_price = next(
        (p.price for p in inputs.commodity_prices
         if p.commodity.lower() == primary_commodity.lower()),
        None,
    )

    be_price = breakeven_price(inputs, primary_commodity)
    be_capex = breakeven_capex_multiplier(inputs)
    be_opex = breakeven_opex_multiplier(inputs)

    return {
        "project_id": inputs.project_id,
        "scenario": inputs.scenario,
        "primary_commodity": primary_commodity,
        "base_price": base_price,
        "breakeven_price": be_price,
        "breakeven_price_discount_to_base_pct": (
            round((be_price - base_price) / base_price * 100, 1)
            if be_price and base_price else None
        ),
        "breakeven_capex_multiplier": round(be_capex, 3) if be_capex else None,
        "breakeven_opex_multiplier": round(be_opex, 3) if be_opex else None,
    }

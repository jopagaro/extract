"""
Sensitivity runner.

Varies one input at a time across a range of changes and records
NPV and IRR at each point. Produces the data behind tornado charts
and spider diagrams.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from engine.core.logging import get_logger
from engine.economics.dcf_model import run_dcf
from engine.economics.models import (
    EconomicsInputBook,
    SensitivityPoint,
    SensitivityResult,
)

log = get_logger(__name__)

# Default sensitivity range: ±40% in 10% steps
DEFAULT_STEPS = [-40.0, -30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0, 40.0]


def _apply_change(inputs: EconomicsInputBook, axis: str, change_pct: float) -> EconomicsInputBook:
    """
    Return a modified copy of inputs with one axis changed by change_pct%.
    Does not mutate the original.
    """
    factor = 1.0 + change_pct / 100.0
    inputs = deepcopy(inputs)

    if axis == "commodity_price":
        inputs.commodity_prices = [
            replace(p, price=p.price * factor)
            for p in inputs.commodity_prices
        ]
    elif axis == "capex":
        inputs.capex_items = [
            replace(i, amount=i.amount * factor)
            for i in inputs.capex_items
        ]
    elif axis == "opex":
        opex = inputs.opex_assumptions
        inputs.opex_assumptions = replace(
            opex,
            mining_cost_per_tonne_ore=opex.mining_cost_per_tonne_ore * factor,
            processing_cost_per_tonne_ore=opex.processing_cost_per_tonne_ore * factor,
            ganda_cost_per_tonne_ore=opex.ganda_cost_per_tonne_ore * factor,
        )
    elif axis == "recovery":
        inputs.production_schedule = [
            replace(p, recovery_percent=min(100.0, p.recovery_percent * factor))
            for p in inputs.production_schedule
        ]
    elif axis == "throughput":
        inputs.production_schedule = [
            replace(p, ore_tonnes=p.ore_tonnes * factor)
            for p in inputs.production_schedule
        ]
    elif axis == "discount_rate":
        inputs.discounting = replace(
            inputs.discounting,
            discount_rate_percent=inputs.discounting.discount_rate_percent * factor,
        )
    else:
        log.warning("Unknown sensitivity axis: %s", axis)

    return inputs


def run_sensitivity(
    base_inputs: EconomicsInputBook,
    axes: list[str] | None = None,
    steps: list[float] | None = None,
) -> SensitivityResult:
    """
    Run a full one-at-a-time sensitivity analysis.

    axes: which inputs to vary. Defaults to all standard axes.
    steps: list of percentage changes. Defaults to DEFAULT_STEPS.
    """
    if axes is None:
        axes = ["commodity_price", "capex", "opex", "recovery", "throughput"]
    if steps is None:
        steps = DEFAULT_STEPS

    # Base case
    _, base_summary = run_dcf(base_inputs)
    base_npv = base_summary.npv_musd
    base_irr = base_summary.irr_percent

    points: list[SensitivityPoint] = []

    for axis in axes:
        log.info("Sensitivity axis: %s", axis)
        for step in steps:
            modified = _apply_change(base_inputs, axis, step)
            _, summary = run_dcf(modified)
            points.append(SensitivityPoint(
                axis=axis,
                change_percent=step,
                npv_musd=summary.npv_musd,
                irr_percent=summary.irr_percent,
                payback_years=summary.payback_years,
            ))

    return SensitivityResult(
        project_id=base_inputs.project_id,
        scenario=base_inputs.scenario,
        base_npv_musd=base_npv,
        base_irr_percent=base_irr,
        points=points,
    )

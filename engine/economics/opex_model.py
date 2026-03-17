"""
OPEX model.

Calculates operating costs per production period with optional escalation.
"""

from __future__ import annotations

from engine.economics.models import OpexAssumptions, ProductionPeriod


def calculate_period_opex(
    period: ProductionPeriod,
    opex: OpexAssumptions,
    years_from_start: int = 0,
) -> tuple[float, float, float, float]:
    """
    Calculate operating costs for one period.

    Returns (mining_cost, processing_cost, ganda_cost, total_opex) in USD millions.
    Applies annual escalation if configured.
    """
    escalation_factor = (1 + opex.escalation_rate_percent / 100.0) ** years_from_start

    mining   = period.ore_tonnes * opex.mining_cost_per_tonne_ore * escalation_factor
    process  = period.ore_tonnes * opex.processing_cost_per_tonne_ore * escalation_factor
    ganda    = period.ore_tonnes * opex.ganda_cost_per_tonne_ore * escalation_factor
    total    = mining + process + ganda

    # Convert to USD millions
    return (
        mining   / 1_000_000,
        process  / 1_000_000,
        ganda    / 1_000_000,
        total    / 1_000_000,
    )


def calculate_aisc(
    total_opex_musd: float,
    sustaining_capex_musd: float,
    metal_produced: float,
) -> float | None:
    """
    All-In Sustaining Cost per metal unit.
    Returns None if no metal was produced.
    """
    if metal_produced <= 0:
        return None
    total_cost_usd = (total_opex_musd + sustaining_capex_musd) * 1_000_000
    return total_cost_usd / metal_produced

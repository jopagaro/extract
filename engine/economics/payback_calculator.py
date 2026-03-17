"""
Payback period calculator.

Simple and discounted payback — when cumulative cash flow turns positive.
"""

from __future__ import annotations


def calculate_simple_payback(
    cash_flows: list[float],
    *,
    production_start_year: int = 1,
) -> float | None:
    """
    Simple (undiscounted) payback period in years from first production.

    Returns None if the project never pays back within the cash flow schedule.
    Interpolates within the payback year for fractional results.
    """
    cumulative = 0.0
    for i, cf in enumerate(cash_flows):
        if i < production_start_year:
            # Track capex spent before production
            cumulative += cf
            continue
        prev_cumulative = cumulative
        cumulative += cf
        if cumulative >= 0 and prev_cumulative < 0:
            # Payback occurs within this year — interpolate
            fraction = abs(prev_cumulative) / cf if cf > 0 else 0.0
            years_from_production = (i - production_start_year) + fraction
            return round(years_from_production, 2)

    return None  # never paid back


def calculate_discounted_payback(
    cash_flows: list[float],
    discount_rate_percent: float,
    *,
    production_start_year: int = 1,
    convention: str = "mid_year",
) -> float | None:
    """
    Discounted payback period in years from first production.

    Uses the same discounting convention as the NPV calculation.
    """
    from engine.economics.npv_irr_calculator import calculate_discount_factors

    factors = calculate_discount_factors(
        len(cash_flows), discount_rate_percent, convention
    )
    discounted = [cf * f for cf, f in zip(cash_flows, factors)]
    return calculate_simple_payback(discounted, production_start_year=production_start_year)

"""
NPV and IRR calculator.

Pure functions — no dependencies beyond the standard library.
IRR is solved using the bisection method so numpy is not required.
"""

from __future__ import annotations

import math


def calculate_npv(
    cash_flows: list[float],
    discount_rate_percent: float,
    convention: str = "mid_year",
) -> float:
    """
    Calculate Net Present Value.

    cash_flows: list of annual cash flows. Index 0 = year 0 (construction).
    discount_rate_percent: annual discount rate as a percentage (e.g. 8.0 for 8%).
    convention: "mid_year" (cash flows occur mid-year) or "end_of_year".

    Returns NPV in the same units as the cash_flows.
    """
    r = discount_rate_percent / 100.0
    npv = 0.0
    for i, cf in enumerate(cash_flows):
        if convention == "mid_year" and i > 0:
            exponent = i - 0.5
        else:
            exponent = float(i)
        npv += cf / ((1 + r) ** exponent)
    return npv


def calculate_discount_factors(
    n_periods: int,
    discount_rate_percent: float,
    convention: str = "mid_year",
) -> list[float]:
    """Return a list of discount factors for each period."""
    r = discount_rate_percent / 100.0
    factors = []
    for i in range(n_periods):
        if convention == "mid_year" and i > 0:
            exponent = i - 0.5
        else:
            exponent = float(i)
        factors.append(1.0 / ((1 + r) ** exponent))
    return factors


def calculate_irr(
    cash_flows: list[float],
    *,
    max_iterations: int = 1_000,
    tolerance: float = 1e-6,
) -> float | None:
    """
    Calculate Internal Rate of Return using bisection.

    Returns the IRR as a percentage (e.g. 18.5 for 18.5%).
    Returns None if no solution exists or the project never pays back.

    Searches in the range [0%, 500%] which covers all realistic mining IRRs.
    Using a near-zero lower bound avoids numerical blow-up from late negative
    cash flows (e.g. closure costs) that cause NPV to diverge at negative rates.
    """
    def npv_at_rate(r: float) -> float:
        return sum(cf / ((1 + r) ** i) for i, cf in enumerate(cash_flows))

    # IRR requires at least one sign change in the cash flow series
    if all(cf >= 0 for cf in cash_flows) or all(cf <= 0 for cf in cash_flows):
        return None

    # Search between 0% and 500% (r=0.0 to r=5.0)
    # At r=0 NPV = sum of all cash flows (must be positive for IRR to exist above 0%)
    # At r=5.0 (500%) early construction capex dominates and NPV is strongly negative
    low, high = 0.0, 5.0
    npv_low = npv_at_rate(low)
    npv_high = npv_at_rate(high)

    if npv_low * npv_high > 0:
        # No sign change in [0%, 500%] — IRR does not exist in a meaningful range
        return None

    for _ in range(max_iterations):
        mid = (low + high) / 2.0
        npv_mid = npv_at_rate(mid)

        if abs(npv_mid) < tolerance or (high - low) / 2.0 < tolerance:
            return mid * 100.0  # return as percentage

        if npv_low * npv_mid < 0:
            high = mid
        else:
            low = mid
            npv_low = npv_mid

    return None  # did not converge


def calculate_multiple_on_invested_capital(
    cash_flows: list[float],
) -> float | None:
    """
    MOIC — total cash returned divided by total capital invested.
    Returns None if no capital was invested.
    """
    invested = sum(abs(cf) for cf in cash_flows if cf < 0)
    returned = sum(cf for cf in cash_flows if cf > 0)
    if invested == 0:
        return None
    return returned / invested

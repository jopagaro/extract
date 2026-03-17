"""
Revenue model.

Calculates gross revenue, royalties, and net revenue per period
from production and commodity price assumptions.
Handles NSR royalties, gross revenue royalties, and streaming.
"""

from __future__ import annotations

from engine.economics.models import (
    CommodityPrice,
    ProductionPeriod,
    RoyaltyTerm,
)


def _price_for_commodity(
    commodity: str,
    prices: list[CommodityPrice],
) -> float:
    """Return the price for a commodity. Returns 0.0 if not found."""
    for p in prices:
        if p.commodity.lower() == commodity.lower():
            return p.price
    return 0.0


def calculate_gross_revenue(
    period: ProductionPeriod,
    prices: list[CommodityPrice],
) -> float:
    """
    Gross revenue = primary metal produced × price
                  + sum of secondary metal produced × price
    """
    primary_price = _price_for_commodity(period.commodity, prices)
    primary_revenue = period.contained_metal_produced * primary_price

    secondary_revenue = 0.0
    for sec in period.secondary_production:
        sec_price = _price_for_commodity(sec.get("commodity", ""), prices)
        secondary_revenue += sec.get("produced", 0.0) * sec_price

    return primary_revenue + secondary_revenue


def calculate_royalties(
    gross_revenue: float,
    royalties: list[RoyaltyTerm],
    net_revenue: float | None = None,
) -> float:
    """
    Calculate total royalty payments for the period.

    NSR royalties apply to net smelter return (≈ gross revenue after refining).
    Gross revenue royalties apply before any deductions.
    Net profit royalties apply to net profit (handled at tax level — not here).
    """
    total = 0.0
    for r in royalties:
        basis = r.basis.lower()
        if basis in ("nsr", "gross_revenue", "revenue"):
            total += gross_revenue * (r.rate_percent / 100.0)
        # net_profit royalties calculated post-tax — skipped here
    return total


def calculate_period_revenue(
    period: ProductionPeriod,
    prices: list[CommodityPrice],
    royalties: list[RoyaltyTerm],
) -> tuple[float, float, float]:
    """
    Returns (gross_revenue, royalties_paid, net_revenue) for one period.
    All values in USD millions.
    """
    # Prices are typically in USD/oz or USD/lb — revenue comes out in USD
    # Divide by 1_000_000 to convert to USD millions
    gross = calculate_gross_revenue(period, prices) / 1_000_000
    royalties_paid = calculate_royalties(gross, royalties)
    net = gross - royalties_paid
    return gross, royalties_paid, net

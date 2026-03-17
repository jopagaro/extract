"""
CAPEX model.

Schedules capital expenditures by year and category.
"""

from __future__ import annotations

from collections import defaultdict

from engine.economics.models import CapexItem


def build_capex_schedule(
    capex_items: list[CapexItem],
) -> dict[int, dict[str, float]]:
    """
    Group CAPEX items by year and category.

    Returns: {year: {"initial": x, "sustaining": y, "closure": z, "total": t}}
    """
    schedule: dict[int, dict[str, float]] = defaultdict(
        lambda: {"initial": 0.0, "sustaining": 0.0, "closure": 0.0, "expansion": 0.0, "total": 0.0}
    )
    for item in capex_items:
        cat = item.category.lower()
        schedule[item.year][cat] = schedule[item.year].get(cat, 0.0) + item.amount
        schedule[item.year]["total"] += item.amount

    return dict(schedule)


def get_depreciable_base(capex_items: list[CapexItem]) -> float:
    """
    Return the total initial capital that is subject to depreciation.
    Excludes closure/reclamation costs (treated separately).
    """
    return sum(
        i.amount for i in capex_items
        if i.category.lower() in ("initial", "expansion")
    )


def get_total_by_category(capex_items: list[CapexItem]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for item in capex_items:
        totals[item.category.lower()] += item.amount
    return dict(totals)

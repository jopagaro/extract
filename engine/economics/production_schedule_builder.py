"""
Production schedule builder.

Calculates contained metal produced per period from ore, grade, and recovery.
Handles multiple commodities and unit conversions.
"""

from __future__ import annotations

from engine.economics.models import ProductionPeriod

# Conversion factors to a common base unit per commodity type
_GRADE_TO_METAL: dict[str, float] = {
    # grade unit → multiply by ore_tonnes to get metal in base unit
    "g/t":  1.0,            # → grams
    "ppm":  1.0,            # same as g/t
    "%":    10_000.0,       # → grams per tonne at 1% = 10,000 g/t equiv
    "oz/t": 31.1035,        # → grams (troy oz per short ton is different but we use metric)
}

_METAL_UNIT_DIVISOR: dict[str, float] = {
    # base grams → target unit
    "g":    1.0,
    "kg":   1_000.0,
    "t":    1_000_000.0,
    "oz":   31.1035,        # grams per troy oz
    "koz":  31_103.5,
    "Moz":  31_103_500.0,
    "lb":   453.592,
    "klb":  453_592.0,
    "Mlb":  453_592_000.0,
}


def calculate_contained_metal(
    ore_tonnes: float,
    head_grade: float,
    grade_unit: str,
    recovery_percent: float,
    metal_unit: str,
) -> float:
    """
    Calculate contained metal produced from ore, grade, and recovery.

    Formula: ore_tonnes × head_grade × recovery × unit_conversion

    Returns metal produced in the specified metal_unit.
    """
    grade_factor = _GRADE_TO_METAL.get(grade_unit, 1.0)
    metal_divisor = _METAL_UNIT_DIVISOR.get(metal_unit, 1.0)

    contained_raw = ore_tonnes * head_grade * grade_factor  # in grams (for precious metals)
    recovered = contained_raw * (recovery_percent / 100.0)
    return recovered / metal_divisor


def build_production_schedule(
    periods: list[ProductionPeriod],
) -> list[ProductionPeriod]:
    """
    Fill in contained_metal_produced for each period.
    Returns the same list with the derived field populated.
    Does not mutate input — returns new objects.

    If contained_metal_produced is already set (> 0) on a period, it is used
    as-is and the grade/recovery formula is skipped. This allows callers to
    pass in values sourced directly from extraction rather than re-deriving them.
    """
    from dataclasses import replace
    result: list[ProductionPeriod] = []
    for p in periods:
        if p.contained_metal_produced > 0:
            result.append(p)
        else:
            metal = calculate_contained_metal(
                ore_tonnes=p.ore_tonnes,
                head_grade=p.head_grade,
                grade_unit=p.grade_unit,
                recovery_percent=p.recovery_percent,
                metal_unit=p.metal_unit,
            )
            result.append(replace(p, contained_metal_produced=metal))
    return result

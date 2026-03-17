"""
Resource summary builder.

The most critical link between geology and economics.

Takes the ResourceEstimate and mine plan assumptions, applies dilution
and mining recovery factors, and builds the ProductionPeriod list that
feeds directly into the DCF model.

This is where geological confidence directly constrains economics:
- Only Measured + Indicated can support FS-level mine plans
- Inferred resources flag as a risk — cannot be the basis of economic conclusions
- Grade variability across domains affects head grade assumptions
- Dilution and mining recovery reduce the in-situ resource to a mineable reserve
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.core.logging import get_logger
from engine.economics.models import ProductionPeriod
from engine.geology.models import GeologicalDomain, ResourceEstimate

log = get_logger(__name__)


@dataclass
class MinePlanAssumptions:
    """
    Assumptions applied when converting a resource to a mine plan.
    These come from engineering — either from a study or as order-of-magnitude estimates.
    """
    annual_throughput_tonnes: float       # ore tonnes processed per year
    mine_type: str                        # "open_pit", "underground", "heap_leach"
    mining_recovery_percent: float        # ore recovery from in-situ resource
    mining_dilution_percent: float        # waste diluted into ore stream
    dilution_grade: float                 # grade of diluting material
    metallurgical_recovery_percent: float # from testwork
    ramp_up_years: int = 1                # years to reach full throughput
    ramp_up_rate_percent: float = 70.0    # throughput as % of full rate in ramp-up years


def build_production_schedule_from_resource(
    resource: ResourceEstimate,
    mine_plan: MinePlanAssumptions,
    domains: list[GeologicalDomain] | None = None,
) -> tuple[list[ProductionPeriod], list[str]]:
    """
    Convert a resource estimate into a production schedule for the DCF model.

    Returns:
        schedule   — list of ProductionPeriod, one per year
        warnings   — list of data quality / assumption warnings

    Key geological constraints applied:
    - Only M&I used as mineable base (Inferred flagged as warning)
    - Dilution reduces effective head grade
    - Mining recovery reduces total mineable tonnes
    - Grade variability across domains noted in warnings
    """
    warnings: list[str] = []

    # --- Step 1: Establish mineable tonnes and grade ---

    # M&I is the bankable base
    mi_tonnes, mi_grade, mi_metal = resource.total_by_category("measured")
    ind_tonnes, ind_grade, ind_metal = resource.total_by_category("indicated")

    total_mi_t = (mi_tonnes + ind_tonnes) * 1_000_000  # convert Mt to tonnes
    total_mi_metal = mi_metal + ind_metal

    # Weighted average M&I grade
    if total_mi_t > 0:
        avg_mi_grade = (mi_tonnes * mi_grade + ind_tonnes * ind_grade) / (mi_tonnes + ind_tonnes)
    else:
        avg_mi_grade = 0.0
        warnings.append(
            "No Measured or Indicated resources found. "
            "Production schedule cannot be built from resource data alone. "
            "Manual inputs required."
        )
        return [], warnings

    # Check for Inferred — flag but don't use in schedule
    inf_tonnes, inf_grade, inf_metal = resource.total_by_category("inferred")
    if inf_tonnes > 0:
        warnings.append(
            f"Inferred resource of {inf_tonnes:.1f} Mt at {inf_grade:.2f} {resource.primary_element} "
            f"is NOT included in the production schedule. Inferred resources carry insufficient "
            f"confidence to support mine planning under NI 43-101 or JORC. "
            f"If converted to M&I, this represents potential upside."
        )

    # --- Step 2: Apply mining factors ---

    # Mining recovery: what fraction of the in-situ M&I is actually mined
    mineable_tonnes = total_mi_t * (mine_plan.mining_recovery_percent / 100.0)

    # Dilution: diluting material blended into ore
    dilution_factor = mine_plan.mining_dilution_percent / 100.0
    diluted_ore_tonnes = mineable_tonnes / (1 - dilution_factor)

    # Effective head grade after dilution
    diluted_grade = (
        avg_mi_grade * (1 - dilution_factor) +
        mine_plan.dilution_grade * dilution_factor
    )

    log.info(
        "Resource → mine plan | M&I=%.1fMt @ %.2f %s | "
        "Mineable=%.1fMt | Diluted head grade=%.2f",
        total_mi_t / 1_000_000, avg_mi_grade, resource.primary_element,
        diluted_ore_tonnes / 1_000_000, diluted_grade,
    )

    # --- Step 3: Grade variability warning ---
    if domains:
        grades = [d.mean_grade for d in domains if d.mean_grade is not None]
        if len(grades) > 1:
            grade_range = max(grades) - min(grades)
            avg = sum(grades) / len(grades)
            cv = grade_range / avg if avg > 0 else 0
            if cv > 0.5:
                warnings.append(
                    f"Grade variability across {len(domains)} geological domains is high "
                    f"(range: {min(grades):.2f}–{max(grades):.2f} {resource.primary_element}). "
                    f"The average head grade assumption may not represent individual mining zones. "
                    f"Domain-by-domain scheduling is recommended."
                )

    # --- Step 4: Build annual production schedule ---

    total_life_years = diluted_ore_tonnes / mine_plan.annual_throughput_tonnes
    mine_life_years = max(1, round(total_life_years))

    if abs(total_life_years - mine_life_years) > 0.5:
        warnings.append(
            f"Mine life of {total_life_years:.1f} years rounded to {mine_life_years} years. "
            f"The final year will have lower throughput than shown."
        )

    schedule: list[ProductionPeriod] = []

    for year_idx in range(mine_life_years):
        production_year = year_idx + 1  # year 0 = construction

        # Apply ramp-up in first N years
        if year_idx < mine_plan.ramp_up_years:
            throughput = mine_plan.annual_throughput_tonnes * (mine_plan.ramp_up_rate_percent / 100.0)
        else:
            # Last year may have partial ore
            remaining = diluted_ore_tonnes - (mine_plan.annual_throughput_tonnes * max(0, year_idx - mine_plan.ramp_up_years) +
                                               mine_plan.annual_throughput_tonnes * (mine_plan.ramp_up_rate_percent / 100.0) * min(year_idx, mine_plan.ramp_up_years))
            throughput = min(mine_plan.annual_throughput_tonnes, remaining)
            throughput = max(throughput, 0.0)

        schedule.append(ProductionPeriod(
            year=production_year,
            ore_tonnes=throughput,
            head_grade=diluted_grade,
            grade_unit=resource.primary_element,
            recovery_percent=mine_plan.metallurgical_recovery_percent,
            commodity=resource.primary_element,
            metal_unit=_infer_metal_unit(resource.primary_element),
        ))

    return schedule, warnings


def _infer_metal_unit(element: str) -> str:
    """Infer the most common reporting unit for a given element."""
    precious = {"au", "ag", "pt", "pd", "gold", "silver", "platinum", "palladium"}
    base_percent = {"cu", "zn", "pb", "ni", "copper", "zinc", "lead", "nickel"}
    if element.lower() in precious:
        return "oz"
    if element.lower() in base_percent:
        return "t"   # tonnes of contained metal
    return "t"

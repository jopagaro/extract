"""
Continuity analyzer.

Assesses the geological continuity of mineralisation from drillhole data.
Continuity is one of the most important inputs to resource classification —
it determines whether Measured, Indicated, or Inferred is appropriate,
and directly affects the reliability of grade and tonnage assumptions.
"""

from __future__ import annotations

from engine.core.enums import DataStatus, EconomicDirection
from engine.geology.models import GeologicalDomain, GeologicalRisk


def assess_drill_spacing(
    average_spacing_m: float,
    mine_type: str,
    study_level: str,
) -> tuple[str, GeologicalRisk]:
    """
    Assess whether drill spacing supports the study level and mine type.

    Industry benchmarks (approximate):
        Open pit Measured:    25–50 m spacing
        Open pit Indicated:   50–100 m spacing
        Open pit Inferred:    >100 m spacing
        Underground Measured: 15–25 m spacing
        Underground Indicated:25–50 m spacing

    Returns (classification_supported, risk)
    """
    pit_benchmarks = {"measured": 50, "indicated": 100, "inferred": 999}
    ug_benchmarks  = {"measured": 25, "indicated": 50,  "inferred": 999}

    benchmarks = ug_benchmarks if "underground" in mine_type.lower() else pit_benchmarks

    # What classification does this spacing support?
    if average_spacing_m <= benchmarks["measured"]:
        supported = "Measured"
    elif average_spacing_m <= benchmarks["indicated"]:
        supported = "Indicated"
    else:
        supported = "Inferred"

    # What does the study level require?
    study_needs = {
        "fs": "Measured/Indicated", "pfs": "Measured/Indicated",
        "pea": "Indicated", "scoping": "Inferred",
    }
    required = study_needs.get(study_level.lower(), "Indicated")

    adequate = (
        (study_level.lower() in ("scoping", "pea") and supported in ("Measured", "Indicated", "Inferred")) or
        (study_level.lower() in ("pfs", "fs") and supported in ("Measured", "Indicated"))
    )

    direction = EconomicDirection.NEUTRAL if adequate else EconomicDirection.NEGATIVE
    assessment = (
        f"Average drill spacing of {average_spacing_m:.0f} m supports {supported}-level resource "
        f"classification for a {mine_type.replace('_', ' ')} operation. "
        + (
            f"This is adequate for a {study_level.upper()} study."
            if adequate else
            f"A {study_level.upper()} study typically requires tighter spacing. "
            f"Additional infill drilling is needed to upgrade resource confidence. "
            f"Using the current data as the basis for {study_level.upper()}-level economics "
            f"introduces material estimation uncertainty and is a negative economic risk factor."
        )
    )

    risk = GeologicalRisk(
        risk_id="drill_spacing_continuity",
        category="continuity",
        description=f"Drill spacing of {average_spacing_m:.0f} m assessed against {study_level.upper()} requirements",
        economic_direction=direction.value,
        assessment=assessment,
        impacts=["resource_classification", "production_schedule", "npv_reliability"],
        recommended_action=None if adequate else "Conduct infill drilling to reduce average spacing.",
        severity="high" if not adequate else "low",
    )

    return supported, risk


def assess_grade_variability(domain: GeologicalDomain) -> GeologicalRisk | None:
    """
    Assess grade variability within a domain.

    High CV (coefficient of variation) indicates erratic grade distribution
    that is difficult to estimate and increases the risk of grade over/understatement.
    """
    if domain.cv is None:
        return GeologicalRisk(
            risk_id=f"grade_variability_{domain.domain_id}",
            category="grade_variability",
            description=f"Grade variability not quantified for domain {domain.name}",
            economic_direction=EconomicDirection.NEGATIVE.value,
            assessment=(
                f"Coefficient of variation has not been calculated for domain '{domain.name}'. "
                f"Without this metric, the statistical reliability of the grade estimate cannot "
                f"be assessed. This is a data gap that should be resolved before the resource "
                f"estimate is used as the basis for economic modelling."
            ),
            impacts=["resource_grade", "head_grade_assumption"],
            recommended_action="Calculate CV for each domain from assay composites.",
            severity="medium",
        )

    if domain.cv < 0.5:
        direction = EconomicDirection.POSITIVE
        severity = "low"
        assessment = (
            f"Grade variability in domain '{domain.name}' is low (CV = {domain.cv:.2f}), "
            f"indicating a relatively uniform grade distribution. "
            f"This supports reliable grade estimation and reduces the risk of "
            f"significant deviation between estimated and mined grades. "
            f"This is a positive factor for economic model reliability."
        )
    elif domain.cv < 1.0:
        direction = EconomicDirection.NEUTRAL
        severity = "medium"
        assessment = (
            f"Grade variability in domain '{domain.name}' is moderate (CV = {domain.cv:.2f}). "
            f"Some grade smoothing in the resource model may be appropriate. "
            f"Head grade assumptions should be treated as estimates with meaningful uncertainty bands."
        )
    else:
        direction = EconomicDirection.NEGATIVE
        severity = "high"
        assessment = (
            f"Grade variability in domain '{domain.name}' is high (CV = {domain.cv:.2f}), "
            f"indicating an erratic or nugget-prone grade distribution. "
            f"High-grade outliers may inflate the estimated mean grade, which would result in "
            f"overstated revenue in the economic model. This is a material negative risk. "
            f"High-cut grade treatment and robust estimation methods should be confirmed with "
            f"the Qualified Person before these grades are used in economic calculations."
        )

    return GeologicalRisk(
        risk_id=f"grade_variability_{domain.domain_id}",
        category="grade_variability",
        description=f"Grade variability assessment for domain {domain.name} (CV={domain.cv:.2f})",
        economic_direction=direction.value,
        assessment=assessment,
        impacts=["head_grade_assumption", "revenue_model"],
        severity=severity,
    )


def assess_inferred_proportion(
    inferred_tonnes_mt: float,
    total_mi_tonnes_mt: float,
) -> GeologicalRisk | None:
    """
    Assess what proportion of the total resource is Inferred.

    Inferred resources cannot form the basis of a FS or PFS mine plan.
    A high Inferred proportion relative to M&I is a risk for economics
    that depend on that tonnage being mineable.
    """
    if total_mi_tonnes_mt <= 0:
        return None

    inferred_pct = inferred_tonnes_mt / (total_mi_tonnes_mt + inferred_tonnes_mt) * 100

    if inferred_pct < 20:
        return None  # not material

    direction = EconomicDirection.MIXED if inferred_pct < 50 else EconomicDirection.NEGATIVE
    assessment = (
        f"Inferred resources represent {inferred_pct:.0f}% of the total resource. "
        f"Inferred material cannot be included in a PFS or FS mine plan under NI 43-101 or JORC. "
        + (
            "The current economic model is based on M&I resources only. "
            f"If the Inferred resource is successfully upgraded through infill drilling, "
            f"mine life and NPV could increase materially — this is a potential upside."
            if inferred_pct < 50 else
            "The majority of the resource base is Inferred, which limits the credibility of "
            "economic projections and the ability to attract project financing. "
            "Significant infill drilling is required before a robust economic study can be completed."
        )
    )

    return GeologicalRisk(
        risk_id="inferred_resource_proportion",
        category="resource",
        description=f"Inferred resources are {inferred_pct:.0f}% of total resource",
        economic_direction=direction.value,
        assessment=assessment,
        impacts=["mine_life", "production_schedule", "npv"],
        recommended_action="Infill drill to convert Inferred to Indicated.",
        severity="high" if inferred_pct >= 50 else "medium",
    )

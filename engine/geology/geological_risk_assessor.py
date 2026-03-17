"""
Geological risk assessor.

Assembles all geological risk flags into a unified GeologicalRisk list
and generates the data_assessments compatible output that feeds the
critic's review and the report's risk section.

This is the geological equivalent of what the critic does for compliance —
it systematically checks every geological assumption for weaknesses.
"""

from __future__ import annotations

from engine.core.enums import DataStatus, EconomicDirection
from engine.core.logging import get_logger
from engine.geology.continuity_analyzer import (
    assess_drill_spacing,
    assess_grade_variability,
    assess_inferred_proportion,
)
from engine.geology.models import (
    GeologicalDomain,
    GeologicalPicture,
    GeologicalRisk,
    ResourceEstimate,
)

log = get_logger(__name__)


def assess_geological_picture(
    picture: GeologicalPicture,
    mine_type: str = "open_pit",
    study_level: str = "pea",
) -> list[dict]:
    """
    Run all geological risk assessments and return a list of data assessment dicts
    compatible with data_assessments.json.

    These feed directly into the critic's review and the report risk section.
    """
    assessments: list[dict] = []
    resource = picture.resource_estimate

    # --- Resource estimate present? ---
    if resource is None:
        assessments.append({
            "field": "geology.resource_estimate",
            "status": DataStatus.MISSING.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                "No mineral resource estimate has been provided or extracted. "
                "The resource estimate is the single most important geological input — "
                "it defines the ore tonnes, grade, and classification that the production "
                "schedule and all economic projections depend on. "
                "Without it, the economic model is entirely assumption-based and has no "
                "geological grounding. All economic outputs should be treated as illustrative only "
                "until a resource estimate is provided."
            ),
            "impacts": ["production_schedule", "mine_life", "revenue_model", "npv", "irr"],
            "recommended_action": "Provide a resource estimate (NI 43-101 or JORC compliant) "
                                  "or extract one from a technical report.",
        })
        return assessments

    # --- Effective date ---
    if resource.effective_date is None:
        assessments.append({
            "field": "geology.resource_estimate.effective_date",
            "status": DataStatus.MISSING.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                "The effective date of the resource estimate has not been recorded. "
                "An undated resource estimate cannot be assessed for currency. "
                "Resource estimates can become stale if significant drilling has occurred "
                "since the estimate was completed, or if geological interpretation has changed. "
                "The date must be confirmed before the estimate is used in economic modelling."
            ),
            "impacts": ["resource_reliability"],
            "recommended_action": "Confirm and record the effective date of the resource estimate.",
        })

    # --- Qualified Person ---
    if resource.qualified_person is None:
        assessments.append({
            "field": "geology.resource_estimate.qualified_person",
            "status": DataStatus.MISSING.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                "No Qualified Person (QP) has been identified for the resource estimate. "
                "Under NI 43-101 and JORC, a resource estimate must be prepared or reviewed "
                "by a QP with relevant experience. Without QP identification, the estimate "
                "cannot be considered compliant and may not be acceptable for regulatory filings "
                "or project financing."
            ),
            "impacts": ["resource_compliance", "financing_risk"],
            "recommended_action": "Identify and record the QP name and credentials.",
        })

    # --- M&I tonnes ---
    mi_t, mi_g, mi_metal = resource.total_by_category("measured")
    ind_t, ind_g, ind_metal = resource.total_by_category("indicated")
    total_mi = mi_t + ind_t

    if total_mi <= 0:
        assessments.append({
            "field": "geology.resource_estimate.measured_indicated_tonnes",
            "status": DataStatus.MISSING.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                "No Measured or Indicated resources have been identified. "
                "Without M&I resources, a credible mine plan and economic study cannot be constructed. "
                "Only Inferred or lower-confidence material is present, which is insufficient "
                "for project financing or advanced economic studies."
            ),
            "impacts": ["production_schedule", "mine_life", "npv"],
            "recommended_action": "Drill sufficient holes to support M&I classification.",
        })
    else:
        assessments.append({
            "field": "geology.resource_estimate.measured_indicated_tonnes",
            "status": DataStatus.PRESENT.value,
            "economic_direction": EconomicDirection.POSITIVE.value,
            "assessment": (
                f"The project has {total_mi:.1f} Mt of Measured and Indicated resources "
                f"at {((mi_t*mi_g + ind_t*ind_g)/total_mi):.2f} {resource.primary_element} "
                f"(weighted average grade). This M&I base supports mine planning and provides "
                f"the geological foundation for the economic model."
            ),
            "impacts": ["production_schedule"],
        })

    # --- Inferred proportion ---
    inf_t, _, _ = resource.total_by_category("inferred")
    inferred_risk = assess_inferred_proportion(inf_t, total_mi)
    if inferred_risk:
        assessments.append(_risk_to_assessment(inferred_risk, "geology.resource_estimate.inferred_proportion"))

    # --- Domain-level grade variability ---
    for domain in picture.domains:
        cv_risk = assess_grade_variability(domain)
        if cv_risk:
            assessments.append(_risk_to_assessment(
                cv_risk, f"geology.domains.{domain.domain_id}.grade_variability"
            ))

    # --- Drill spacing ---
    spacing_risks = [
        d.average_drill_spacing_m for d in picture.domains
        if d.average_drill_spacing_m is not None
    ]
    if spacing_risks:
        avg_spacing = sum(spacing_risks) / len(spacing_risks)
        _, spacing_risk = assess_drill_spacing(avg_spacing, mine_type, study_level)
        assessments.append(_risk_to_assessment(spacing_risk, "geology.drilling.average_spacing"))
    else:
        assessments.append({
            "field": "geology.drilling.average_spacing",
            "status": DataStatus.MISSING.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                "Average drill hole spacing has not been recorded. "
                "Drill spacing is a key input to resource classification — it determines "
                "whether Measured, Indicated, or Inferred classification is appropriate. "
                "Without this data, the confidence level of the resource estimate cannot "
                "be independently assessed."
            ),
            "impacts": ["resource_classification", "production_schedule_reliability"],
            "recommended_action": "Calculate and record average drill spacing per domain.",
        })

    # --- Deposit model ---
    if picture.deposit_model is None:
        assessments.append({
            "field": "geology.deposit_model",
            "status": DataStatus.MISSING.value,
            "economic_direction": EconomicDirection.NEUTRAL.value,
            "assessment": (
                "A deposit model hypothesis has not been recorded. "
                "The deposit model informs the likely mining method, depth extent, "
                "and structural controls — all of which have direct economic implications. "
                "This is an interpretive gap rather than a data gap, but it should be "
                "addressed by a geologist familiar with the project."
            ),
            "impacts": ["mine_type_assumption", "capex_basis"],
            "recommended_action": "Have a geologist document the deposit model interpretation.",
        })

    log.info("Geological risk assessment complete | %d assessments generated", len(assessments))
    return assessments


def _risk_to_assessment(risk: GeologicalRisk, field: str) -> dict:
    return {
        "field": field,
        "status": DataStatus.PRESENT.value,
        "economic_direction": risk.economic_direction,
        "assessment": risk.assessment,
        "impacts": risk.impacts,
        "recommended_action": risk.recommended_action,
    }

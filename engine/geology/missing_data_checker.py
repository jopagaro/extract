"""
Missing data checker for geology.

Systematically checks every expected geological data field and generates
a prioritised list of what is missing, why it matters, and what to collect.

This runs at the start of every analysis so analysts always know exactly
what data gaps exist before outputs are generated.
"""

from __future__ import annotations

from engine.core.enums import DataStatus, EconomicDirection
from engine.geology.models import GeologicalPicture


# Every field we expect in a complete geological picture, with its priority
# and economic consequence if missing.
EXPECTED_FIELDS: list[dict] = [
    {
        "field": "geology.drillhole_data.collars",
        "priority": "critical",
        "economic_direction": EconomicDirection.NEGATIVE.value,
        "assessment_if_missing": (
            "Drillhole collar data has not been provided. Collar locations define the "
            "spatial framework of all subsurface data. Without collars, no geological "
            "interpretation, resource estimation, or mine planning is possible. "
            "This is the most fundamental geological dataset required."
        ),
        "recommended_action": "Provide collar CSV with hole_id, easting, northing, elevation, azimuth, dip, total_depth.",
    },
    {
        "field": "geology.drillhole_data.assays",
        "priority": "critical",
        "economic_direction": EconomicDirection.NEGATIVE.value,
        "assessment_if_missing": (
            "Assay data has not been provided. Assays define the grade of mineralisation "
            "within each drillhole — without them, the resource grade and contained metal "
            "cannot be estimated. All grade-dependent economic outputs are without foundation."
        ),
        "recommended_action": "Provide assay CSV with hole_id, from_m, to_m, element, grade.",
    },
    {
        "field": "geology.drillhole_data.surveys",
        "priority": "high",
        "economic_direction": EconomicDirection.NEGATIVE.value,
        "assessment_if_missing": (
            "Downhole survey data has not been provided. Survey data corrects for drillhole "
            "deviation — without it, the 3D position of assay intervals cannot be accurately "
            "reconstructed, which introduces spatial error into the resource model. "
            "This is particularly important for deep holes and steeply-dipping deposits."
        ),
        "recommended_action": "Provide survey CSV with hole_id, depth_m, azimuth, dip.",
    },
    {
        "field": "geology.drillhole_data.lithology",
        "priority": "high",
        "economic_direction": EconomicDirection.NEUTRAL.value,
        "assessment_if_missing": (
            "Lithology logs have not been provided. Lithology defines the rock types hosting "
            "the mineralisation and is used to establish geological domains for resource "
            "estimation. Without lithology, domain boundaries must be inferred from grades alone, "
            "which reduces the geological rigour of the resource model."
        ),
        "recommended_action": "Provide lithology logs with hole_id, from_m, to_m, rock_code.",
    },
    {
        "field": "geology.resource_estimate",
        "priority": "critical",
        "economic_direction": EconomicDirection.NEGATIVE.value,
        "assessment_if_missing": (
            "No resource estimate has been provided. The resource is the foundation of the "
            "production schedule and all economic calculations. Without it, economic outputs "
            "are entirely assumption-based."
        ),
        "recommended_action": "Provide a resource statement or extract one from a technical report.",
    },
    {
        "field": "geology.metallurgy.recovery",
        "priority": "critical",
        "economic_direction": EconomicDirection.NEGATIVE.value,
        "assessment_if_missing": (
            "Metallurgical recovery data has not been provided. Recovery directly determines "
            "how much of the in-situ grade is converted to saleable metal. A 10% change in "
            "recovery assumption has an approximately proportional effect on revenue. "
            "Without testwork-based recovery data, any recovery assumption is speculative "
            "and represents a material risk to economic projections."
        ),
        "recommended_action": "Provide metallurgical testwork results or recovery assumptions from a study.",
    },
    {
        "field": "geology.domain_model",
        "priority": "medium",
        "economic_direction": EconomicDirection.NEUTRAL.value,
        "assessment_if_missing": (
            "Geological domain model has not been provided. Domains are used to separate "
            "zones with distinct grade distributions and ensure statistically appropriate "
            "resource estimation. Without domain constraints, grade estimation may mix "
            "populations with different mineralisation styles."
        ),
        "recommended_action": "Define geological domains based on lithology, alteration, and grade distribution.",
    },
    {
        "field": "geology.qaqc",
        "priority": "medium",
        "economic_direction": EconomicDirection.NEGATIVE.value,
        "assessment_if_missing": (
            "QAQC data (standards, blanks, duplicates) has not been provided. "
            "Without QAQC verification, the accuracy and precision of the assay database "
            "cannot be independently assessed. Undetected laboratory errors or sample "
            "contamination could systematically bias grade estimates in either direction."
        ),
        "recommended_action": "Provide QAQC summary or raw standards/blanks/duplicates data.",
    },
    {
        "field": "geology.structural_data",
        "priority": "low",
        "economic_direction": EconomicDirection.NEUTRAL.value,
        "assessment_if_missing": (
            "Structural geology data has not been provided. Structural controls on "
            "mineralisation affect the continuity and orientation of ore zones. "
            "While not always required for early-stage economic studies, structural "
            "data is important for underground mine design and for understanding "
            "potential dilution sources."
        ),
        "recommended_action": "Collect structural measurements during logging.",
    },
]


def check_missing_geological_data(picture: GeologicalPicture) -> list[dict]:
    """
    Check the geological picture against expected fields.
    Returns a list of data assessments for missing or incomplete fields.
    """
    assessments: list[dict] = []

    has_resource = picture.resource_estimate is not None
    has_domains = len(picture.domains) > 0
    has_drillholes = (picture.drillhole_count or 0) > 0

    field_present = {
        "geology.drillhole_data.collars": has_drillholes,
        "geology.drillhole_data.assays": has_drillholes,
        "geology.drillhole_data.surveys": has_drillholes,
        "geology.drillhole_data.lithology": has_drillholes,
        "geology.resource_estimate": has_resource,
        "geology.metallurgy.recovery": (
            has_resource and picture.resource_estimate is not None
        ),
        "geology.domain_model": has_domains,
        "geology.qaqc": False,         # always flag until QAQC data is verified
        "geology.structural_data": False,  # low priority, flag but don't alarm
    }

    for expected in EXPECTED_FIELDS:
        field = expected["field"]
        present = field_present.get(field, False)

        if not present:
            assessments.append({
                "field": field,
                "status": DataStatus.MISSING.value,
                "economic_direction": expected["economic_direction"],
                "assessment": expected["assessment_if_missing"],
                "impacts": [],
                "recommended_action": expected["recommended_action"],
                "priority": expected["priority"],
            })

    return assessments

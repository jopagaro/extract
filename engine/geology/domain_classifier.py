"""
Domain classifier.

Assigns composites and assay intervals to geological domains based on
lithology, alteration, and/or grade thresholds.

In a full resource estimation workflow, domain boundaries are defined by
3D wireframes from geological modelling software. Here, without 3D geometry,
we classify using available drillhole attributes:
  - Rock code / lithology
  - Alteration type
  - Grade thresholds (e.g. oxide vs. sulphide based on cut-off)
  - Manual domain codes where already logged

The output feeds into drillhole_compositor.py (compositing per domain)
and GeologicalDomain statistics (domain_classifier → continuity_analyzer).
"""

from __future__ import annotations

from dataclasses import replace

from engine.core.logging import get_logger
from engine.geology.drillhole_compositor import domain_statistics
from engine.geology.models import (
    AssayInterval,
    Composite,
    GeologicalDomain,
    LithologyInterval,
)

log = get_logger(__name__)


def classify_by_lithology(
    intervals: list[AssayInterval],
    lithology_map: list[LithologyInterval],
    domain_lookup: dict[str, str],
) -> dict[str, list[AssayInterval]]:
    """
    Assign assay intervals to domains by matching them to lithology intervals.

    domain_lookup: maps rock_code → domain_id
        e.g. {"DIOR": "domain_diorite", "QVN": "domain_quartz_vein"}

    Returns a dict mapping domain_id → list of AssayInterval.
    Intervals not matching any domain code are placed in "domain_unclassified".
    """
    # Build a quick lookup: hole_id → sorted list of lithology intervals
    lith_by_hole: dict[str, list[LithologyInterval]] = {}
    for lith in lithology_map:
        lith_by_hole.setdefault(lith.hole_id, []).append(lith)
    for hole in lith_by_hole:
        lith_by_hole[hole].sort(key=lambda x: x.from_m)

    result: dict[str, list[AssayInterval]] = {}

    for iv in intervals:
        domain = _match_lithology(iv, lith_by_hole.get(iv.hole_id, []), domain_lookup)
        result.setdefault(domain, []).append(iv)

    log.debug(
        "Lithology classification | intervals=%d domains=%s",
        len(intervals),
        {k: len(v) for k, v in result.items()},
    )
    return result


def classify_by_grade_threshold(
    intervals: list[AssayInterval],
    cut_off_grade: float,
    ore_domain: str = "domain_ore",
    waste_domain: str = "domain_waste",
) -> dict[str, list[AssayInterval]]:
    """
    Simple binary classification: above cut-off = ore domain, below = waste.

    Useful when no lithological classification is available and a grade shell
    proxy is needed for resource estimation.
    """
    result: dict[str, list[AssayInterval]] = {ore_domain: [], waste_domain: []}
    for iv in intervals:
        grade = iv.primary_grade if iv.primary_grade is not None else 0.0
        if grade >= cut_off_grade:
            result[ore_domain].append(iv)
        else:
            result[waste_domain].append(iv)

    log.debug(
        "Grade threshold classification | cut_off=%.3f ore=%d waste=%d",
        cut_off_grade,
        len(result[ore_domain]),
        len(result[waste_domain]),
    )
    return result


def build_domain_from_composites(
    domain_id: str,
    name: str,
    primary_element: str,
    grade_unit: str,
    composites: list[Composite],
) -> GeologicalDomain:
    """
    Build a GeologicalDomain with statistics populated from a list of composites.

    This is the link between the compositing step and the domain model:
    after compositing per domain, call this to get a fully populated domain.
    """
    stats = domain_statistics(composites)
    return GeologicalDomain(
        domain_id=domain_id,
        name=name,
        primary_element=primary_element,
        grade_unit=grade_unit,
        sample_count=stats.get("count", 0),
        mean_grade=stats.get("mean"),
        median_grade=stats.get("median"),
        cv=stats.get("cv"),
        min_grade=stats.get("min"),
        max_grade=stats.get("max"),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _match_lithology(
    iv: AssayInterval,
    lith_intervals: list[LithologyInterval],
    domain_lookup: dict[str, str],
) -> str:
    """
    Match an assay interval to the overlapping lithology interval at mid-depth.
    Returns the domain_id or 'domain_unclassified'.
    """
    mid = (iv.from_m + iv.to_m) / 2.0
    for lith in lith_intervals:
        if lith.from_m <= mid <= lith.to_m:
            return domain_lookup.get(lith.rock_code, "domain_unclassified")
    return "domain_unclassified"

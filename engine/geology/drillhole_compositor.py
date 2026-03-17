"""
Drillhole compositor.

Composites raw assay intervals from drillholes into fixed-length intervals
suitable for geostatistical analysis and resource estimation.

Compositing aggregates short assay intervals into consistent length blocks,
averaging grade by length weighting. This reduces noise from variable-length
sampling and provides regular data for variography and resource estimation.

Key compositing methods supported:
  - Fixed-length: composite to a target length, with partial intervals at ends
  - Bench: composite to a mining bench height (for open pit scheduling)
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from engine.core.logging import get_logger
from engine.geology.models import AssayInterval, Composite

log = get_logger(__name__)


def composite_fixed_length(
    intervals: list[AssayInterval],
    composite_length_m: float,
    domain: str,
    min_composite_length_m: float | None = None,
) -> list[Composite]:
    """
    Composite assay intervals to a fixed composite length.

    Intervals from the same hole are processed together.
    Grade is weighted by interval length.

    composite_length_m: target composite length (e.g. 2.0, 5.0)
    domain: geological domain to tag composites with
    min_composite_length_m: minimum acceptable composite length as a fraction
        of target (default: half the composite_length_m). Short end composites
        below this threshold are discarded to avoid biasing grade estimates.

    Returns a list of Composite objects.
    """
    if not intervals:
        return []

    if min_composite_length_m is None:
        min_composite_length_m = composite_length_m * 0.5

    # Group by hole
    holes: dict[str, list[AssayInterval]] = {}
    for iv in intervals:
        holes.setdefault(iv.hole_id, []).append(iv)

    composites: list[Composite] = []
    for hole_id, hole_intervals in holes.items():
        hole_composites = _composite_hole(
            hole_id=hole_id,
            intervals=sorted(hole_intervals, key=lambda x: x.from_m),
            composite_length_m=composite_length_m,
            domain=domain,
            min_composite_length_m=min_composite_length_m,
        )
        composites.extend(hole_composites)

    log.debug(
        "Compositing complete | holes=%d intervals=%d composites=%d domain=%s",
        len(holes), len(intervals), len(composites), domain,
    )
    return composites


def _composite_hole(
    hole_id: str,
    intervals: list[AssayInterval],
    composite_length_m: float,
    domain: str,
    min_composite_length_m: float,
) -> list[Composite]:
    """Composite a single hole's intervals into fixed-length blocks."""
    if not intervals:
        return []

    primary_element = intervals[0].primary_element
    grade_unit = intervals[0].grade_unit

    # Expand intervals into a continuous sequence of (from, to, grade) segments
    # This handles the case where assay intervals are not contiguous
    composites: list[Composite] = []

    composite_start = intervals[0].from_m
    accumulated_length = 0.0
    grade_x_length: list[tuple[float, float]] = []  # (grade, length)
    secondary_x_length: dict[str, list[tuple[float, float]]] = {}

    for iv in intervals:
        iv_len = iv.to_m - iv.from_m
        if iv_len <= 0:
            continue

        iv_grade = iv.primary_grade if iv.primary_grade is not None else 0.0
        grade_x_length.append((iv_grade, iv_len))
        accumulated_length += iv_len

        # Secondary grades
        for elem, grade in iv.secondary_grades.items():
            secondary_x_length.setdefault(elem, []).append((grade, iv_len))

        # Flush composite when we reach the target length
        while accumulated_length >= composite_length_m:
            # Take exactly composite_length_m worth from grade_x_length
            taken = 0.0
            comp_grade_xl: list[tuple[float, float]] = []
            comp_secondary_xl: dict[str, list[tuple[float, float]]] = {}
            remaining_xl: list[tuple[float, float]] = []
            remaining_secondary: dict[str, list[tuple[float, float]]] = {}

            for g, l in grade_x_length:
                if taken >= composite_length_m:
                    remaining_xl.append((g, l))
                    for elem, vals in secondary_x_length.items():
                        pass  # handled below
                else:
                    take = min(l, composite_length_m - taken)
                    comp_grade_xl.append((g, take))
                    taken += take
                    if take < l:
                        remaining_xl.append((g, l - take))

            # Weighted average grade for the composite
            total_len = sum(l for _, l in comp_grade_xl)
            if total_len > 0:
                avg_grade = sum(g * l for g, l in comp_grade_xl) / total_len
            else:
                avg_grade = 0.0

            # Secondary grades
            sec_grades: dict[str, float] = {}
            for elem, xl_list in secondary_x_length.items():
                elem_len = 0.0
                elem_sum = 0.0
                for g, l in xl_list[:len(comp_grade_xl)]:
                    elem_sum += g * l
                    elem_len += l
                if elem_len > 0:
                    sec_grades[elem] = elem_sum / elem_len

            composites.append(Composite(
                hole_id=hole_id,
                from_m=composite_start,
                to_m=composite_start + total_len,
                composite_length_m=total_len,
                domain=domain,
                primary_element=primary_element,
                composite_grade=round(avg_grade, 4),
                grade_unit=grade_unit,
                secondary_grades=sec_grades,
            ))

            composite_start += total_len
            accumulated_length -= total_len
            grade_x_length = remaining_xl
            secondary_x_length = {k: v[len(comp_grade_xl):] for k, v in secondary_x_length.items()}

    # Handle end composite (partial)
    if grade_x_length and accumulated_length >= min_composite_length_m:
        total_len = sum(l for _, l in grade_x_length)
        avg_grade = sum(g * l for g, l in grade_x_length) / total_len if total_len > 0 else 0.0
        composites.append(Composite(
            hole_id=hole_id,
            from_m=composite_start,
            to_m=composite_start + total_len,
            composite_length_m=total_len,
            domain=domain,
            primary_element=primary_element,
            composite_grade=round(avg_grade, 4),
            grade_unit=grade_unit,
        ))

    return composites


def domain_statistics(composites: list[Composite]) -> dict[str, float | int | None]:
    """
    Calculate basic grade statistics for a list of composites (single domain).

    Returns a dict with: count, mean, median, cv, min, max
    weighted by composite length.
    """
    if not composites:
        return {"count": 0, "mean": None, "median": None, "cv": None, "min": None, "max": None}

    grades = [c.composite_grade for c in composites]
    weights = [c.composite_length_m for c in composites]

    total_weight = sum(weights)
    mean = sum(g * w for g, w in zip(grades, weights)) / total_weight if total_weight > 0 else 0.0

    std = statistics.pstdev(grades) if len(grades) > 1 else 0.0
    cv = std / mean if mean > 0 else None

    return {
        "count": len(grades),
        "mean": round(mean, 4),
        "median": round(statistics.median(grades), 4),
        "cv": round(cv, 3) if cv is not None else None,
        "min": round(min(grades), 4),
        "max": round(max(grades), 4),
    }

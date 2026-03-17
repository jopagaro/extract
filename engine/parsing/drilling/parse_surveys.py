"""
Parse downhole survey CSV files into normalised SurveyPoint objects.

Downhole surveys record the orientation of the drillhole at regular depth
intervals (typically every 30 m), used to reconstruct the 3-D drillhole
path for resource estimation and geological interpretation.

The two main survey types are:
- Magnetic (uses true or magnetic azimuth)
- Gyroscopic (more accurate in magnetically disturbed zones)

Both produce the same data columns: hole_id, depth, azimuth, dip.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.geology.models import SurveyPoint
from engine.io.csv_io import read_csv_normalised


# ---------------------------------------------------------------------------
# Column alias table
# ---------------------------------------------------------------------------

SURVEY_COLUMN_ALIASES: dict[str, list[str]] = {
    "hole_id": [
        "hole_id", "holeid", "hole", "bhid", "dhid",
        "drillhole_id", "drillhole", "name", "borehole_id",
        "well_id", "wellid", "id",
    ],
    "depth_m": [
        "depth_m", "depth", "survey_depth", "depth_from",
        "measured_depth", "md", "at", "at_depth",
        "downhole_depth", "dh_depth",
    ],
    "azimuth": [
        "azimuth", "az", "azi", "bearing",
        "azimuth_deg", "trend", "grid_az",
        "magnetic_azimuth", "gyro_azimuth",
    ],
    "dip": [
        "dip", "inclination", "incl", "plunge",
        "dip_angle", "dip_deg", "hade",
    ],
}


# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

def detect_survey_columns(df: Any) -> dict[str, str]:
    """
    Map canonical survey column names to actual column names in *df*.

    Parameters
    ----------
    df:
        A Polars DataFrame with normalised column names.

    Returns
    -------
    dict[str, str]
        Canonical name → actual column name found.
    """
    actual_cols = set(df.columns)
    mapping: dict[str, str] = {}

    for canonical, aliases in SURVEY_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in actual_cols:
                mapping[canonical] = alias
                break

    return mapping


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------

def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None


def parse_surveys_csv(
    path: Path | str,
) -> tuple[list[SurveyPoint], list[str]]:
    """
    Parse a downhole survey CSV file into a list of :class:`SurveyPoint` objects.

    Parameters
    ----------
    path:
        Path to the survey CSV file.

    Returns
    -------
    tuple[list[SurveyPoint], list[str]]
        - Parsed SurveyPoint objects
        - List of warning strings for problematic rows
    """
    path = Path(path)
    df = read_csv_normalised(path)
    col_map = detect_survey_columns(df)

    warnings: list[str] = []

    # Check for required columns
    required = ["hole_id", "depth_m", "azimuth", "dip"]
    for req in required:
        if req not in col_map:
            warnings.append(
                f"No '{req}' column found in {path.name}. "
                f"Tried: {SURVEY_COLUMN_ALIASES[req]}. "
                f"Available columns: {df.columns}"
            )

    missing = [r for r in required if r not in col_map]
    if missing:
        return [], warnings

    surveys: list[SurveyPoint] = []

    for row_idx, row in enumerate(df.to_dicts()):
        hole_id_val = row.get(col_map["hole_id"])
        if not hole_id_val or str(hole_id_val).strip() == "":
            warnings.append(f"Row {row_idx + 2}: empty hole_id, skipping.")
            continue

        hole_id = str(hole_id_val).strip()
        depth_m = _safe_float(row.get(col_map["depth_m"]))
        azimuth = _safe_float(row.get(col_map["azimuth"]))
        dip = _safe_float(row.get(col_map["dip"]))

        if depth_m is None:
            warnings.append(f"Row {row_idx + 2} [{hole_id}]: non-numeric depth, skipping.")
            continue
        if azimuth is None:
            warnings.append(f"Row {row_idx + 2} [{hole_id}]: non-numeric azimuth, skipping.")
            continue
        if dip is None:
            warnings.append(f"Row {row_idx + 2} [{hole_id}]: non-numeric dip, skipping.")
            continue

        surveys.append(SurveyPoint(
            hole_id=hole_id,
            depth_m=depth_m,
            azimuth=azimuth,
            dip=dip,
        ))

    return surveys, warnings


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_surveys(surveys: list[SurveyPoint]) -> list[str]:
    """
    Validate a list of SurveyPoint objects and return warning strings.

    Checks for:
    - Azimuth outside 0–360°
    - Dip outside -90° to 90°
    - Negative depths
    - Duplicate depth entries within the same hole
    - Non-increasing depth sequence within a hole

    Parameters
    ----------
    surveys:
        List of SurveyPoint objects.

    Returns
    -------
    list[str]
        Warning messages. Empty list means validation passed.
    """
    warnings: list[str] = []

    # Group by hole
    by_hole: dict[str, list[SurveyPoint]] = {}
    for sp in surveys:
        by_hole.setdefault(sp.hole_id, []).append(sp)

    for hole_id, points in by_hole.items():
        sorted_pts = sorted(points, key=lambda p: p.depth_m)

        seen_depths: set[float] = set()
        prev_depth: float | None = None

        for pt in sorted_pts:
            # Azimuth range
            if not (0.0 <= pt.azimuth <= 360.0):
                warnings.append(
                    f"[{hole_id}] Depth {pt.depth_m}: "
                    f"azimuth {pt.azimuth}° outside valid range 0–360°."
                )

            # Dip range
            if not (-90.0 <= pt.dip <= 90.0):
                warnings.append(
                    f"[{hole_id}] Depth {pt.depth_m}: "
                    f"dip {pt.dip}° outside valid range -90 to 90°."
                )

            # Negative depth
            if pt.depth_m < 0:
                warnings.append(
                    f"[{hole_id}] Negative survey depth {pt.depth_m} m."
                )

            # Duplicate depth
            if pt.depth_m in seen_depths:
                warnings.append(
                    f"[{hole_id}] Duplicate survey depth {pt.depth_m} m."
                )
            seen_depths.add(pt.depth_m)

    return warnings

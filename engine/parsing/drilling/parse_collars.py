"""
Parse drillhole collar CSV files into normalised Collar objects.

A collar is the surface location of a drillhole. Collar files typically
contain the hole ID, coordinates (easting/northing/elevation or
latitude/longitude), orientation (azimuth/dip), and total depth.

Column names vary enormously across different mining software packages,
lab systems, and regional conventions. The alias table below maps the
most common variants to the canonical names used by this platform.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.geology.models import Collar
from engine.io.csv_io import read_csv_normalised


# ---------------------------------------------------------------------------
# Column alias table
# ---------------------------------------------------------------------------

COLLAR_COLUMN_ALIASES: dict[str, list[str]] = {
    "hole_id": [
        "hole_id", "holeid", "hole", "bhid", "dhid",
        "drillhole_id", "drillhole", "name", "borehole_id",
        "well_id", "wellid", "id",
    ],
    "easting": [
        "easting", "east", "x", "utm_e", "utm_easting",
        "longitude", "lon", "long", "lng", "x_coord",
    ],
    "northing": [
        "northing", "north", "y", "utm_n", "utm_northing",
        "latitude", "lat", "y_coord",
    ],
    "elevation": [
        "elevation", "elev", "rl", "z", "collar_rl",
        "collar_elevation", "collar_z", "altitude", "alt",
        "z_coord", "reduced_level",
    ],
    "azimuth": [
        "azimuth", "az", "azi", "bearing", "dip_azimuth",
        "azimuth_deg", "trend", "grid_az",
    ],
    "dip": [
        "dip", "inclination", "incl", "plunge",
        "dip_angle", "dip_deg",
    ],
    "total_depth": [
        "total_depth", "depth", "td", "eoh", "end_of_hole",
        "max_depth", "hole_depth", "finaldepth", "final_depth",
        "depth_m", "total_depth_m",
    ],
}


# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

def detect_collar_columns(df: Any) -> dict[str, str]:
    """
    Map canonical collar column names to the actual column names found in *df*.

    Parameters
    ----------
    df:
        A Polars DataFrame (with normalised column names).

    Returns
    -------
    dict[str, str]
        Mapping of canonical name → actual column name found in *df*.
        Only canonical names that were successfully matched are included.
    """
    actual_cols = set(df.columns)
    mapping: dict[str, str] = {}

    for canonical, aliases in COLLAR_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in actual_cols:
                mapping[canonical] = alias
                break

    return mapping


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _safe_float(val: Any) -> float | None:
    """Convert a value to float, returning None on failure."""
    if val is None:
        return None
    try:
        fval = float(str(val).strip())
        return fval
    except (ValueError, TypeError):
        return None


def parse_collars_csv(
    path: Path | str,
) -> tuple[list[Collar], list[str]]:
    """
    Parse a drillhole collar CSV file into a list of :class:`Collar` objects.

    Handles:
    - Auto-detected delimiters (comma, tab, semicolon, pipe)
    - Normalised column names (lowercase, underscores)
    - Flexible column alias resolution
    - Rows with missing critical fields generate a warning (not an error)

    Parameters
    ----------
    path:
        Path to the collar CSV file.

    Returns
    -------
    tuple[list[Collar], list[str]]
        - Parsed Collar objects (may be empty)
        - List of warning strings for rows/columns with issues
    """
    path = Path(path)
    df = read_csv_normalised(path)
    col_map = detect_collar_columns(df)

    warnings: list[str] = []

    if "hole_id" not in col_map:
        warnings.append(
            f"No hole_id column found in {path.name}. "
            f"Tried: {COLLAR_COLUMN_ALIASES['hole_id']}. "
            f"Available columns: {df.columns}"
        )
        return [], warnings

    collars: list[Collar] = []

    for row_idx, row in enumerate(df.to_dicts()):
        hole_id_val = row.get(col_map["hole_id"])
        if not hole_id_val or str(hole_id_val).strip() == "":
            warnings.append(f"Row {row_idx + 2}: empty hole_id, skipping.")
            continue

        hole_id = str(hole_id_val).strip()

        easting = _safe_float(row.get(col_map.get("easting"))) if "easting" in col_map else None
        northing = _safe_float(row.get(col_map.get("northing"))) if "northing" in col_map else None
        elevation = _safe_float(row.get(col_map.get("elevation"))) if "elevation" in col_map else None
        azimuth = _safe_float(row.get(col_map.get("azimuth"))) if "azimuth" in col_map else None
        dip = _safe_float(row.get(col_map.get("dip"))) if "dip" in col_map else None
        total_depth = _safe_float(row.get(col_map.get("total_depth"))) if "total_depth" in col_map else None

        if easting is None and "easting" in col_map:
            warnings.append(f"Row {row_idx + 2} [{hole_id}]: non-numeric easting value.")
        if northing is None and "northing" in col_map:
            warnings.append(f"Row {row_idx + 2} [{hole_id}]: non-numeric northing value.")

        collar = Collar(
            hole_id=hole_id,
            easting=easting,
            northing=northing,
            elevation=elevation,
            azimuth=azimuth,
            dip=dip,
            total_depth_m=total_depth,
        )
        collars.append(collar)

    return collars, warnings


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_collars(collars: list[Collar]) -> list[str]:
    """
    Validate a list of Collar objects and return a list of warning strings.

    Checks for:
    - Missing easting / northing (coordinates are critical)
    - Duplicate hole IDs
    - Unrealistic coordinate values (e.g. easting of 0.0)
    - Unrealistic depth values (e.g. negative total depth)
    - Azimuth outside 0–360
    - Dip outside -90 to 90

    Parameters
    ----------
    collars:
        List of parsed Collar objects.

    Returns
    -------
    list[str]
        Warning messages. Empty list means validation passed.
    """
    warnings: list[str] = []
    seen_ids: dict[str, int] = {}

    for i, collar in enumerate(collars):
        hid = collar.hole_id

        # Duplicate hole IDs
        if hid in seen_ids:
            warnings.append(
                f"Duplicate hole_id '{hid}' at row {i + 1} "
                f"(first seen at row {seen_ids[hid] + 1})."
            )
        else:
            seen_ids[hid] = i

        # Missing coordinates
        if collar.easting is None:
            warnings.append(f"[{hid}] Missing easting coordinate.")
        if collar.northing is None:
            warnings.append(f"[{hid}] Missing northing coordinate.")

        # Zero coordinates are suspicious in UTM data
        if collar.easting is not None and collar.easting == 0.0:
            warnings.append(f"[{hid}] Easting is 0.0 — possible missing value.")
        if collar.northing is not None and collar.northing == 0.0:
            warnings.append(f"[{hid}] Northing is 0.0 — possible missing value.")

        # Total depth
        if collar.total_depth_m is not None:
            if collar.total_depth_m < 0:
                warnings.append(f"[{hid}] Negative total depth ({collar.total_depth_m} m).")
            if collar.total_depth_m > 10_000:
                warnings.append(
                    f"[{hid}] Total depth {collar.total_depth_m} m is unusually large."
                )

        # Azimuth range
        if collar.azimuth is not None:
            if not (0.0 <= collar.azimuth <= 360.0):
                warnings.append(
                    f"[{hid}] Azimuth {collar.azimuth}° is outside valid range 0–360°."
                )

        # Dip range
        if collar.dip is not None:
            if not (-90.0 <= collar.dip <= 90.0):
                warnings.append(
                    f"[{hid}] Dip {collar.dip}° is outside valid range -90 to 90°."
                )

    return warnings

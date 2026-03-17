"""
Parse drillhole assay CSV files into normalised AssayInterval objects.

Assay data records the chemical analysis of drillhole intervals —
the grades of economically relevant elements (gold, copper, silver, etc.)
along the drillhole.

Column names vary by lab, software, and commodity. This module uses an
alias table for structural columns (hole_id, from, to) and heuristic
detection for element grade columns.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from engine.geology.models import AssayInterval
from engine.io.csv_io import read_csv_normalised


# ---------------------------------------------------------------------------
# Column alias table
# ---------------------------------------------------------------------------

ASSAY_COLUMN_ALIASES: dict[str, list[str]] = {
    "hole_id": [
        "hole_id", "holeid", "hole", "bhid", "dhid",
        "drillhole_id", "drillhole", "name", "borehole_id",
        "well_id", "wellid", "id",
    ],
    "from_m": [
        "from_m", "from", "from_depth", "depth_from",
        "interval_from", "start_depth", "top", "top_m",
        "from_depth_m", "depth_top",
    ],
    "to_m": [
        "to_m", "to", "to_depth", "depth_to",
        "interval_to", "end_depth", "bottom", "bottom_m",
        "to_depth_m", "depth_bottom",
    ],
    "sample_id": [
        "sample_id", "sampleid", "sample", "sample_no",
        "sample_number", "lab_no", "lab_number",
    ],
    "lab": [
        "lab", "laboratory", "lab_name", "assay_lab",
    ],
}

# Element symbols commonly used as column headers in assay data
_ELEMENT_SYMBOLS = {
    "au", "ag", "cu", "zn", "pb", "mo", "ni", "co", "fe", "mn",
    "as", "sb", "bi", "w", "sn", "pt", "pd", "re", "v", "cr",
    "ti", "al", "k", "na", "ca", "mg", "p", "s", "c",
    "li", "b", "u", "th", "rare", "te", "se",
}

# Unit suffixes that appear in assay column names
_UNIT_SUFFIXES = {
    "ppm", "ppb", "pct", "percent", "g_t", "gt", "oz_t", "opt",
    "mg_kg", "mg_l", "ug_g",
}

# Common patterns for grade columns (e.g. "au_ppm", "cu_pct", "zn_%")
_GRADE_COL_PATTERN = re.compile(
    r"^(?:" +
    "|".join(re.escape(e) for e in sorted(_ELEMENT_SYMBOLS, key=len, reverse=True)) +
    r")"
    r"(?:[_\s]?(?:" + "|".join(_UNIT_SUFFIXES) + r"))?$"
)


# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

def detect_assay_columns(df: Any) -> dict[str, str]:
    """
    Map canonical assay structural column names to actual column names in *df*.

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

    for canonical, aliases in ASSAY_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in actual_cols:
                mapping[canonical] = alias
                break

    return mapping


def detect_element_columns(df: Any) -> list[str]:
    """
    Find columns in *df* that look like element grade measurements.

    A column is considered an element grade column if:
    1. Its (normalised) name matches a known element symbol or symbol+unit pattern, OR
    2. It contains numeric data and its name is a single element symbol (case-insensitive)

    Parameters
    ----------
    df:
        A Polars DataFrame with normalised column names.

    Returns
    -------
    list[str]
        Column names that appear to be element grades, in original order.
    """
    import polars as pl

    # Exclude structural columns
    structural_aliases = {
        alias
        for aliases in ASSAY_COLUMN_ALIASES.values()
        for alias in aliases
    }

    element_cols: list[str] = []
    for col in df.columns:
        if col in structural_aliases:
            continue
        col_lower = col.lower().strip()

        # Direct element symbol match
        if col_lower in _ELEMENT_SYMBOLS:
            element_cols.append(col)
            continue

        # Pattern match (e.g. au_ppm, cu_pct)
        if _GRADE_COL_PATTERN.match(col_lower):
            element_cols.append(col)
            continue

        # Numeric column whose name contains an element symbol as a token
        # (e.g. "gold_grade", "copper_assay")
        tokens = re.split(r"[_\s]+", col_lower)
        if any(t in _ELEMENT_SYMBOLS for t in tokens):
            # Confirm the column is numeric
            dtype = df[col].dtype
            if dtype in (
                pl.Float32, pl.Float64,
                pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
            ):
                element_cols.append(col)

    return element_cols


# ---------------------------------------------------------------------------
# Primary element detection
# ---------------------------------------------------------------------------

def detect_primary_element(df: Any) -> str | None:
    """
    Guess the primary economic element from column names and grade magnitudes.

    Heuristics (in priority order):
    1. If a column is named exactly an element symbol (e.g. ``au``, ``cu``),
       prefer precious metals (Au, Ag) then base metals (Cu, Zn, Pb, …).
    2. Among numeric element columns, the one with the highest coefficient of
       variation (std/mean) is often the pay element.
    3. Fall back to the first detected element column.

    Parameters
    ----------
    df:
        A Polars DataFrame with normalised column names.

    Returns
    -------
    str | None
        Canonical element symbol (e.g. ``"Au"``), or None if not detected.
    """
    import polars as pl

    element_cols = detect_element_columns(df)
    if not element_cols:
        return None

    # Priority: precious metals first
    priority_order = ["au", "ag", "pt", "pd", "cu", "zn", "pb", "ni", "mo", "co"]

    # Check for exact symbol matches in priority order
    col_lower_map = {col.lower().split("_")[0]: col for col in element_cols}
    for elem in priority_order:
        if elem in col_lower_map:
            return elem.capitalize()

    # Fallback: highest coefficient of variation among numeric columns
    best_col = None
    best_cv = -1.0

    for col in element_cols:
        try:
            series = df[col].cast(pl.Float64).drop_nulls()
            if series.len() < 2:
                continue
            mean_val = series.mean()
            if mean_val and mean_val > 0:
                cv = series.std() / mean_val
                if cv > best_cv:
                    best_cv = cv
                    best_col = col
        except Exception:
            continue

    if best_col:
        # Extract the element part
        return best_col.split("_")[0].capitalize()

    return element_cols[0].split("_")[0].capitalize()


# ---------------------------------------------------------------------------
# Infer grade unit from column name
# ---------------------------------------------------------------------------

def _infer_grade_unit(col_name: str, values: Any) -> str:
    """
    Infer the grade unit from the column name and, if needed, the value range.
    """
    col_lower = col_name.lower()
    if "ppm" in col_lower or "mg_kg" in col_lower:
        return "ppm"
    if "ppb" in col_lower or "ug_g" in col_lower:
        return "ppb"
    if "pct" in col_lower or "percent" in col_lower or "%" in col_lower:
        return "%"
    if "g_t" in col_lower or "gt" in col_lower or "oz_t" in col_lower:
        return "g/t"

    # Guess from magnitude: Au/Ag typically <100 g/t; Cu/Zn as % typically <50
    try:
        import polars as pl
        median = values.cast(pl.Float64).drop_nulls().median()
        if median is not None:
            if median < 100:
                return "g/t"
            else:
                return "ppm"
    except Exception:
        pass

    return "ppm"


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


def parse_assays_csv(
    path: Path | str,
    primary_element: str | None = None,
) -> tuple[list[AssayInterval], list[str]]:
    """
    Parse a drillhole assay CSV into a list of :class:`AssayInterval` objects.

    Parameters
    ----------
    path:
        Path to the assay CSV file.
    primary_element:
        The primary economic element to use as the ``primary_element`` field
        on each interval. If None, :func:`detect_primary_element` is called.

    Returns
    -------
    tuple[list[AssayInterval], list[str]]
        - Parsed AssayInterval objects
        - List of warning strings
    """
    path = Path(path)
    df = read_csv_normalised(path)
    col_map = detect_assay_columns(df)
    element_cols = detect_element_columns(df)
    warnings: list[str] = []

    # Validate required columns
    for required in ("hole_id", "from_m", "to_m"):
        if required not in col_map:
            warnings.append(
                f"No '{required}' column found in {path.name}. "
                f"Tried: {ASSAY_COLUMN_ALIASES[required]}. "
                f"Available columns: {df.columns}"
            )

    if "hole_id" not in col_map or "from_m" not in col_map or "to_m" not in col_map:
        return [], warnings

    # Detect primary element if not supplied
    if primary_element is None:
        primary_element = detect_primary_element(df)
        if primary_element is None and element_cols:
            primary_element = element_cols[0].split("_")[0].capitalize()

    primary_element = primary_element or "Unknown"

    # Determine primary element column
    primary_col: str | None = None
    pe_lower = primary_element.lower()
    for col in element_cols:
        if col.lower().startswith(pe_lower):
            primary_col = col
            break

    # Infer grade unit for primary element
    grade_unit = "ppm"
    if primary_col:
        grade_unit = _infer_grade_unit(primary_col, df[primary_col])

    # Secondary element columns (all element cols except primary)
    secondary_cols = [c for c in element_cols if c != primary_col]

    intervals: list[AssayInterval] = []

    for row_idx, row in enumerate(df.to_dicts()):
        hole_id_val = row.get(col_map["hole_id"])
        if not hole_id_val or str(hole_id_val).strip() == "":
            warnings.append(f"Row {row_idx + 2}: empty hole_id, skipping.")
            continue

        hole_id = str(hole_id_val).strip()
        from_m = _safe_float(row.get(col_map["from_m"]))
        to_m = _safe_float(row.get(col_map["to_m"]))

        if from_m is None or to_m is None:
            warnings.append(f"Row {row_idx + 2} [{hole_id}]: non-numeric from/to, skipping.")
            continue

        length_m = round(to_m - from_m, 4)
        primary_grade = _safe_float(row.get(primary_col)) if primary_col else None

        secondary_grades: dict[str, float] = {}
        for sc in secondary_cols:
            val = _safe_float(row.get(sc))
            if val is not None:
                secondary_grades[sc.split("_")[0].capitalize()] = val

        sample_id = str(row.get(col_map.get("sample_id", ""), "") or "").strip() or None
        lab = str(row.get(col_map.get("lab", ""), "") or "").strip() or None

        interval = AssayInterval(
            hole_id=hole_id,
            from_m=from_m,
            to_m=to_m,
            length_m=length_m,
            primary_element=primary_element,
            primary_grade=primary_grade,
            grade_unit=grade_unit,
            secondary_grades=secondary_grades,
            sample_id=sample_id,
            lab=lab,
        )
        intervals.append(interval)

    return intervals, warnings


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_assay_intervals(intervals: list[AssayInterval]) -> list[str]:
    """
    Validate a list of AssayInterval objects and return warning strings.

    Checks for:
    - Intervals where from_m >= to_m
    - Negative grade values
    - Overlapping intervals within the same hole
    - Unrealistically high grade values (>10,000 g/t or >100%)
    - Null / missing grades for the primary element

    Parameters
    ----------
    intervals:
        List of parsed AssayInterval objects.

    Returns
    -------
    list[str]
        Warning messages. Empty list means validation passed.
    """
    warnings: list[str] = []

    # Group by hole
    by_hole: dict[str, list[AssayInterval]] = {}
    for iv in intervals:
        by_hole.setdefault(iv.hole_id, []).append(iv)

    for hole_id, hole_intervals in by_hole.items():
        # Sort by from_m for overlap detection
        sorted_ivs = sorted(hole_intervals, key=lambda x: x.from_m)

        prev: AssayInterval | None = None
        for iv in sorted_ivs:
            # from >= to
            if iv.from_m >= iv.to_m:
                warnings.append(
                    f"[{hole_id}] Interval {iv.from_m}–{iv.to_m}: "
                    f"from_m >= to_m."
                )

            # Negative grade
            if iv.primary_grade is not None and iv.primary_grade < 0:
                warnings.append(
                    f"[{hole_id}] Interval {iv.from_m}–{iv.to_m}: "
                    f"negative {iv.primary_element} grade ({iv.primary_grade})."
                )

            # Unrealistically high grade
            if iv.primary_grade is not None:
                if iv.grade_unit in ("g/t", "ppm") and iv.primary_grade > 10_000:
                    warnings.append(
                        f"[{hole_id}] Interval {iv.from_m}–{iv.to_m}: "
                        f"{iv.primary_element} grade {iv.primary_grade} g/t is very high."
                    )
                if iv.grade_unit == "%" and iv.primary_grade > 100:
                    warnings.append(
                        f"[{hole_id}] Interval {iv.from_m}–{iv.to_m}: "
                        f"{iv.primary_element} grade {iv.primary_grade}% > 100%."
                    )

            # Missing primary grade
            if iv.primary_grade is None:
                warnings.append(
                    f"[{hole_id}] Interval {iv.from_m}–{iv.to_m}: "
                    f"missing {iv.primary_element} grade."
                )

            # Overlap with previous interval
            if prev is not None and iv.from_m < prev.to_m:
                warnings.append(
                    f"[{hole_id}] Overlap: interval {iv.from_m}–{iv.to_m} "
                    f"overlaps with {prev.from_m}–{prev.to_m}."
                )

            prev = iv

    return warnings

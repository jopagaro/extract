"""
Assay normalizer.

Reads raw/assays/assay_csv/ CSV files, detects the primary element,
checks basic QAQC completeness, and writes normalized Parquet output.
"""

from __future__ import annotations

from pathlib import Path

from engine.core.logging import get_logger
from engine.core.paths import project_normalized, project_raw
from engine.io.parquet_io import dicts_to_parquet
from engine.parsing.drilling.parse_assays import (
    detect_primary_element,
    parse_assays_csv,
    validate_assay_intervals,
)

log = get_logger(__name__)

# Keywords that indicate QAQC sample types
_BLANK_KEYWORDS = {"blank", "blk", "qaqc_blank", "neg_blank", "negative_blank"}
_STD_KEYWORDS = {"std", "standard", "cert", "certified", "crm", "reference"}
_DUP_KEYWORDS = {"dup", "duplicate", "field_dup", "quarter_core", "twin"}


def _check_qaqc(interval_rows: list[dict]) -> list[str]:
    """
    Simple QAQC completeness check.
    Looks for blanks, standards, and duplicates in sample_id or hole_id fields.
    Returns warnings for missing QAQC types.
    """
    warnings: list[str] = []
    has_blanks = False
    has_standards = False
    has_duplicates = False

    for row in interval_rows:
        sample_id = str(row.get("sample_id") or "").lower()
        hole_id = str(row.get("hole_id") or "").lower()
        combined = sample_id + " " + hole_id

        if any(kw in combined for kw in _BLANK_KEYWORDS):
            has_blanks = True
        if any(kw in combined for kw in _STD_KEYWORDS):
            has_standards = True
        if any(kw in combined for kw in _DUP_KEYWORDS):
            has_duplicates = True

    if not has_blanks:
        warnings.append(
            "QAQC: No blank samples detected in assay data. "
            "Blanks are required to assess contamination. "
            "Assay accuracy cannot be independently verified."
        )
    if not has_standards:
        warnings.append(
            "QAQC: No certified reference material (standard) samples detected. "
            "Standards are required to verify laboratory accuracy and bias. "
            "Grade reliability cannot be confirmed without standards."
        )
    if not has_duplicates:
        warnings.append(
            "QAQC: No duplicate samples detected. "
            "Field and/or laboratory duplicates are needed to assess precision. "
            "Grade variability from sampling error cannot be quantified."
        )

    return warnings


def normalise_assays(project_id: str, run_id: str) -> list[str]:
    """
    Reads raw/assays/assay_csv/ CSV files.
    Detects primary element.
    Writes to normalized/assays/assay_intervals.parquet.
    Checks for basic QAQC completeness (blanks, standards, duplicates present?).
    Flags missing QAQC in warnings.
    Returns list of warnings.
    """
    warnings: list[str] = []
    log.info("Normalising assays for project=%s", project_id)

    raw_root = project_raw(project_id)
    norm_root = project_normalized(project_id) / "assays"

    # Candidate directories for assay CSVs
    candidate_dirs = [
        raw_root / "assays" / "assay_csv",
        raw_root / "assays",
        raw_root / "geochemistry",
        raw_root / "geochem",
    ]

    csv_files: list[Path] = []
    seen: set[Path] = set()
    for d in candidate_dirs:
        if d.exists():
            for f in sorted(d.rglob("*.csv")):
                if f not in seen:
                    seen.add(f)
                    csv_files.append(f)

    if not csv_files:
        warnings.append(
            "No CSV files found in raw/assays/. No assay data normalised."
        )
        return warnings

    all_intervals: list[dict] = []
    primary_element: str | None = None

    for csv_path in csv_files:
        log.info("Parsing assay file: %s", csv_path.name)
        intervals, file_warnings = parse_assays_csv(csv_path, primary_element=primary_element)
        warnings.extend([f"{csv_path.name}: {w}" for w in file_warnings])

        if intervals and primary_element is None:
            primary_element = intervals[0].primary_element

        # Validate
        val_warnings = validate_assay_intervals(intervals)
        warnings.extend([f"{csv_path.name} validation: {w}" for w in val_warnings])

        for iv in intervals:
            all_intervals.append({
                "hole_id": iv.hole_id,
                "from_m": iv.from_m,
                "to_m": iv.to_m,
                "length_m": iv.length_m,
                "primary_element": iv.primary_element,
                "primary_grade": iv.primary_grade,
                "grade_unit": iv.grade_unit,
                "sample_id": iv.sample_id,
                "lab": iv.lab,
            })

    if not all_intervals:
        warnings.append("No assay intervals parsed — assay_intervals.parquet not written.")
        return warnings

    log.info("Detected primary element: %s", primary_element)

    # QAQC check
    qaqc_warnings = _check_qaqc(all_intervals)
    warnings.extend(qaqc_warnings)

    # Deduplicate by hole_id + from_m + to_m
    seen_keys: set[tuple] = set()
    deduped: list[dict] = []
    for row in all_intervals:
        key = (row["hole_id"], row["from_m"], row["to_m"])
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(row)
    if len(deduped) < len(all_intervals):
        warnings.append(
            f"Assays: removed {len(all_intervals) - len(deduped)} duplicate interval entries."
        )

    norm_root.mkdir(parents=True, exist_ok=True)
    dicts_to_parquet(deduped, norm_root / "assay_intervals.parquet")
    log.info("Written %d assay interval records to assay_intervals.parquet", len(deduped))

    log.info("Assay normalisation complete | %d warnings", len(warnings))
    return warnings

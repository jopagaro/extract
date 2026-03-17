"""
Drilling normalizer.

Scans raw/drillhole_csv/ for CSV files, routes each to the appropriate
parser, deduplicates, and writes normalised Parquet files.
"""

from __future__ import annotations

from pathlib import Path

from engine.core.logging import get_logger
from engine.core.paths import project_normalized, project_raw
from engine.io.parquet_io import dicts_to_parquet
from engine.parsing.drilling.parse_assays import parse_assays_csv
from engine.parsing.drilling.parse_collars import parse_collars_csv
from engine.parsing.drilling.parse_surveys import parse_surveys_csv

log = get_logger(__name__)

# Folder/filename hints that identify file type
_COLLAR_HINTS = {"collar", "collars", "location", "locations", "bhid", "drillhole"}
_SURVEY_HINTS = {"survey", "surveys", "downhole", "deviation"}
_ASSAY_HINTS = {"assay", "assays", "interval", "intervals", "geochem", "geochemistry", "sample"}


def _classify_csv(path: Path) -> str:
    """Guess whether a CSV is collars, surveys, or assays from name/folder."""
    name = path.stem.lower()
    parent = path.parent.name.lower()

    for hint in _COLLAR_HINTS:
        if hint in name or hint in parent:
            return "collars"
    for hint in _SURVEY_HINTS:
        if hint in name or hint in parent:
            return "surveys"
    for hint in _ASSAY_HINTS:
        if hint in name or hint in parent:
            return "assays"
    # Default: assume assays (the most common case)
    return "assays"


def normalise_drilling(project_id: str, run_id: str) -> list[str]:
    """
    Scans raw/drillhole_csv/ for CSV files.
    Routes each file to the appropriate parser (collars/surveys/intervals).
    Writes output to:
        normalized/drilling/collars.parquet
        normalized/drilling/surveys.parquet
        normalized/drilling/intervals.parquet
    Deduplicates by hole_id (collars) and hole_id+from_m+to_m (intervals).
    Returns list of warnings.
    """
    warnings: list[str] = []
    log.info("Normalising drilling data for project=%s", project_id)

    raw_root = project_raw(project_id)
    norm_root = project_normalized(project_id) / "drilling"

    # Scan candidate directories
    candidate_dirs = [
        raw_root / "drillhole_csv",
        raw_root / "drilling",
        raw_root / "collars",
        raw_root / "assays",
        raw_root / "surveys",
    ]
    # Also include all CSV files directly in raw/
    csv_files: list[Path] = []
    for d in candidate_dirs:
        if d.exists():
            csv_files.extend(sorted(d.rglob("*.csv")))
    # Deduplicate
    seen: set[Path] = set()
    unique_csvs: list[Path] = []
    for f in csv_files:
        if f not in seen:
            seen.add(f)
            unique_csvs.append(f)

    if not unique_csvs:
        warnings.append(
            "No CSV files found in raw/drillhole_csv/ or raw/drilling/. "
            "No drilling data normalised."
        )
        return warnings

    # Accumulate records per type
    collar_rows: list[dict] = []
    survey_rows: list[dict] = []
    interval_rows: list[dict] = []

    for csv_path in unique_csvs:
        file_type = _classify_csv(csv_path)
        log.info("Parsing %s as %s", csv_path.name, file_type)

        if file_type == "collars":
            collars, file_warnings = parse_collars_csv(csv_path)
            warnings.extend([f"{csv_path.name}: {w}" for w in file_warnings])
            for c in collars:
                collar_rows.append({
                    "hole_id": c.hole_id,
                    "easting": c.easting,
                    "northing": c.northing,
                    "elevation": c.elevation,
                    "azimuth": c.azimuth,
                    "dip": c.dip,
                    "total_depth_m": c.total_depth_m,
                    "drill_date": c.drill_date,
                    "drill_type": c.drill_type,
                    "program": c.program,
                })

        elif file_type == "surveys":
            surveys, file_warnings = parse_surveys_csv(csv_path)
            warnings.extend([f"{csv_path.name}: {w}" for w in file_warnings])
            for s in surveys:
                survey_rows.append({
                    "hole_id": s.hole_id,
                    "depth_m": s.depth_m,
                    "azimuth": s.azimuth,
                    "dip": s.dip,
                })

        else:  # assays / intervals
            intervals, file_warnings = parse_assays_csv(csv_path)
            warnings.extend([f"{csv_path.name}: {w}" for w in file_warnings])
            for iv in intervals:
                interval_rows.append({
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

    # Deduplicate collars by hole_id (keep first)
    seen_holes: set[str] = set()
    deduped_collars: list[dict] = []
    for row in collar_rows:
        if row["hole_id"] not in seen_holes:
            seen_holes.add(row["hole_id"])
            deduped_collars.append(row)
    if len(deduped_collars) < len(collar_rows):
        warnings.append(
            f"Collars: removed {len(collar_rows) - len(deduped_collars)} duplicate hole_id entries."
        )

    # Deduplicate intervals by hole_id+from_m+to_m
    seen_intervals: set[tuple] = set()
    deduped_intervals: list[dict] = []
    for row in interval_rows:
        key = (row["hole_id"], row["from_m"], row["to_m"])
        if key not in seen_intervals:
            seen_intervals.add(key)
            deduped_intervals.append(row)
    if len(deduped_intervals) < len(interval_rows):
        warnings.append(
            f"Intervals: removed {len(interval_rows) - len(deduped_intervals)} duplicate entries."
        )

    # Write outputs
    norm_root.mkdir(parents=True, exist_ok=True)

    if deduped_collars:
        dicts_to_parquet(deduped_collars, norm_root / "collars.parquet")
        log.info("Written %d collar records", len(deduped_collars))
    else:
        warnings.append("No collar records parsed — collars.parquet not written.")

    if survey_rows:
        dicts_to_parquet(survey_rows, norm_root / "surveys.parquet")
        log.info("Written %d survey records", len(survey_rows))
    else:
        warnings.append("No survey records parsed — surveys.parquet not written.")

    if deduped_intervals:
        dicts_to_parquet(deduped_intervals, norm_root / "intervals.parquet")
        log.info("Written %d interval records", len(deduped_intervals))
    else:
        warnings.append("No assay interval records parsed — intervals.parquet not written.")

    log.info("Drilling normalisation complete | %d warnings", len(warnings))
    return warnings

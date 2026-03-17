"""
Geology normalizer.

Reads LLM extraction outputs and builds GeologicalPicture.
Writes resource estimate summary, geological risks, and data assessments.
"""

from __future__ import annotations

import json
from pathlib import Path

from engine.core.logging import get_logger
from engine.core.manifests import read_json, write_json, write_data_assessments
from engine.core.paths import project_normalized
from engine.geology.geological_risk_assessor import assess_geological_picture
from engine.geology.missing_data_checker import check_missing_geological_data
from engine.geology.models import (
    GeologicalDomain,
    GeologicalPicture,
    ResourceCategory,
    ResourceEstimate,
)
from engine.io.parquet_io import dicts_to_parquet

log = get_logger(__name__)


def _load_geological_facts(staging_dir: Path) -> dict:
    """Load all JSON files from the geological_facts extraction directory."""
    facts: dict = {}
    if not staging_dir.exists():
        return facts
    for json_file in sorted(staging_dir.glob("*.json")):
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            facts.update(data)
        except Exception as e:
            log.warning("Could not load geological facts file %s: %s", json_file.name, e)
    return facts


def _build_resource_estimate(project_id: str, facts: dict) -> ResourceEstimate | None:
    """Build a ResourceEstimate from extracted facts."""
    resource_data = facts.get("resource_estimate") or facts.get("resources")
    if not resource_data:
        return None

    categories: list[ResourceCategory] = []

    raw_categories = resource_data.get("categories", [])
    for cat in raw_categories:
        categories.append(ResourceCategory(
            category=cat.get("category", "Unknown"),
            domain=cat.get("domain"),
            tonnes=cat.get("tonnes_mt") or cat.get("tonnes"),
            grade=cat.get("grade"),
            grade_unit=cat.get("grade_unit", ""),
            contained_metal=cat.get("contained_metal"),
            contained_metal_unit=cat.get("contained_metal_unit", ""),
            cut_off_grade=cat.get("cut_off_grade"),
            cut_off_unit=cat.get("cut_off_unit", ""),
        ))

    if not categories:
        return None

    estimate = ResourceEstimate(
        project_id=project_id,
        effective_date=resource_data.get("effective_date"),
        classification_system=resource_data.get("classification_system"),
        qualified_person=resource_data.get("qualified_person"),
        primary_element=resource_data.get("primary_element", "Unknown"),
        categories=categories,
        cut_off_grade=resource_data.get("cut_off_grade"),
        cut_off_unit=resource_data.get("cut_off_unit", ""),
        notes=resource_data.get("notes"),
    )

    # Compute totals
    mi_t, mi_g, mi_metal = estimate.total_by_category("measured")
    ind_t, ind_g, ind_metal = estimate.total_by_category("indicated")
    inf_t, inf_g, inf_metal = estimate.total_by_category("inferred")

    total_mi = mi_t + ind_t
    estimate.total_mi_tonnes_mt = total_mi if total_mi > 0 else None
    estimate.total_mi_contained = mi_metal + ind_metal if (mi_metal + ind_metal) > 0 else None
    estimate.total_inferred_tonnes_mt = inf_t if inf_t > 0 else None

    return estimate


def _build_domains(facts: dict) -> list[GeologicalDomain]:
    """Build geological domains from extracted facts."""
    domains: list[GeologicalDomain] = []
    raw_domains = facts.get("domains", [])
    for d in raw_domains:
        domains.append(GeologicalDomain(
            domain_id=d.get("domain_id", f"domain_{len(domains)+1}"),
            name=d.get("name", f"Domain {len(domains)+1}"),
            primary_element=d.get("primary_element", "Unknown"),
            grade_unit=d.get("grade_unit", ""),
            sample_count=d.get("sample_count", 0),
            mean_grade=d.get("mean_grade"),
            cv=d.get("cv"),
            mineralisation_style=d.get("mineralisation_style"),
            host_lithology=d.get("host_lithology"),
            average_drill_spacing_m=d.get("average_drill_spacing_m"),
            continuity_assessment=d.get("continuity_assessment"),
        ))
    return domains


def normalise_geology(project_id: str, run_id: str) -> list[str]:
    """
    Reads from normalized/staging/entity_extraction/geological_facts/ (LLM extraction outputs).
    Also checks normalized/assays/ for domain information.
    Builds GeologicalPicture from all available data.
    Writes:
        normalized/geology/resource_estimate_summary.parquet
        normalized/interpreted/geology/geological_risks.json
        normalized/interpreted/risk/missing_data_flags.json
        normalized/interpreted/risk/data_assessments.json
    Returns list of warnings.
    """
    warnings: list[str] = []
    log.info("Normalising geology for project=%s", project_id)

    norm_root = project_normalized(project_id)
    staging_dir = norm_root / "staging" / "entity_extraction" / "geological_facts"

    facts = _load_geological_facts(staging_dir)
    if not facts:
        warnings.append(
            "No geological_facts extraction outputs found in "
            "normalized/staging/entity_extraction/geological_facts/. "
            "Geology normalisation proceeding with empty facts."
        )

    resource_estimate = _build_resource_estimate(project_id, facts)
    if resource_estimate is None:
        warnings.append(
            "No resource estimate could be built from extraction outputs. "
            "Geological picture will have no resource estimate."
        )

    domains = _build_domains(facts)

    # Check drillhole data presence from normalized/drilling
    drillhole_count: int | None = None
    drilling_dir = norm_root / "drilling"
    collars_parquet = drilling_dir / "collars.parquet"
    if collars_parquet.exists():
        try:
            from engine.io.parquet_io import parquet_row_count
            drillhole_count = parquet_row_count(collars_parquet)
        except Exception:
            pass

    picture = GeologicalPicture(
        project_id=project_id,
        resource_estimate=resource_estimate,
        domains=domains,
        drillhole_count=drillhole_count,
        notes=facts.get("notes"),
    )

    # --- Write resource estimate summary parquet ---
    geology_dir = norm_root / "geology"
    geology_dir.mkdir(parents=True, exist_ok=True)

    resource_rows: list[dict] = []
    if resource_estimate is not None:
        for cat in resource_estimate.categories:
            resource_rows.append({
                "category": cat.category,
                "domain": cat.domain or "",
                "tonnes_mt": cat.tonnes,
                "grade": cat.grade,
                "grade_unit": cat.grade_unit,
                "contained_metal": cat.contained_metal,
                "contained_metal_unit": cat.contained_metal_unit,
                "cut_off_grade": cat.cut_off_grade,
                "cut_off_unit": cat.cut_off_unit,
                "primary_element": resource_estimate.primary_element,
                "effective_date": resource_estimate.effective_date,
                "classification_system": resource_estimate.classification_system,
                "qualified_person": resource_estimate.qualified_person,
            })

    if resource_rows:
        dicts_to_parquet(resource_rows, geology_dir / "resource_estimate_summary.parquet")
        log.info("Written %d resource category rows", len(resource_rows))
    else:
        warnings.append(
            "No resource categories available — resource_estimate_summary.parquet not written."
        )

    # --- Geological risk assessment ---
    risk_assessments = assess_geological_picture(picture)
    interpreted_geology_dir = norm_root / "interpreted" / "geology"
    interpreted_geology_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        interpreted_geology_dir / "geological_risks.json",
        {"project_id": project_id, "run_id": run_id, "risks": risk_assessments},
    )
    log.info("Written geological_risks.json with %d assessments", len(risk_assessments))

    # --- Missing data flags ---
    missing_flags = check_missing_geological_data(picture)
    risk_dir = norm_root / "interpreted" / "risk"
    risk_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        risk_dir / "missing_data_flags.json",
        {"project_id": project_id, "run_id": run_id, "flags": missing_flags},
    )
    log.info("Written missing_data_flags.json with %d flags", len(missing_flags))

    # --- Combined data assessments ---
    combined_assessments = risk_assessments + missing_flags
    write_data_assessments(project_id, combined_assessments, run_id=run_id)
    write_json(
        risk_dir / "data_assessments.json",
        {
            "project_id": project_id,
            "run_id": run_id,
            "assessments": combined_assessments,
        },
    )
    log.info("Written data_assessments.json with %d total items", len(combined_assessments))

    log.info("Geology normalisation complete | %d warnings", len(warnings))
    return warnings

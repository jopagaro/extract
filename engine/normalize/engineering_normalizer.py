"""
Engineering normalizer.

Reads engineering study data (production schedules, capex, opex line items)
from raw/engineering/ and LLM extraction outputs.
Writes normalised Parquet files for use by the economics normalizer.
"""

from __future__ import annotations

import json
from pathlib import Path

from engine.core.logging import get_logger
from engine.core.paths import project_normalized, project_raw
from engine.io.parquet_io import dicts_to_parquet

log = get_logger(__name__)


def _load_economic_facts(staging_dir: Path) -> dict:
    facts: dict = {}
    if not staging_dir.exists():
        return facts
    for jf in sorted(staging_dir.glob("*.json")):
        try:
            with jf.open("r", encoding="utf-8") as f:
                data = json.load(f)
            facts.update(data)
        except Exception as e:
            log.warning("Could not load %s: %s", jf.name, e)
    return facts


def normalise_engineering(project_id: str, run_id: str) -> list[str]:
    """
    Reads engineering data from:
        raw/engineering/ (Excel, CSV)
        normalized/staging/entity_extraction/economic_facts/ (LLM extracted)

    Writes (if data available):
        normalized/engineering/production_schedule.parquet
        normalized/engineering/capex_line_items.parquet
        normalized/engineering/opex_line_items.parquet

    Returns list of warnings.
    """
    warnings: list[str] = []
    log.info("Normalising engineering data for project=%s", project_id)

    norm_root = project_normalized(project_id)
    staging_dir = norm_root / "staging" / "entity_extraction" / "economic_facts"
    facts = _load_economic_facts(staging_dir)
    eng_dir = norm_root / "engineering"

    # --- Production schedule ---
    raw_prod = facts.get("production_schedule", [])
    prod_rows: list[dict] = []
    if isinstance(raw_prod, list):
        for item in raw_prod:
            if isinstance(item, dict):
                try:
                    prod_rows.append({
                        "year": int(item.get("year", 1)),
                        "ore_tonnes": float(item.get("ore_tonnes", 0)),
                        "head_grade": float(item.get("head_grade", 0)),
                        "grade_unit": str(item.get("grade_unit", "g/t")),
                        "recovery_percent": float(item.get("recovery_percent", 90.0)),
                        "commodity": str(item.get("commodity", "Au")),
                        "metal_unit": str(item.get("metal_unit", "oz")),
                    })
                except (ValueError, TypeError):
                    pass

    if prod_rows:
        eng_dir.mkdir(parents=True, exist_ok=True)
        dicts_to_parquet(prod_rows, eng_dir / "production_schedule.parquet")
        log.info("Written %d production schedule rows", len(prod_rows))
    else:
        warnings.append(
            "No engineering production schedule data found — "
            "economics normalizer will build schedule from resource estimate."
        )

    # --- CAPEX line items ---
    raw_capex = facts.get("capex_line_items") or facts.get("capex", {})
    capex_rows: list[dict] = []
    if isinstance(raw_capex, list):
        for item in raw_capex:
            if isinstance(item, dict):
                try:
                    capex_rows.append({
                        "name": str(item.get("name", "CAPEX Item")),
                        "year": int(item.get("year", 0)),
                        "amount": float(item.get("amount", 0)),
                        "category": str(item.get("category", "initial")),
                        "notes": str(item.get("notes", "")),
                    })
                except (ValueError, TypeError):
                    pass

    if capex_rows:
        eng_dir.mkdir(parents=True, exist_ok=True)
        dicts_to_parquet(capex_rows, eng_dir / "capex_line_items.parquet")
        log.info("Written %d CAPEX rows", len(capex_rows))
    else:
        warnings.append(
            "No engineering CAPEX line items found — "
            "economics normalizer will use defaults or LLM extraction."
        )

    # --- OPEX line items ---
    raw_opex = facts.get("opex_line_items") or facts.get("opex", {})
    opex_rows: list[dict] = []
    if isinstance(raw_opex, list):
        for item in raw_opex:
            if isinstance(item, dict):
                try:
                    opex_rows.append({
                        "name": str(item.get("name", "OPEX Item")),
                        "category": str(item.get("category", "")),
                        "amount": float(item.get("amount", 0)),
                        "unit": str(item.get("unit", "USD/t")),
                        "notes": str(item.get("notes", "")),
                    })
                except (ValueError, TypeError):
                    pass

    if opex_rows:
        eng_dir.mkdir(parents=True, exist_ok=True)
        dicts_to_parquet(opex_rows, eng_dir / "opex_line_items.parquet")
        log.info("Written %d OPEX rows", len(opex_rows))
    else:
        warnings.append(
            "No engineering OPEX line items found — "
            "economics normalizer will use defaults or LLM extraction."
        )

    log.info("Engineering normalisation complete | %d warnings", len(warnings))
    return warnings

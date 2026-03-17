"""
Metallurgy normalizer.

Reads metallurgical recovery data from LLM extractions and raw Excel files.
Writes normalised recovery assumptions to Parquet.
"""

from __future__ import annotations

import json
from pathlib import Path

from engine.core.logging import get_logger
from engine.core.paths import project_normalized, project_raw
from engine.io.parquet_io import dicts_to_parquet

log = get_logger(__name__)

_DEFAULT_RECOVERIES: dict[str, float] = {
    "Au": 90.0,
    "Ag": 75.0,
    "Cu": 87.0,
    "Zn": 85.0,
    "Pb": 80.0,
    "Mo": 80.0,
    "Ni": 78.0,
    "Co": 75.0,
}


def _load_economic_facts(staging_dir: Path) -> dict:
    """Load economic facts JSON files from the staging extraction directory."""
    facts: dict = {}
    if not staging_dir.exists():
        return facts
    for json_file in sorted(staging_dir.glob("*.json")):
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            facts.update(data)
        except Exception as e:
            log.warning("Could not load economic facts %s: %s", json_file.name, e)
    return facts


def _try_load_excel_recovery(excel_dir: Path) -> list[dict]:
    """Attempt to extract recovery data from Excel files in raw/metallurgy/."""
    rows: list[dict] = []
    if not excel_dir.exists():
        return rows

    excel_files = list(excel_dir.glob("*.xlsx")) + list(excel_dir.glob("*.xls"))
    for ef in excel_files:
        try:
            from engine.io.excel_io import read_excel
            df = read_excel(ef)
            # Try to find recovery column
            for col in df.columns:
                if "recov" in col.lower():
                    for row in df.to_dicts():
                        commodity = row.get("commodity") or row.get("element") or "Unknown"
                        recovery = row.get(col)
                        if recovery is not None:
                            try:
                                recovery_pct = float(recovery)
                                if recovery_pct > 1.0:
                                    # Already a percentage
                                    pass
                                else:
                                    recovery_pct *= 100.0
                                rows.append({
                                    "commodity": str(commodity),
                                    "recovery_percent": recovery_pct,
                                    "basis": "testwork",
                                    "testwork_type": "Excel import",
                                    "variability_range_low": None,
                                    "variability_range_high": None,
                                    "source": ef.name,
                                })
                            except (ValueError, TypeError):
                                pass
                    break
        except Exception as e:
            log.warning("Could not read Excel file %s: %s", ef.name, e)

    return rows


def normalise_metallurgy(project_id: str, run_id: str) -> list[str]:
    """
    Reads from normalized/staging/entity_extraction/economic_facts/ for recovery data.
    Also reads any Excel files in raw/metallurgy/.
    Writes to normalized/metallurgy/recovery_assumptions.parquet with columns:
        commodity, recovery_percent, basis, testwork_type, variability_range_low,
        variability_range_high, source
    Returns list of warnings including if only default/assumed recovery is available.
    """
    warnings: list[str] = []
    log.info("Normalising metallurgy for project=%s", project_id)

    norm_root = project_normalized(project_id)
    raw_root = project_raw(project_id)
    staging_dir = norm_root / "staging" / "entity_extraction" / "economic_facts"

    facts = _load_economic_facts(staging_dir)
    recovery_rows: list[dict] = []

    # Try to get recovery from LLM extraction
    raw_recovery = (
        facts.get("metallurgy", {}).get("recovery") or
        facts.get("recovery") or
        facts.get("recoveries") or
        []
    )

    if isinstance(raw_recovery, list):
        for item in raw_recovery:
            if isinstance(item, dict):
                recovery_pct = item.get("recovery_percent") or item.get("recovery")
                if recovery_pct is not None:
                    try:
                        rpct = float(recovery_pct)
                        if rpct <= 1.0:
                            rpct *= 100.0
                        recovery_rows.append({
                            "commodity": item.get("commodity", "Unknown"),
                            "recovery_percent": rpct,
                            "basis": item.get("basis", "testwork"),
                            "testwork_type": item.get("testwork_type", ""),
                            "variability_range_low": item.get("variability_range_low"),
                            "variability_range_high": item.get("variability_range_high"),
                            "source": "llm_extraction",
                        })
                    except (ValueError, TypeError):
                        pass
    elif isinstance(raw_recovery, dict):
        for commodity, value in raw_recovery.items():
            try:
                rpct = float(value)
                if rpct <= 1.0:
                    rpct *= 100.0
                recovery_rows.append({
                    "commodity": commodity,
                    "recovery_percent": rpct,
                    "basis": "assumed",
                    "testwork_type": "",
                    "variability_range_low": None,
                    "variability_range_high": None,
                    "source": "llm_extraction",
                })
            except (ValueError, TypeError):
                pass

    # Also try Excel
    excel_rows = _try_load_excel_recovery(raw_root / "metallurgy")
    recovery_rows.extend(excel_rows)

    # If no recovery found, use defaults and warn heavily
    if not recovery_rows:
        warnings.append(
            "CRITICAL: No metallurgical recovery data found in LLM extractions or raw/metallurgy/. "
            "Falling back to commodity-class defaults. These are speculative and represent "
            "a material risk to all economic projections. Testwork results must be provided."
        )

        # Determine primary element from resource summary if available
        resource_parquet = norm_root / "geology" / "resource_estimate_summary.parquet"
        primary_element = "Au"  # fallback default
        if resource_parquet.exists():
            try:
                from engine.io.parquet_io import parquet_to_dicts
                resource_rows = parquet_to_dicts(resource_parquet)
                if resource_rows:
                    primary_element = resource_rows[0].get("primary_element", "Au")
            except Exception:
                pass

        default_recovery = _DEFAULT_RECOVERIES.get(primary_element, 85.0)
        recovery_rows.append({
            "commodity": primary_element,
            "recovery_percent": default_recovery,
            "basis": "assumed_default",
            "testwork_type": "none",
            "variability_range_low": default_recovery - 10.0,
            "variability_range_high": default_recovery + 5.0,
            "source": "system_default",
        })
        warnings.append(
            f"Using default recovery of {default_recovery}% for {primary_element}. "
            "This assumption must be replaced with actual testwork data."
        )
    else:
        # Warn if recovery source is weak
        assumed_count = sum(1 for r in recovery_rows if r.get("basis") in ("assumed", "assumed_default"))
        if assumed_count > 0:
            warnings.append(
                f"{assumed_count} recovery assumption(s) are based on assumed/default values, "
                "not testwork results. Economic projections are subject to metallurgical uncertainty."
            )

    # Write output
    metall_dir = norm_root / "metallurgy"
    metall_dir.mkdir(parents=True, exist_ok=True)
    dicts_to_parquet(recovery_rows, metall_dir / "recovery_assumptions.parquet")
    log.info("Written %d recovery assumption rows", len(recovery_rows))

    log.info("Metallurgy normalisation complete | %d warnings", len(warnings))
    return warnings

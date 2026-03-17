"""
Economics normalizer.

Assembles EconomicsInputBook from all normalised layers and writes
the economic input book JSON for use by the DCF model.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.core.logging import get_logger
from engine.core.manifests import write_json
from engine.core.paths import project_normalized, project_raw
from engine.economics.models import (
    CapexItem,
    CommodityPrice,
    DiscountingAssumptions,
    EconomicsInputBook,
    FiscalTerms,
    OpexAssumptions,
    ProductionPeriod,
    RoyaltyTerm,
)
from engine.io.parquet_io import parquet_to_dicts

log = get_logger(__name__)

# Default economic assumptions (used when data is not available)
_DEFAULT_GOLD_PRICE_USD_OZ = 1_900.0
_DEFAULT_COPPER_PRICE_USD_LB = 3.80
_DEFAULT_DISCOUNT_RATE = 8.0
_DEFAULT_TAX_RATE = 30.0
_DEFAULT_MINE_LIFE = 10
_DEFAULT_THROUGHPUT_MTPA = 2.0
_DEFAULT_RECOVERY = 90.0
_DEFAULT_MINING_COST = 3.50
_DEFAULT_PROCESSING_COST = 12.00
_DEFAULT_GANDA_COST = 2.50


def _load_json_safe(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("Could not load JSON %s: %s", path, e)
        return {}


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
            log.warning("Could not load economic facts %s: %s", jf.name, e)
    return facts


def _build_production_schedule(
    resource_rows: list[dict],
    recovery_rows: list[dict],
    engineering_rows: list[dict],
    warnings: list[str],
) -> list[ProductionPeriod]:
    """Build a production schedule from available data."""
    schedule: list[ProductionPeriod] = []

    # Use engineering production schedule if available
    if engineering_rows:
        for row in engineering_rows:
            try:
                schedule.append(ProductionPeriod(
                    year=int(row.get("year", 1)),
                    ore_tonnes=float(row.get("ore_tonnes", 0)),
                    head_grade=float(row.get("head_grade", 0)),
                    grade_unit=str(row.get("grade_unit", "g/t")),
                    recovery_percent=float(row.get("recovery_percent", _DEFAULT_RECOVERY)),
                    commodity=str(row.get("commodity", "Unknown")),
                    metal_unit=str(row.get("metal_unit", "oz")),
                ))
            except (ValueError, TypeError) as e:
                warnings.append(f"Production schedule row error: {e}")
        return schedule

    # Build from resource estimate + recovery assumptions
    if not resource_rows:
        warnings.append(
            "No resource estimate data available — production schedule uses illustrative defaults. "
            "All economic outputs are speculative."
        )
        # Create illustrative schedule
        primary_element = "Au"
        grade = 1.5
        grade_unit = "g/t"
        recovery = _DEFAULT_RECOVERY
        metal_unit = "oz"
    else:
        # Aggregate M&I resources
        mi_categories = [
            r for r in resource_rows
            if r.get("category", "").lower() in ("measured", "indicated")
        ]
        if not mi_categories:
            mi_categories = resource_rows  # fall back to all
            warnings.append(
                "No Measured or Indicated resources — using all categories for production schedule."
            )

        total_tonnes = sum((r.get("tonnes_mt") or 0.0) for r in mi_categories)
        primary_element = (mi_categories[0].get("primary_element") or "Au") if mi_categories else "Au"
        grade_unit = (mi_categories[0].get("grade_unit") or "g/t") if mi_categories else "g/t"

        # Weighted average grade
        graded = [(r.get("tonnes_mt") or 0.0, r.get("grade") or 0.0) for r in mi_categories]
        total_t_for_grade = sum(t for t, _ in graded)
        if total_t_for_grade > 0:
            grade = sum(t * g for t, g in graded) / total_t_for_grade
        else:
            grade = 1.5
            warnings.append("Could not calculate weighted average grade — using 1.5 g/t default.")

        # Recovery
        if recovery_rows:
            # Match primary element
            matching = [
                r for r in recovery_rows
                if r.get("commodity", "").upper()[:2] == primary_element.upper()[:2]
            ]
            recovery = float((matching[0] if matching else recovery_rows[0]).get("recovery_percent", _DEFAULT_RECOVERY))
        else:
            recovery = _DEFAULT_RECOVERY
            warnings.append("No recovery data — using default recovery for production schedule.")

        metal_unit = "oz" if primary_element.upper() in ("AU", "AG", "PT", "PD") else "t"

        if total_tonnes <= 0:
            total_tonnes = _DEFAULT_THROUGHPUT_MTPA * _DEFAULT_MINE_LIFE
            warnings.append(
                f"Resource tonnes not available — using default {total_tonnes:.0f} Mt "
                f"({_DEFAULT_THROUGHPUT_MTPA} Mtpa for {_DEFAULT_MINE_LIFE} years)."
            )

        mine_life = max(1, round(total_tonnes / _DEFAULT_THROUGHPUT_MTPA))
        mine_life = min(mine_life, 30)  # cap at 30 years
        annual_tonnes = (total_tonnes / mine_life) * 1_000_000  # Mt → t

        # Year 0 = construction
        schedule.append(ProductionPeriod(
            year=0,
            ore_tonnes=0.0,
            head_grade=0.0,
            grade_unit=grade_unit,
            recovery_percent=recovery,
            commodity=primary_element,
            metal_unit=metal_unit,
        ))

        for yr in range(1, mine_life + 1):
            schedule.append(ProductionPeriod(
                year=yr,
                ore_tonnes=annual_tonnes,
                head_grade=grade,
                grade_unit=grade_unit,
                recovery_percent=recovery,
                commodity=primary_element,
                metal_unit=metal_unit,
            ))

        return schedule

    # Illustrative fallback schedule
    schedule.append(ProductionPeriod(
        year=0,
        ore_tonnes=0.0,
        head_grade=0.0,
        grade_unit=grade_unit,
        recovery_percent=recovery,
        commodity=primary_element,
        metal_unit=metal_unit,
    ))
    for yr in range(1, _DEFAULT_MINE_LIFE + 1):
        schedule.append(ProductionPeriod(
            year=yr,
            ore_tonnes=_DEFAULT_THROUGHPUT_MTPA * 1_000_000,
            head_grade=grade,
            grade_unit=grade_unit,
            recovery_percent=recovery,
            commodity=primary_element,
            metal_unit=metal_unit,
        ))

    return schedule


def _build_capex(capex_rows: list[dict], facts: dict, warnings: list[str]) -> list[CapexItem]:
    """Build CAPEX items from available data."""
    items: list[CapexItem] = []

    if capex_rows:
        for row in capex_rows:
            try:
                items.append(CapexItem(
                    name=str(row.get("name", "Unknown")),
                    year=int(row.get("year", 0)),
                    amount=float(row.get("amount", 0)),
                    category=str(row.get("category", "initial")),
                    notes=str(row.get("notes", "")),
                ))
            except (ValueError, TypeError) as e:
                warnings.append(f"CAPEX row error: {e}")
        return items

    # Try LLM extraction
    raw_capex = facts.get("capex") or facts.get("capital_costs", {})
    if isinstance(raw_capex, dict):
        total = raw_capex.get("total_musd") or raw_capex.get("total")
        if total:
            try:
                items.append(CapexItem(
                    name="Total Initial CAPEX",
                    year=0,
                    amount=float(total),
                    category="initial",
                    notes="LLM extracted",
                ))
                return items
            except (ValueError, TypeError):
                pass
    elif isinstance(raw_capex, list):
        for item in raw_capex:
            if isinstance(item, dict):
                try:
                    items.append(CapexItem(
                        name=str(item.get("name", "CAPEX Item")),
                        year=int(item.get("year", 0)),
                        amount=float(item.get("amount", 0)),
                        category=str(item.get("category", "initial")),
                    ))
                except (ValueError, TypeError):
                    pass
        if items:
            return items

    # Default
    warnings.append(
        "CAPEX data not found — using illustrative default of 150 M USD. "
        "Actual CAPEX must be sourced from a feasibility study or cost estimate."
    )
    items.append(CapexItem(
        name="Illustrative Initial CAPEX",
        year=0,
        amount=150.0,
        category="initial",
        notes="system_default",
    ))
    return items


def _build_opex(opex_rows: list[dict], facts: dict, warnings: list[str]) -> OpexAssumptions:
    """Build OPEX assumptions from available data."""
    if opex_rows:
        mining = next((r["amount"] for r in opex_rows if "mining" in r.get("category", "").lower()), None)
        processing = next((r["amount"] for r in opex_rows if "process" in r.get("category", "").lower()), None)
        ganda = next((r["amount"] for r in opex_rows if "g&a" in r.get("category", "").lower() or "admin" in r.get("category", "").lower()), None)

        if mining and processing:
            return OpexAssumptions(
                mining_cost_per_tonne_ore=float(mining),
                processing_cost_per_tonne_ore=float(processing),
                ganda_cost_per_tonne_ore=float(ganda) if ganda else _DEFAULT_GANDA_COST,
            )

    # Try LLM
    raw_opex = facts.get("opex") or facts.get("operating_costs", {})
    if isinstance(raw_opex, dict):
        mining = raw_opex.get("mining_cost_per_tonne") or raw_opex.get("mining")
        processing = raw_opex.get("processing_cost_per_tonne") or raw_opex.get("processing")
        ganda = raw_opex.get("ganda") or raw_opex.get("ga")
        if mining:
            try:
                return OpexAssumptions(
                    mining_cost_per_tonne_ore=float(mining),
                    processing_cost_per_tonne_ore=float(processing) if processing else _DEFAULT_PROCESSING_COST,
                    ganda_cost_per_tonne_ore=float(ganda) if ganda else _DEFAULT_GANDA_COST,
                )
            except (ValueError, TypeError):
                pass

    warnings.append(
        f"OPEX data not found — using illustrative defaults: "
        f"mining={_DEFAULT_MINING_COST} USD/t, processing={_DEFAULT_PROCESSING_COST} USD/t, "
        f"G&A={_DEFAULT_GANDA_COST} USD/t. These must be confirmed from a study."
    )
    return OpexAssumptions(
        mining_cost_per_tonne_ore=_DEFAULT_MINING_COST,
        processing_cost_per_tonne_ore=_DEFAULT_PROCESSING_COST,
        ganda_cost_per_tonne_ore=_DEFAULT_GANDA_COST,
    )


def _build_commodity_prices(price_deck: dict, facts: dict, warnings: list[str]) -> list[CommodityPrice]:
    """Build commodity price assumptions."""
    prices: list[CommodityPrice] = []

    if price_deck:
        for commodity, data in price_deck.items():
            if isinstance(data, dict):
                try:
                    prices.append(CommodityPrice(
                        commodity=commodity,
                        price=float(data.get("price", 0)),
                        unit=str(data.get("unit", "USD/oz")),
                        scenario="base_case",
                    ))
                except (ValueError, TypeError):
                    pass
            elif isinstance(data, (int, float)):
                prices.append(CommodityPrice(
                    commodity=commodity,
                    price=float(data),
                    unit="USD/oz",
                    scenario="base_case",
                ))
        if prices:
            return prices

    # Try LLM
    raw_prices = facts.get("commodity_prices") or facts.get("prices", {})
    if isinstance(raw_prices, list):
        for item in raw_prices:
            if isinstance(item, dict):
                try:
                    prices.append(CommodityPrice(
                        commodity=str(item.get("commodity", "Unknown")),
                        price=float(item.get("price", 0)),
                        unit=str(item.get("unit", "USD/oz")),
                    ))
                except (ValueError, TypeError):
                    pass
    elif isinstance(raw_prices, dict):
        for commodity, price in raw_prices.items():
            try:
                prices.append(CommodityPrice(
                    commodity=commodity,
                    price=float(price),
                    unit="USD/oz",
                ))
            except (ValueError, TypeError):
                pass

    if prices:
        return prices

    warnings.append(
        f"No commodity price data found — using illustrative gold default of "
        f"USD {_DEFAULT_GOLD_PRICE_USD_OZ}/oz. Actual price deck must be specified."
    )
    prices.append(CommodityPrice(
        commodity="Au",
        price=_DEFAULT_GOLD_PRICE_USD_OZ,
        unit="USD/oz",
        scenario="base_case",
    ))
    return prices


def normalise_economics(project_id: str, run_id: str) -> list[str]:
    """
    Reads from:
        normalized/geology/resource_estimate_summary.parquet
        normalized/metallurgy/recovery_assumptions.parquet
        normalized/engineering/production_schedule.parquet (if exists)
        normalized/engineering/capex_line_items.parquet (if exists)
        normalized/engineering/opex_line_items.parquet (if exists)
        normalized/economics/price_decks/base_case.json (if exists)
        normalized/staging/entity_extraction/economic_facts/ (LLM extracted)

    Assembles EconomicsInputBook for base_case scenario.
    Writes: normalized/economics/model_inputs/economic_input_book.json
    Returns list of warnings for every assumption that is missing or defaulted.
    """
    warnings: list[str] = []
    log.info("Normalising economics for project=%s", project_id)

    norm_root = project_normalized(project_id)
    staging_dir = norm_root / "staging" / "entity_extraction" / "economic_facts"

    facts = _load_economic_facts(staging_dir)

    # Load resource summary
    resource_parquet = norm_root / "geology" / "resource_estimate_summary.parquet"
    resource_rows: list[dict] = []
    if resource_parquet.exists():
        try:
            resource_rows = parquet_to_dicts(resource_parquet)
        except Exception as e:
            warnings.append(f"Could not read resource_estimate_summary.parquet: {e}")

    if not resource_rows:
        warnings.append(
            "Resource estimate summary not available — "
            "production schedule will use illustrative defaults."
        )

    # Load recovery assumptions
    recovery_parquet = norm_root / "metallurgy" / "recovery_assumptions.parquet"
    recovery_rows: list[dict] = []
    if recovery_parquet.exists():
        try:
            recovery_rows = parquet_to_dicts(recovery_parquet)
        except Exception as e:
            warnings.append(f"Could not read recovery_assumptions.parquet: {e}")

    # Load engineering data
    eng_prod_parquet = norm_root / "engineering" / "production_schedule.parquet"
    eng_prod_rows: list[dict] = []
    if eng_prod_parquet.exists():
        try:
            eng_prod_rows = parquet_to_dicts(eng_prod_parquet)
        except Exception as e:
            warnings.append(f"Could not read production_schedule.parquet: {e}")

    capex_parquet = norm_root / "engineering" / "capex_line_items.parquet"
    capex_rows: list[dict] = []
    if capex_parquet.exists():
        try:
            capex_rows = parquet_to_dicts(capex_parquet)
        except Exception as e:
            warnings.append(f"Could not read capex_line_items.parquet: {e}")

    opex_parquet = norm_root / "engineering" / "opex_line_items.parquet"
    opex_rows: list[dict] = []
    if opex_parquet.exists():
        try:
            opex_rows = parquet_to_dicts(opex_parquet)
        except Exception as e:
            warnings.append(f"Could not read opex_line_items.parquet: {e}")

    # Load price deck
    price_deck_path = norm_root / "economics" / "price_decks" / "base_case.json"
    price_deck = _load_json_safe(price_deck_path)
    if price_deck:
        log.info("Loaded price deck from base_case.json")

    # Assemble components
    production_schedule = _build_production_schedule(
        resource_rows, recovery_rows, eng_prod_rows, warnings
    )
    capex_items = _build_capex(capex_rows, facts, warnings)
    opex_assumptions = _build_opex(opex_rows, facts, warnings)
    commodity_prices = _build_commodity_prices(price_deck, facts, warnings)

    # Fiscal terms
    fiscal_data = facts.get("fiscal_terms") or facts.get("fiscal", {})
    tax_rate = _DEFAULT_TAX_RATE
    royalties: list[RoyaltyTerm] = []

    if isinstance(fiscal_data, dict):
        try:
            tax_rate = float(fiscal_data.get("corporate_tax_rate_percent", _DEFAULT_TAX_RATE))
        except (ValueError, TypeError):
            pass
        raw_royalties = fiscal_data.get("royalties", [])
        if isinstance(raw_royalties, list):
            for r in raw_royalties:
                if isinstance(r, dict):
                    try:
                        royalties.append(RoyaltyTerm(
                            name=str(r.get("name", "Royalty")),
                            rate_percent=float(r.get("rate_percent", 0)),
                            basis=str(r.get("basis", "gross_revenue")),
                        ))
                    except (ValueError, TypeError):
                        pass

    if tax_rate == _DEFAULT_TAX_RATE:
        warnings.append(
            f"Corporate tax rate not found — using default of {_DEFAULT_TAX_RATE}%. "
            "Actual jurisdiction tax rate must be confirmed."
        )

    if not royalties:
        warnings.append(
            "No royalty terms found — assuming zero royalties. "
            "Jurisdiction-specific royalties must be confirmed."
        )

    fiscal_terms = FiscalTerms(
        corporate_tax_rate_percent=tax_rate,
        royalties=royalties,
    )

    discounting_data = facts.get("discounting") or {}
    discount_rate = _DEFAULT_DISCOUNT_RATE
    if isinstance(discounting_data, dict):
        try:
            discount_rate = float(discounting_data.get("discount_rate_percent", _DEFAULT_DISCOUNT_RATE))
        except (ValueError, TypeError):
            pass

    if discount_rate == _DEFAULT_DISCOUNT_RATE:
        warnings.append(
            f"Discount rate not specified — using default WACC of {_DEFAULT_DISCOUNT_RATE}%. "
            "This should be set based on project risk profile and jurisdiction."
        )

    discounting = DiscountingAssumptions(discount_rate_percent=discount_rate)

    # Compute initial capex total for reference
    initial_capex_total = sum(
        item.amount for item in capex_items
        if item.category in ("initial", "development")
    )

    input_book = EconomicsInputBook(
        project_id=project_id,
        scenario="base_case",
        production_schedule=production_schedule,
        capex_items=capex_items,
        opex_assumptions=opex_assumptions,
        commodity_prices=commodity_prices,
        fiscal_terms=fiscal_terms,
        discounting=discounting,
        initial_capex_currency_musd=initial_capex_total,
        notes=f"Assembled by economics normalizer | run_id={run_id}",
    )

    # Serialise to JSON — dataclasses don't auto-serialise so we do it manually
    def serialise(obj: Any) -> Any:
        if hasattr(obj, "__dataclass_fields__"):
            return {k: serialise(v) for k, v in asdict(obj).items()}
        if isinstance(obj, list):
            return [serialise(i) for i in obj]
        return obj

    output_dict = serialise(input_book)
    output_dict["assembled_at"] = datetime.now(timezone.utc).isoformat()
    output_dict["run_id"] = run_id

    econ_dir = norm_root / "economics" / "model_inputs"
    econ_dir.mkdir(parents=True, exist_ok=True)
    write_json(econ_dir / "economic_input_book.json", output_dict)
    log.info("Written economic_input_book.json")

    log.info("Economics normalisation complete | %d warnings", len(warnings))
    return warnings

"""
Build an EconomicsInputBook from LLM-extracted data.

Converts the JSON outputs of extract_financial_terms and extract_mine_plan_inputs
into the typed dataclasses required by the DCF engine.

Returns None if the extracted data is insufficient to run a meaningful DCF model
(no production schedule, no CAPEX, no OPEX, or no commodity prices).
"""

from __future__ import annotations

from typing import Any

from engine.core.logging import get_logger
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

log = get_logger(__name__)

# Defaults applied when values are absent from source documents
_DEFAULT_DISCOUNT_RATE = 8.0
_DEFAULT_TAX_RATE = 30.0
_DEFAULT_RECOVERY = 90.0
_DEFAULT_DEPRECIATION_YEARS = 10


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------

def _parse_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _normalize_to_musd(amount: float | None, unit: str | None) -> float | None:
    """
    Normalise a currency amount to USD millions.

    Handles common unit strings from LLM extraction:
      "M$", "MUSD", "USD millions", "$ million"  → keep as-is
      "B$", "billion"                              → multiply by 1 000
      "K$", "USD thousands"                        → divide by 1 000
      Raw USD (very large number)                  → divide by 1 000 000
    """
    if amount is None:
        return None

    u = (unit or "").lower().replace(" ", "")

    if any(x in u for x in ("musd", "m$", "usdm", "million", "$m")):
        return amount

    if any(x in u for x in ("busd", "b$", "billion")):
        return amount * 1_000.0

    if any(x in u for x in ("kusd", "k$", "thousand")):
        return amount / 1_000.0

    if "usd" in u or "$" in u:
        # Heuristic based on magnitude
        if amount > 1_000_000:
            return amount / 1_000_000.0   # raw USD → MUSD
        if amount > 10_000:
            return amount / 1_000.0       # KUSD → MUSD
        return amount                     # assume already MUSD

    # No recognisable unit — assume MUSD
    return amount


def _normalize_opex_to_per_tonne(
    cost: float | None,
    unit: str | None,
    avg_metal_per_year: float | None,
    avg_ore_tonnes_per_year: float | None,
) -> float | None:
    """
    Normalise an OPEX cost to USD per tonne of ore.

    If the cost is expressed per metal unit (oz, lb) and we know the average
    annual production and ore throughput, we can convert. Otherwise None.
    """
    if cost is None:
        return None

    u = (unit or "").lower()

    if any(x in u for x in ("/t ore", "/tonne ore", "/t milled", "/tonne milled", "/t ore mined")):
        return cost

    # Generic $/t  — assume per tonne ore
    if "/t" in u or "/tonne" in u:
        return cost

    # Per metal unit — convert via average production
    if "/oz" in u or "/troy" in u or "/lb" in u:
        if avg_metal_per_year and avg_ore_tonnes_per_year and avg_ore_tonnes_per_year > 0:
            return (cost * avg_metal_per_year) / avg_ore_tonnes_per_year
        log.debug("Cannot convert per-metal-unit OPEX without production figures")
        return None

    # Default: assume per tonne
    return cost


# ---------------------------------------------------------------------------
# Commodity / metal helpers
# ---------------------------------------------------------------------------

def _primary_commodity(price_assumptions: list[dict], project_facts: dict) -> str:
    if price_assumptions:
        c = price_assumptions[0].get("commodity")
        if c:
            return str(c).lower()
    for key in ("primary_commodity", "commodity", "primary_metal"):
        v = project_facts.get(key)
        if v:
            return str(v).lower()
    return "gold"


def _infer_metal_unit(commodity: str, price_unit: str | None) -> str:
    if price_unit:
        u = price_unit.lower()
        if "oz" in u:
            return "oz"
        if "/lb" in u:
            return "lb"
        if "/t" in u and "kt" not in u:
            return "t"
        if "/kg" in u:
            return "kg"
        if "koz" in u:
            return "koz"
    c = commodity.lower()
    if c in ("gold", "silver", "platinum", "palladium"):
        return "oz"
    if c in ("copper", "zinc", "lead", "nickel", "cobalt", "molybdenum"):
        return "lb"
    return "t"


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_input_book_from_llm(
    project_id: str,
    economic_assumptions: dict,
    mine_plan: dict,
    project_facts: dict,
) -> EconomicsInputBook | None:
    """
    Convert LLM extraction outputs into an EconomicsInputBook.

    Returns None if the data is insufficient to run a meaningful DCF model.
    All applied defaults are recorded in the returned book's `notes` field.
    """
    defaults: list[str] = []

    # ── Price assumptions (needed to identify primary commodity) ─────────────
    econ_data = economic_assumptions.get("economics") or {}
    price_assumptions: list[dict] = econ_data.get("commodity_price_assumptions") or []

    primary_commodity = _primary_commodity(price_assumptions, project_facts)
    price_unit = price_assumptions[0].get("unit") if price_assumptions else None
    metal_unit = _infer_metal_unit(primary_commodity, price_unit)

    # ── Production schedule ──────────────────────────────────────────────────
    raw_schedule: list[dict] = mine_plan.get("production_schedule") or []
    if not raw_schedule:
        log.info("DCF skipped: no production schedule in extracted mine plan data")
        return None

    production_schedule: list[ProductionPeriod] = []
    for row in raw_schedule:
        year_raw = row.get("year")
        try:
            year = int(year_raw)
        except (TypeError, ValueError):
            year = 1  # "average" row → treat as year 1

        ore_tonnes = _parse_float(row.get("ore_tonnes"))
        if not ore_tonnes:
            continue

        head_grade = _parse_float(row.get("ore_grade_primary")) or 0.0
        grade_unit = str(row.get("ore_grade_unit") or "g/t")
        contained_metal = _parse_float(row.get("contained_metal"))

        if contained_metal and contained_metal > 0:
            # Use directly extracted contained-metal value
            production_schedule.append(ProductionPeriod(
                year=year,
                ore_tonnes=ore_tonnes,
                head_grade=head_grade,
                grade_unit=grade_unit,
                recovery_percent=100.0,
                commodity=primary_commodity,
                metal_unit=metal_unit,
                contained_metal_produced=contained_metal,
            ))
        elif head_grade > 0:
            defaults.append(f"metallurgical_recovery={_DEFAULT_RECOVERY}% (default)")
            production_schedule.append(ProductionPeriod(
                year=year,
                ore_tonnes=ore_tonnes,
                head_grade=head_grade,
                grade_unit=grade_unit,
                recovery_percent=_DEFAULT_RECOVERY,
                commodity=primary_commodity,
                metal_unit=metal_unit,
            ))
        else:
            log.debug("Skipping schedule row year=%s — no grade or contained metal", year)

    if not production_schedule:
        log.info("DCF skipped: no valid production periods could be built from extracted data")
        return None

    production_schedule.sort(key=lambda p: p.year)
    mine_life = max(p.year for p in production_schedule)
    avg_ore_tonnes = sum(p.ore_tonnes for p in production_schedule) / len(production_schedule)

    # Average metal produced (for OPEX unit conversion if needed)
    avg_metal = (
        sum(p.contained_metal_produced for p in production_schedule) / len(production_schedule)
        if all(p.contained_metal_produced > 0 for p in production_schedule)
        else None
    )

    # ── CAPEX ────────────────────────────────────────────────────────────────
    capex_data = economic_assumptions.get("capex") or {}
    capex_items: list[CapexItem] = []

    initial_raw = _parse_float(capex_data.get("initial_capex"))
    initial_musd = _normalize_to_musd(initial_raw, capex_data.get("initial_capex_unit"))
    if initial_musd and initial_musd > 0:
        capex_items.append(CapexItem(
            name="Initial Capital",
            year=0,
            amount=initial_musd,
            category="initial",
        ))

    sust_unit = capex_data.get("sustaining_capex_unit")
    sust_total_raw = _parse_float(capex_data.get("sustaining_capex_total"))
    sust_peryear_raw = _parse_float(capex_data.get("sustaining_capex_per_year"))

    sust_per_year: float | None = None
    if sust_total_raw and mine_life > 0:
        total = _normalize_to_musd(sust_total_raw, sust_unit)
        if total:
            sust_per_year = total / mine_life
    elif sust_peryear_raw:
        sust_per_year = _normalize_to_musd(sust_peryear_raw, sust_unit)

    if sust_per_year and sust_per_year > 0:
        for yr in range(1, mine_life + 1):
            capex_items.append(CapexItem(
                name="Sustaining Capital",
                year=yr,
                amount=sust_per_year,
                category="sustaining",
            ))

    closure_raw = _parse_float(capex_data.get("closure_cost"))
    closure_musd = _normalize_to_musd(closure_raw, capex_data.get("closure_cost_unit"))
    if closure_musd and closure_musd > 0:
        capex_items.append(CapexItem(
            name="Closure and Reclamation",
            year=mine_life + 1,
            amount=closure_musd,
            category="closure",
        ))

    if not capex_items:
        log.info("DCF skipped: no CAPEX data found in extracted financial terms")
        return None

    # ── OPEX ─────────────────────────────────────────────────────────────────
    opex_data = economic_assumptions.get("opex") or {}
    cost_unit = opex_data.get("cost_unit")

    mining_cost = _normalize_opex_to_per_tonne(
        _parse_float(opex_data.get("mining_cost")), cost_unit, avg_metal, avg_ore_tonnes
    )
    processing_cost = _normalize_opex_to_per_tonne(
        _parse_float(opex_data.get("processing_cost")), cost_unit, avg_metal, avg_ore_tonnes
    )
    ganda_cost = _normalize_opex_to_per_tonne(
        _parse_float(opex_data.get("ganda_cost")), cost_unit, avg_metal, avg_ore_tonnes
    )

    # Fall back to total cash cost split proportionally
    if not (mining_cost or processing_cost):
        total_cost = _normalize_opex_to_per_tonne(
            _parse_float(opex_data.get("total_cash_cost")),
            opex_data.get("total_cash_cost_unit") or cost_unit,
            avg_metal,
            avg_ore_tonnes,
        )
        if total_cost and total_cost > 0:
            mining_cost = total_cost * 0.50
            processing_cost = total_cost * 0.35
            ganda_cost = (ganda_cost or total_cost * 0.15)
            defaults.append("OPEX split 50/35/15 mining/processing/G&A (inferred from total cash cost)")

    if not mining_cost:
        log.info("DCF skipped: no usable OPEX cost data in extracted financial terms")
        return None

    opex_assumptions = OpexAssumptions(
        mining_cost_per_tonne_ore=mining_cost,
        processing_cost_per_tonne_ore=processing_cost or 0.0,
        ganda_cost_per_tonne_ore=ganda_cost or 0.0,
    )

    # ── Commodity prices ──────────────────────────────────────────────────────
    commodity_prices: list[CommodityPrice] = []
    for pa in price_assumptions:
        price = _parse_float(pa.get("price"))
        if price and price > 0:
            commodity_prices.append(CommodityPrice(
                commodity=pa.get("commodity", primary_commodity),
                price=price,
                unit=pa.get("unit", f"USD/{metal_unit}"),
                scenario="base_case",
            ))

    if not commodity_prices:
        log.info("DCF skipped: no commodity price assumptions found in extracted data")
        return None

    # ── Fiscal terms ──────────────────────────────────────────────────────────
    tax_data = economic_assumptions.get("taxes") or {}
    tax_rate = _parse_float(tax_data.get("corporate_tax_rate_percent"))
    if tax_rate is None:
        tax_rate = _DEFAULT_TAX_RATE
        defaults.append(f"corporate_tax_rate={_DEFAULT_TAX_RATE}% (default)")

    royalty_terms: list[RoyaltyTerm] = []
    for r in (economic_assumptions.get("royalties") or []):
        rate = _parse_float(r.get("rate"))
        if rate is not None:
            royalty_terms.append(RoyaltyTerm(
                name=r.get("type", "Royalty"),
                rate_percent=rate,
                basis=r.get("basis", "gross_revenue"),
                payable_to=r.get("payable_to", ""),
            ))

    fiscal_terms = FiscalTerms(
        corporate_tax_rate_percent=tax_rate,
        royalties=royalty_terms,
        depreciation_years=_DEFAULT_DEPRECIATION_YEARS,
        loss_carry_forward=True,
        jurisdiction=tax_data.get("jurisdiction", ""),
    )

    # ── Discounting ───────────────────────────────────────────────────────────
    discount_rate = _parse_float(econ_data.get("discount_rate_percent"))
    if discount_rate is None:
        discount_rate = _DEFAULT_DISCOUNT_RATE
        defaults.append(f"discount_rate={_DEFAULT_DISCOUNT_RATE}% (default)")

    discounting = DiscountingAssumptions(
        discount_rate_percent=discount_rate,
        discounting_convention="mid_year",
    )

    if defaults:
        log.info("DCF model using defaults: %s", "; ".join(defaults))

    return EconomicsInputBook(
        project_id=project_id,
        scenario="base_case",
        production_schedule=production_schedule,
        capex_items=capex_items,
        opex_assumptions=opex_assumptions,
        commodity_prices=commodity_prices,
        fiscal_terms=fiscal_terms,
        discounting=discounting,
        notes=("Defaults applied: " + "; ".join(defaults)) if defaults else "",
    )

"""
DCF model — the core of the economics engine.

Assembles one full discounted cash flow table from the input book,
calculates all line items year by year, and returns the complete
CashFlowPeriod list plus a ValuationSummary.
"""

from __future__ import annotations

from dataclasses import replace

from engine.core.logging import get_logger
from engine.economics.capex_model import build_capex_schedule, get_depreciable_base
from engine.economics.models import (
    CashFlowPeriod,
    EconomicsInputBook,
    ValuationSummary,
)
from engine.economics.npv_irr_calculator import (
    calculate_discount_factors,
    calculate_irr,
    calculate_multiple_on_invested_capital,
    calculate_npv,
)
from engine.economics.opex_model import calculate_aisc, calculate_period_opex
from engine.economics.payback_calculator import (
    calculate_discounted_payback,
    calculate_simple_payback,
)
from engine.economics.production_schedule_builder import build_production_schedule
from engine.economics.revenue_model import calculate_period_revenue

log = get_logger(__name__)


def run_dcf(inputs: EconomicsInputBook) -> tuple[list[CashFlowPeriod], ValuationSummary]:
    """
    Run a full DCF model from an EconomicsInputBook.

    Returns:
        cash_flows    — one CashFlowPeriod per year
        summary       — NPV, IRR, payback, AISC and other headline metrics
    """
    log.info(
        "Running DCF | project=%s scenario=%s discount_rate=%.1f%%",
        inputs.project_id,
        inputs.scenario,
        inputs.discounting.discount_rate_percent,
    )

    # 1. Build production schedule (populates contained_metal_produced)
    schedule = build_production_schedule(inputs.production_schedule)

    # 2. Build CAPEX schedule indexed by year
    capex_schedule = build_capex_schedule(inputs.capex_items)

    # 3. Depreciation — straight-line on depreciable base over stated years
    depreciable_base = get_depreciable_base(inputs.capex_items)
    dep_years = inputs.fiscal_terms.depreciation_years
    annual_depreciation = depreciable_base / dep_years if dep_years > 0 else 0.0

    # 4. Find all years in the model
    production_years = {p.year for p in schedule}
    capex_years = set(capex_schedule.keys())
    all_years = sorted(production_years | capex_years)
    production_start = min(production_years) if production_years else 1

    # 5. Build period map for quick lookup
    period_map = {p.year: p for p in schedule}

    # 6. Carry-forward loss tracking
    cumulative_loss = 0.0

    # 7. Year-by-year calculation
    cash_flows: list[CashFlowPeriod] = []
    cumulative_undiscounted = 0.0

    discount_factors = calculate_discount_factors(
        n_periods=max(all_years) + 2,
        discount_rate_percent=inputs.discounting.discount_rate_percent,
        convention=inputs.discounting.discounting_convention,
    )

    for year in all_years:
        period = period_map.get(year)
        capex_row = capex_schedule.get(year, {})

        # Production metrics
        ore_tonnes = period.ore_tonnes if period else 0.0
        metal_produced = period.contained_metal_produced if period else 0.0
        metal_unit = period.metal_unit if period else ""

        # Revenue
        gross_rev, royalties_paid, net_rev = (
            calculate_period_revenue(period, inputs.commodity_prices, inputs.fiscal_terms.royalties)
            if period else (0.0, 0.0, 0.0)
        )

        # Operating costs
        years_operating = max(0, year - production_start)
        mining_c, process_c, ganda_c, total_opex = (
            calculate_period_opex(period, inputs.opex_assumptions, years_operating)
            if period else (0.0, 0.0, 0.0, 0.0)
        )

        # EBITDA
        ebitda = net_rev - total_opex

        # CAPEX
        initial_capex  = capex_row.get("initial", 0.0)
        sustaining_cap = capex_row.get("sustaining", 0.0)
        closure_cap    = capex_row.get("closure", 0.0)
        total_capex    = capex_row.get("total", 0.0)

        # Pre-tax FCF
        pre_tax_fcf = ebitda - total_capex

        # Depreciation (only in production years, limited to dep_years)
        dep = annual_depreciation if (
            production_start <= year < production_start + dep_years
        ) else 0.0

        # Taxable income
        ebit = ebitda - dep
        if inputs.fiscal_terms.loss_carry_forward:
            ebit -= cumulative_loss

        taxable_income = max(0.0, ebit)
        income_tax = taxable_income * (inputs.fiscal_terms.corporate_tax_rate_percent / 100.0)

        # Update loss carry-forward
        if ebit < 0 and inputs.fiscal_terms.loss_carry_forward:
            cumulative_loss += abs(ebit)
        elif ebit > 0 and inputs.fiscal_terms.loss_carry_forward:
            cumulative_loss = max(0.0, cumulative_loss - ebit)

        # After-tax FCF
        after_tax_fcf = pre_tax_fcf - income_tax

        # Discounting
        df = discount_factors[year] if year < len(discount_factors) else 0.0
        pv_cf = after_tax_fcf * df

        cumulative_undiscounted += after_tax_fcf

        cash_flows.append(CashFlowPeriod(
            year=year,
            ore_tonnes=ore_tonnes,
            metal_produced=metal_produced,
            metal_unit=metal_unit,
            gross_revenue=round(gross_rev, 4),
            royalties_paid=round(royalties_paid, 4),
            net_revenue=round(net_rev, 4),
            mining_cost=round(mining_c, 4),
            processing_cost=round(process_c, 4),
            ganda_cost=round(ganda_c, 4),
            total_opex=round(total_opex, 4),
            ebitda=round(ebitda, 4),
            capex=round(initial_capex, 4),
            sustaining_capex=round(sustaining_cap, 4),
            closure_capex=round(closure_cap, 4),
            pre_tax_fcf=round(pre_tax_fcf, 4),
            depreciation=round(dep, 4),
            ebit=round(ebit, 4),
            income_tax=round(income_tax, 4),
            after_tax_fcf=round(after_tax_fcf, 4),
            discount_factor=round(df, 6),
            pv_cash_flow=round(pv_cf, 4),
            cumulative_undiscounted_cf=round(cumulative_undiscounted, 4),
        ))

    # 8. Cumulative PV
    cumulative_pv = 0.0
    for cf in cash_flows:
        cumulative_pv += cf.pv_cash_flow
        object.__setattr__(cf, "cumulative_pv_cf", round(cumulative_pv, 4))

    # 9. Summary metrics
    after_tax_cfs = [cf.after_tax_fcf for cf in cash_flows]
    npv = calculate_npv(
        after_tax_cfs,
        inputs.discounting.discount_rate_percent,
        inputs.discounting.discounting_convention,
    )
    irr = calculate_irr(after_tax_cfs)
    payback = calculate_simple_payback(after_tax_cfs, production_start_year=production_start)

    production_periods = [cf for cf in cash_flows if cf.ore_tonnes > 0]
    avg_revenue = (
        sum(cf.gross_revenue for cf in production_periods) / len(production_periods)
        if production_periods else 0.0
    )
    avg_opex = (
        sum(cf.total_opex for cf in production_periods) / len(production_periods)
        if production_periods else 0.0
    )

    total_metal = sum(cf.metal_produced for cf in production_periods)
    total_sustaining = sum(cf.sustaining_capex for cf in production_periods)
    avg_aisc = calculate_aisc(
        total_opex_musd=sum(cf.total_opex for cf in production_periods),
        sustaining_capex_musd=total_sustaining,
        metal_produced=total_metal,
    )
    metal_unit_out = production_periods[0].metal_unit if production_periods else ""

    capex_totals = {
        cat: sum(i.amount for i in inputs.capex_items if i.category.lower() == cat)
        for cat in ("initial", "sustaining", "closure")
    }

    summary = ValuationSummary(
        project_id=inputs.project_id,
        scenario=inputs.scenario,
        discount_rate_percent=inputs.discounting.discount_rate_percent,
        npv_musd=round(npv, 2),
        irr_percent=round(irr, 2) if irr is not None else None,
        payback_years=payback,
        peak_capex_musd=round(max((row.get("total", 0) for row in capex_schedule.values()), default=0.0), 2),
        total_initial_capex_musd=round(capex_totals.get("initial", 0.0), 2),
        total_sustaining_capex_musd=round(capex_totals.get("sustaining", 0.0), 2),
        total_closure_capex_musd=round(capex_totals.get("closure", 0.0), 2),
        average_annual_revenue_musd=round(avg_revenue, 2),
        average_annual_opex_musd=round(avg_opex, 2),
        average_aisc=round(avg_aisc, 2) if avg_aisc else None,
        aisc_unit=f"USD/{metal_unit_out}",
        mine_life_years=len(production_periods),
        after_tax=True,
    )

    log.info(
        "DCF complete | NPV=%.1f MUSD IRR=%.1f%% Payback=%.1f yrs",
        summary.npv_musd,
        summary.irr_percent or 0.0,
        summary.payback_years or 0.0,
    )

    return cash_flows, summary

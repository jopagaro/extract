"""
Shared data models for the economics engine.

All inputs and outputs are typed dataclasses so every number
is traceable and serialisable without extra work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

@dataclass
class CommodityPrice:
    """A single commodity price assumption."""
    commodity: str          # e.g. "gold", "copper", "silver"
    price: float            # price per unit
    unit: str               # e.g. "USD/oz", "USD/lb", "USD/t"
    scenario: str = "base_case"


@dataclass
class RoyaltyTerm:
    """A royalty obligation against project revenue or profit."""
    name: str
    rate_percent: float
    basis: str              # "nsr", "gross_revenue", "net_profit"
    payable_to: str = ""


@dataclass
class ProductionPeriod:
    """One year of the production schedule."""
    year: int               # 0 = construction, 1 = first year of production
    ore_tonnes: float       # tonnes of ore mined/processed
    head_grade: float       # primary commodity grade (units match grade_unit)
    grade_unit: str         # e.g. "g/t", "%", "ppm"
    recovery_percent: float # metallurgical recovery
    commodity: str          # primary payable commodity
    metal_unit: str         # unit of contained metal e.g. "oz", "t", "lb"
    # Derived — filled by production_schedule_builder
    contained_metal_produced: float = 0.0
    # Secondary commodities
    secondary_production: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class CapexItem:
    """A single capital cost line item."""
    name: str
    year: int               # year in which the spend occurs (0 = construction year)
    amount: float           # in model currency (USD millions unless stated)
    category: str           # "initial", "sustaining", "closure", "expansion"
    notes: str = ""


@dataclass
class OpexAssumptions:
    """Operating cost assumptions applied to each production period."""
    mining_cost_per_tonne_ore: float    # USD/t ore
    processing_cost_per_tonne_ore: float
    ganda_cost_per_tonne_ore: float     # G&A
    cost_currency: str = "USD"
    escalation_rate_percent: float = 0.0  # annual cost escalation
    # Optional: per-unit costs (used when opex is stated per metal unit)
    cost_per_metal_unit: float | None = None
    cost_per_metal_unit_basis: str = ""  # e.g. "USD/oz"


@dataclass
class FiscalTerms:
    """Tax and fiscal regime for the project."""
    corporate_tax_rate_percent: float
    royalties: list[RoyaltyTerm] = field(default_factory=list)
    depreciation_method: str = "straight_line"  # or "units_of_production"
    depreciation_years: int = 10
    loss_carry_forward: bool = True
    jurisdiction: str = ""


@dataclass
class DiscountingAssumptions:
    """Discounting parameters for NPV calculation."""
    discount_rate_percent: float        # WACC or required rate of return
    base_year: int = 0                  # year from which discounting begins
    discounting_convention: str = "mid_year"  # "mid_year" or "end_of_year"


@dataclass
class EconomicsInputBook:
    """
    The complete set of inputs required to run the DCF model.
    Built from normalized/ layer data before each model run.
    """
    project_id: str
    scenario: str
    production_schedule: list[ProductionPeriod]
    capex_items: list[CapexItem]
    opex_assumptions: OpexAssumptions
    commodity_prices: list[CommodityPrice]
    fiscal_terms: FiscalTerms
    discounting: DiscountingAssumptions
    working_capital_months: float = 2.0
    initial_capex_currency_musd: float = 0.0  # cross-check value
    notes: str = ""


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

@dataclass
class CashFlowPeriod:
    """One row of the DCF table."""
    year: int

    # Production
    ore_tonnes: float = 0.0
    metal_produced: float = 0.0
    metal_unit: str = ""

    # Revenue
    gross_revenue: float = 0.0
    royalties_paid: float = 0.0
    net_revenue: float = 0.0

    # Operating costs
    mining_cost: float = 0.0
    processing_cost: float = 0.0
    ganda_cost: float = 0.0
    total_opex: float = 0.0

    # EBITDA
    ebitda: float = 0.0

    # Capital
    capex: float = 0.0
    sustaining_capex: float = 0.0
    closure_capex: float = 0.0

    # Pre-tax free cash flow
    pre_tax_fcf: float = 0.0

    # Tax
    depreciation: float = 0.0
    ebit: float = 0.0
    income_tax: float = 0.0

    # After-tax free cash flow
    after_tax_fcf: float = 0.0

    # Discounted
    discount_factor: float = 1.0
    pv_cash_flow: float = 0.0
    cumulative_undiscounted_cf: float = 0.0
    cumulative_pv_cf: float = 0.0


@dataclass
class ValuationSummary:
    """NPV, IRR, and payback results for one scenario."""
    project_id: str
    scenario: str
    discount_rate_percent: float
    npv_musd: float
    irr_percent: float | None       # None if IRR could not be solved
    payback_years: float | None     # None if project never pays back
    peak_capex_musd: float
    total_initial_capex_musd: float
    total_sustaining_capex_musd: float
    total_closure_capex_musd: float
    average_annual_revenue_musd: float
    average_annual_opex_musd: float
    average_aisc: float | None      # all-in sustaining cost per metal unit
    aisc_unit: str = ""
    mine_life_years: int = 0
    after_tax: bool = True
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "scenario": self.scenario,
            "discount_rate_percent": self.discount_rate_percent,
            "npv_musd": round(self.npv_musd, 2),
            "irr_percent": round(self.irr_percent, 2) if self.irr_percent else None,
            "payback_years": round(self.payback_years, 2) if self.payback_years else None,
            "peak_capex_musd": round(self.peak_capex_musd, 2),
            "total_initial_capex_musd": round(self.total_initial_capex_musd, 2),
            "total_sustaining_capex_musd": round(self.total_sustaining_capex_musd, 2),
            "total_closure_capex_musd": round(self.total_closure_capex_musd, 2),
            "average_annual_revenue_musd": round(self.average_annual_revenue_musd, 2),
            "average_annual_opex_musd": round(self.average_annual_opex_musd, 2),
            "average_aisc": round(self.average_aisc, 2) if self.average_aisc else None,
            "aisc_unit": self.aisc_unit,
            "mine_life_years": self.mine_life_years,
            "after_tax": self.after_tax,
            "notes": self.notes,
        }


@dataclass
class SensitivityPoint:
    """One data point in a sensitivity analysis."""
    axis: str               # e.g. "commodity_price", "capex", "opex", "recovery"
    change_percent: float   # e.g. -20.0, -10.0, 0.0, +10.0, +20.0
    npv_musd: float
    irr_percent: float | None
    payback_years: float | None


@dataclass
class SensitivityResult:
    """Full sensitivity analysis output for one scenario."""
    project_id: str
    scenario: str
    base_npv_musd: float
    base_irr_percent: float | None
    points: list[SensitivityPoint] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "scenario": self.scenario,
            "base_npv_musd": round(self.base_npv_musd, 2),
            "base_irr_percent": round(self.base_irr_percent, 2) if self.base_irr_percent else None,
            "points": [
                {
                    "axis": p.axis,
                    "change_percent": p.change_percent,
                    "npv_musd": round(p.npv_musd, 2),
                    "irr_percent": round(p.irr_percent, 2) if p.irr_percent else None,
                    "payback_years": round(p.payback_years, 2) if p.payback_years else None,
                }
                for p in self.points
            ],
        }

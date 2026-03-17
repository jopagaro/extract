"""
Economic risk assessor.

Evaluates the economic inputs and outputs for risk factors and produces
a list of data assessment dicts compatible with data_assessments.json.

This is the economics equivalent of geological_risk_assessor — it
systematically checks every economic assumption and model output for
weaknesses, missing data, and exposure to commodity price movements.

Feeds into: the critic's review, the risk section of the report, and
the sensitivity analysis framing.
"""

from __future__ import annotations

from engine.core.enums import DataStatus, EconomicDirection
from engine.core.logging import get_logger
from engine.economics.models import (
    EconomicsInputBook,
    ValuationSummary,
)

log = get_logger(__name__)

# Thresholds for flagging specific risk conditions
_HIGH_DEBT_CAPEX_RATIO = 0.6          # >60% debt finance = high leverage risk
_LOW_IRR_THRESHOLD = 10.0             # IRR < 10% is weak for mining
_NEGATIVE_NPV_THRESHOLD = 0.0         # NPV < 0 at base case = uneconomic
_HIGH_PAYBACK_YEARS = 8.0             # >8 years payback = financing risk
_HIGH_OPEX_MARGIN_RATIO = 0.75        # opex > 75% of revenue = thin margin
_HIGH_TAX_RATE = 35.0                 # tax rate > 35% is noteworthy
_HIGH_ROYALTY_RATE = 5.0              # royalty > 5% is material


def assess_economics(
    inputs: EconomicsInputBook,
    summary: ValuationSummary | None = None,
) -> list[dict]:
    """
    Run all economic risk assessments.

    inputs: the full EconomicsInputBook used to run the DCF
    summary: the ValuationSummary output (if the DCF has already been run)

    Returns a list of data assessment dicts for data_assessments.json.
    """
    assessments: list[dict] = []

    # --- Commodity price assumptions ---
    _assess_commodity_prices(inputs, assessments)

    # --- CAPEX ---
    _assess_capex(inputs, assessments)

    # --- OPEX ---
    _assess_opex(inputs, assessments)

    # --- Fiscal terms ---
    _assess_fiscal_terms(inputs, assessments)

    # --- Valuation outputs (only if summary is available) ---
    if summary is not None:
        _assess_valuation_outputs(summary, inputs, assessments)

    log.info("Economic risk assessment complete | %d assessments generated", len(assessments))
    return assessments


# ---------------------------------------------------------------------------
# Individual assessment functions
# ---------------------------------------------------------------------------

def _assess_commodity_prices(inputs: EconomicsInputBook, assessments: list[dict]) -> None:
    if not inputs.commodity_prices:
        assessments.append({
            "field": "economics.commodity_prices",
            "status": DataStatus.MISSING.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                "No commodity price assumptions have been provided. "
                "Revenue cannot be calculated without a price deck. "
                "All revenue-dependent outputs (NPV, IRR, payback) are zero or undefined. "
                "A base-case price deck must be established before any economic conclusions "
                "can be drawn."
            ),
            "impacts": ["revenue", "npv", "irr", "payback"],
            "recommended_action": "Provide a commodity price deck (base, bull, bear scenarios).",
        })
        return

    for cp in inputs.commodity_prices:
        if cp.price <= 0:
            assessments.append({
                "field": f"economics.commodity_prices.{cp.commodity}",
                "status": DataStatus.CONFLICTING.value,
                "economic_direction": EconomicDirection.NEGATIVE.value,
                "assessment": (
                    f"The price for {cp.commodity} is {cp.price} {cp.unit}, which is zero or negative. "
                    f"This will produce zero or negative revenue from this commodity. "
                    f"Verify the price assumption before relying on economic outputs."
                ),
                "impacts": ["revenue", "npv"],
                "recommended_action": f"Confirm and correct the {cp.commodity} price assumption.",
            })
        else:
            assessments.append({
                "field": f"economics.commodity_prices.{cp.commodity}",
                "status": DataStatus.PRESENT.value,
                "economic_direction": EconomicDirection.NEUTRAL.value,
                "assessment": (
                    f"{cp.commodity.capitalize()} price assumed at {cp.price:,.0f} {cp.unit} "
                    f"(scenario: {cp.scenario}). All NPV and IRR results are sensitive to this "
                    f"assumption. Refer to the sensitivity analysis for price impact ranges."
                ),
                "impacts": ["revenue", "npv", "irr"],
            })


def _assess_capex(inputs: EconomicsInputBook, assessments: list[dict]) -> None:
    if not inputs.capex_items:
        assessments.append({
            "field": "economics.capex",
            "status": DataStatus.MISSING.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                "No capital cost items have been provided. "
                "CAPEX is the primary determinant of project value — "
                "without it, NPV and IRR cannot be calculated. "
                "At minimum, an order-of-magnitude initial CAPEX estimate is required."
            ),
            "impacts": ["npv", "irr", "payback", "peak_funding"],
            "recommended_action": "Provide initial, sustaining, and closure CAPEX estimates.",
        })
        return

    initial = sum(i.amount for i in inputs.capex_items if i.category.lower() == "initial")
    sustaining = sum(i.amount for i in inputs.capex_items if i.category.lower() == "sustaining")
    closure = sum(i.amount for i in inputs.capex_items if i.category.lower() == "closure")

    if initial <= 0:
        assessments.append({
            "field": "economics.capex.initial",
            "status": DataStatus.MISSING.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                "No initial (construction-phase) capital expenditure has been provided. "
                "This is the single largest cash outflow and is required to calculate "
                "payback period, peak funding requirement, and project economics."
            ),
            "impacts": ["npv", "irr", "payback"],
            "recommended_action": "Provide initial CAPEX estimate.",
        })
    else:
        assessments.append({
            "field": "economics.capex.initial",
            "status": DataStatus.PRESENT.value,
            "economic_direction": EconomicDirection.NEUTRAL.value,
            "assessment": (
                f"Initial CAPEX of {initial:.1f} MUSD has been provided across "
                f"{sum(1 for i in inputs.capex_items if i.category.lower() == 'initial')} line item(s). "
                f"Sustaining CAPEX: {sustaining:.1f} MUSD. Closure provision: {closure:.1f} MUSD. "
                f"The study level of these estimates determines their reliability — "
                f"order-of-magnitude (scoping) estimates carry ±30–50% accuracy."
            ),
            "impacts": ["npv", "irr", "payback"],
        })

    if closure <= 0:
        assessments.append({
            "field": "economics.capex.closure",
            "status": DataStatus.MISSING.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                "No closure cost provision has been included in the CAPEX schedule. "
                "Closure and rehabilitation costs are a real liability for mining projects — "
                "omitting them overstates project NPV and may not comply with reporting standards. "
                "Even at scoping level, a placeholder closure provision should be included."
            ),
            "impacts": ["npv", "closure_liability"],
            "recommended_action": "Add a closure cost provision — typically 1–5% of initial CAPEX for simple operations.",
        })


def _assess_opex(inputs: EconomicsInputBook, assessments: list[dict]) -> None:
    opex = inputs.opex_assumptions
    total_unit_opex = (
        opex.mining_cost_per_tonne_ore
        + opex.processing_cost_per_tonne_ore
        + opex.ganda_cost_per_tonne_ore
    )

    if total_unit_opex <= 0:
        assessments.append({
            "field": "economics.opex",
            "status": DataStatus.MISSING.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                "Operating cost assumptions are zero or have not been provided. "
                "Operating costs are the primary ongoing cash outflow. "
                "Without them, free cash flow and AISC are meaningless."
            ),
            "impacts": ["free_cash_flow", "aisc", "npv"],
            "recommended_action": "Provide mining, processing, and G&A unit cost assumptions.",
        })
    else:
        assessments.append({
            "field": "economics.opex",
            "status": DataStatus.PRESENT.value,
            "economic_direction": EconomicDirection.NEUTRAL.value,
            "assessment": (
                f"Unit operating costs: mining {opex.mining_cost_per_tonne_ore:.2f}, "
                f"processing {opex.processing_cost_per_tonne_ore:.2f}, "
                f"G&A {opex.ganda_cost_per_tonne_ore:.2f} "
                f"(total {total_unit_opex:.2f} {opex.cost_currency}/t ore). "
                + (
                    f"A cost escalation rate of {opex.escalation_rate_percent:.1f}% per annum is applied. "
                    if opex.escalation_rate_percent > 0 else
                    "No cost escalation has been applied — real (constant dollar) basis assumed. "
                )
            ),
            "impacts": ["aisc", "free_cash_flow"],
        })


def _assess_fiscal_terms(inputs: EconomicsInputBook, assessments: list[dict]) -> None:
    fiscal = inputs.fiscal_terms

    if fiscal.corporate_tax_rate_percent <= 0:
        assessments.append({
            "field": "economics.fiscal_terms.tax_rate",
            "status": DataStatus.MISSING.value,
            "economic_direction": EconomicDirection.MIXED.value,
            "assessment": (
                "Corporate tax rate is zero. This may be correct for a tax-loss project "
                "or a jurisdiction with specific exemptions, but it could also indicate "
                "that the fiscal regime has not been set. Confirm the applicable tax rate "
                "before presenting after-tax economic outputs."
            ),
            "impacts": ["after_tax_npv", "after_tax_irr"],
            "recommended_action": "Confirm jurisdiction and applicable corporate tax rate.",
        })
    elif fiscal.corporate_tax_rate_percent > _HIGH_TAX_RATE:
        assessments.append({
            "field": "economics.fiscal_terms.tax_rate",
            "status": DataStatus.PRESENT.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                f"Corporate tax rate of {fiscal.corporate_tax_rate_percent:.1f}% is above "
                f"the {_HIGH_TAX_RATE:.0f}% threshold commonly used to flag high-tax jurisdictions. "
                f"High tax rates materially reduce after-tax NPV and IRR. "
                f"Confirm that this rate reflects the applicable regime including any "
                f"stability agreements, deductions, or ring-fencing provisions."
            ),
            "impacts": ["after_tax_npv", "after_tax_irr"],
        })

    for royalty in fiscal.royalties:
        if royalty.rate_percent > _HIGH_ROYALTY_RATE:
            assessments.append({
                "field": f"economics.fiscal_terms.royalties.{royalty.name}",
                "status": DataStatus.PRESENT.value,
                "economic_direction": EconomicDirection.NEGATIVE.value,
                "assessment": (
                    f"Royalty '{royalty.name}' of {royalty.rate_percent:.1f}% on {royalty.basis} "
                    f"is above the {_HIGH_ROYALTY_RATE:.0f}% flag threshold. "
                    f"High royalties directly reduce net revenue and can meaningfully impact "
                    f"project economics, particularly at low commodity prices."
                ),
                "impacts": ["net_revenue", "npv"],
            })


def _assess_valuation_outputs(
    summary: ValuationSummary,
    inputs: EconomicsInputBook,
    assessments: list[dict],
) -> None:
    # NPV
    if summary.npv_musd < _NEGATIVE_NPV_THRESHOLD:
        assessments.append({
            "field": "economics.valuation.npv",
            "status": DataStatus.PRESENT.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                f"The base-case NPV is negative ({summary.npv_musd:.1f} MUSD at "
                f"{summary.discount_rate_percent:.1f}% discount rate). "
                f"A negative NPV means the project does not recover its cost of capital "
                f"at the assumed commodity price and cost structure. "
                f"This project is not economic under current assumptions. "
                f"Review commodity price assumptions, CAPEX, OPEX, and grade assumptions "
                f"to identify the primary driver of the negative value."
            ),
            "impacts": ["project_viability", "financing"],
            "recommended_action": (
                "Run sensitivity analysis to identify the minimum commodity price and "
                "cost structure needed for a positive NPV."
            ),
        })
    else:
        assessments.append({
            "field": "economics.valuation.npv",
            "status": DataStatus.PRESENT.value,
            "economic_direction": EconomicDirection.POSITIVE.value,
            "assessment": (
                f"Base-case NPV of {summary.npv_musd:.1f} MUSD at "
                f"{summary.discount_rate_percent:.1f}% discount rate. "
                f"The project returns positive value under current assumptions."
            ),
            "impacts": [],
        })

    # IRR
    if summary.irr_percent is None:
        assessments.append({
            "field": "economics.valuation.irr",
            "status": DataStatus.UNVERIFIABLE.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                "IRR could not be calculated from the current cash flow series. "
                "This can occur when the project never pays back, when cash flows lack "
                "a sign change, or when the discount rate is very high. "
                "An undefined IRR is a significant negative signal for project financing."
            ),
            "impacts": ["financing", "project_viability"],
        })
    elif summary.irr_percent < _LOW_IRR_THRESHOLD:
        assessments.append({
            "field": "economics.valuation.irr",
            "status": DataStatus.PRESENT.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                f"Base-case IRR of {summary.irr_percent:.1f}% is below the "
                f"{_LOW_IRR_THRESHOLD:.0f}% threshold typically required by mining investors. "
                f"This level of return may be insufficient to attract project finance "
                f"or equity investment, particularly given the execution risks of early-stage "
                f"mining projects."
            ),
            "impacts": ["financing", "investment_attractiveness"],
        })

    # Payback
    if summary.payback_years is None:
        assessments.append({
            "field": "economics.valuation.payback",
            "status": DataStatus.UNVERIFIABLE.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                "Payback period cannot be calculated — the project's cumulative cash flow "
                "does not cross zero within the modelled mine life. "
                "This means the project does not recover its initial investment under "
                "current assumptions."
            ),
            "impacts": ["financing"],
        })
    elif summary.payback_years > _HIGH_PAYBACK_YEARS:
        assessments.append({
            "field": "economics.valuation.payback",
            "status": DataStatus.PRESENT.value,
            "economic_direction": EconomicDirection.NEGATIVE.value,
            "assessment": (
                f"Payback period of {summary.payback_years:.1f} years exceeds the "
                f"{_HIGH_PAYBACK_YEARS:.0f}-year threshold. Extended payback periods increase "
                f"exposure to commodity price cycles, political risk, and operating cost "
                f"escalation. Project lenders typically prefer payback within mine life / 2."
            ),
            "impacts": ["financing_risk", "political_risk_exposure"],
        })

    # Margin check
    if summary.average_annual_revenue_musd > 0:
        opex_margin = summary.average_annual_opex_musd / summary.average_annual_revenue_musd
        if opex_margin > _HIGH_OPEX_MARGIN_RATIO:
            assessments.append({
                "field": "economics.valuation.opex_margin",
                "status": DataStatus.PRESENT.value,
                "economic_direction": EconomicDirection.NEGATIVE.value,
                "assessment": (
                    f"Operating costs represent {opex_margin*100:.0f}% of average annual revenue, "
                    f"leaving a thin operating margin. Projects with high opex/revenue ratios are "
                    f"highly sensitive to commodity price declines — a small price fall can turn "
                    f"the project cash-flow negative. This increases financial fragility and "
                    f"makes the project difficult to finance."
                ),
                "impacts": ["cash_flow_sensitivity", "financing_risk"],
            })

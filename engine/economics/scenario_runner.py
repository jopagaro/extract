"""
Scenario runner.

Runs the full DCF model under multiple price deck scenarios
(base, bull, bear, lender, stress) and returns all results for comparison.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from engine.core.logging import get_logger
from engine.economics.dcf_model import run_dcf
from engine.economics.models import (
    CashFlowPeriod,
    CommodityPrice,
    EconomicsInputBook,
    ValuationSummary,
)

log = get_logger(__name__)


def run_scenarios(
    base_inputs: EconomicsInputBook,
    scenarios: dict[str, list[CommodityPrice]],
) -> dict[str, tuple[list[CashFlowPeriod], ValuationSummary]]:
    """
    Run the DCF model for each scenario price deck.

    scenarios: dict mapping scenario name → list of CommodityPrice overrides
    Returns: dict mapping scenario name → (cash_flows, summary)

    Example:
        scenarios = {
            "base_case": [CommodityPrice("gold", 1900, "USD/oz")],
            "bull_case": [CommodityPrice("gold", 2400, "USD/oz")],
            "bear_case": [CommodityPrice("gold", 1500, "USD/oz")],
        }
    """
    results: dict[str, tuple[list[CashFlowPeriod], ValuationSummary]] = {}

    for scenario_name, price_deck in scenarios.items():
        log.info("Running scenario: %s", scenario_name)
        scenario_inputs = deepcopy(base_inputs)
        scenario_inputs.scenario = scenario_name
        scenario_inputs.commodity_prices = price_deck
        cash_flows, summary = run_dcf(scenario_inputs)
        results[scenario_name] = (cash_flows, summary)

    return results


def compare_scenarios(
    results: dict[str, tuple[list[CashFlowPeriod], ValuationSummary]],
) -> list[dict]:
    """
    Produce a comparison table of headline metrics across all scenarios.
    """
    rows = []
    for scenario_name, (_, summary) in results.items():
        rows.append({
            "scenario": scenario_name,
            "npv_musd": summary.npv_musd,
            "irr_percent": summary.irr_percent,
            "payback_years": summary.payback_years,
            "avg_aisc": summary.average_aisc,
        })
    return rows

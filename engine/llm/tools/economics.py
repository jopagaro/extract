"""
Economics tool schemas and executors.

These tools are called BY the LLM during analysis — it queries live prices,
checks fiscal terms, and validates DCF readiness before committing to a model run.

Schema:    OpenAI tool definition (pass to call_openai_with_tools)
Executor:  Python function that runs when the LLM calls the tool

Central dispatch is in executor.py. Import the schemas here for
use in any tool-calling loop.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool schemas (OpenAI format)
# ---------------------------------------------------------------------------

LOOKUP_COMMODITY_PRICE_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "lookup_commodity_price",
        "description": (
            "Fetch the current live spot price for a commodity via market data. "
            "Use this to compare study price assumptions against current market prices, "
            "or when the document does not state a commodity price assumption."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "commodity": {
                    "type": "string",
                    "description": "Commodity name (e.g. gold, copper, silver, nickel, lithium)",
                },
            },
            "required": ["commodity"],
        },
    },
}

GET_FISCAL_TERMS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "get_fiscal_terms",
        "description": (
            "Return tax and royalty parameters for a mining jurisdiction. "
            "Use when the document does not state corporate tax rates or royalty rates, "
            "or to cross-check stated fiscal terms against known regime defaults."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "jurisdiction": {
                    "type": "string",
                    "description": "Country or region (e.g. Canada, Chile, Nevada USA, Mexico, Peru)",
                },
            },
            "required": ["jurisdiction"],
        },
    },
}

CHECK_DCF_READINESS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "check_dcf_readiness",
        "description": (
            "Validate whether the extracted economic data is sufficient to run a meaningful DCF model. "
            "Call this before committing to a DCF run. Returns what is present, what is missing, "
            "and which values would be filled with defaults. Use the result to decide whether "
            "to run the model or flag the data gap in the report instead."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "economic_assumptions": {
                    "type": "object",
                    "description": "The extracted economic assumptions dict (output of record_economic_assumptions)",
                },
                "mine_plan": {
                    "type": "object",
                    "description": "The extracted mine plan dict (output of record_mine_plan_inputs)",
                },
                "project_facts": {
                    "type": "object",
                    "description": "The extracted project facts dict (output of record_project_facts)",
                },
            },
            "required": ["economic_assumptions", "mine_plan", "project_facts"],
        },
    },
}

RUN_SENSITIVITY_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "run_sensitivity_analysis",
        "description": (
            "Run sensitivity analysis on a completed DCF model, varying commodity price, "
            "capex, and opex across ±40% to show how NPV and IRR respond. "
            "Only call this after check_dcf_readiness confirms the model can run."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "economic_assumptions": {
                    "type": "object",
                    "description": "Extracted economic assumptions",
                },
                "mine_plan": {
                    "type": "object",
                    "description": "Extracted mine plan",
                },
                "project_facts": {
                    "type": "object",
                    "description": "Extracted project facts",
                },
                "axes": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["commodity_price", "capex", "opex", "recovery", "grade"],
                    },
                    "description": "Which variables to vary. Defaults to all if omitted.",
                },
            },
            "required": ["economic_assumptions", "mine_plan", "project_facts"],
        },
    },
}

# All economics tools bundled for easy import
ALL_ECONOMICS_TOOLS: list[dict] = [
    LOOKUP_COMMODITY_PRICE_TOOL,
    GET_FISCAL_TERMS_TOOL,
    CHECK_DCF_READINESS_TOOL,
    RUN_SENSITIVITY_TOOL,
]


# ---------------------------------------------------------------------------
# Executors — called by executor.py when the LLM invokes a tool
# ---------------------------------------------------------------------------

def execute_lookup_commodity_price(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch live spot price via yfinance."""
    commodity = args.get("commodity", "gold")
    try:
        from engine.market.live_prices import get_commodity_prices
        result = get_commodity_prices(commodity)
        if result and not result.get("error"):
            return {
                "success": True,
                "commodity": commodity,
                "prices": result,
            }
        return {
            "success": False,
            "commodity": commodity,
            "error": result.get("error", "No price data returned"),
        }
    except Exception as exc:
        log.warning("lookup_commodity_price failed for %s: %s", commodity, exc)
        return {"success": False, "commodity": commodity, "error": str(exc)}


def execute_get_fiscal_terms(args: dict[str, Any]) -> dict[str, Any]:
    """
    Return fiscal parameters for a jurisdiction.

    Reads from configs/economics/fiscal_regimes/ YAML files.
    Falls back to generic defaults if the jurisdiction is not configured.
    """
    jurisdiction = args.get("jurisdiction", "")
    j_key = jurisdiction.lower().strip().replace(" ", "_")

    # Canonical alias map
    _aliases = {
        "usa": "usa", "united_states": "usa", "united_states_of_america": "usa",
        "nevada": "usa", "arizona": "usa",
        "canada": "canada", "british_columbia": "canada", "ontario": "canada",
        "quebec": "canada", "bc": "canada",
        "chile": "chile",
        "mexico": "mexico",
        "peru": "peru",
    }
    j_key = _aliases.get(j_key, j_key)

    regime_path = (
        Path(__file__).parents[4]
        / "configs" / "economics" / "fiscal_regimes" / f"{j_key}.yaml"
    )

    if regime_path.exists():
        try:
            import yaml
            with regime_path.open() as f:
                data = yaml.safe_load(f) or {}
            if data and len(data) > 1:  # not just a stub
                return {"success": True, "jurisdiction": jurisdiction, "fiscal_terms": data}
        except Exception as exc:
            log.warning("Could not read fiscal regime file for %s: %s", j_key, exc)

    # Return sensible generic defaults with a note
    return {
        "success": True,
        "jurisdiction": jurisdiction,
        "note": f"No specific regime configured for '{jurisdiction}'. Generic defaults returned.",
        "fiscal_terms": {
            "corporate_tax_rate_percent": 30.0,
            "mining_royalty_percent": 2.0,
            "royalty_basis": "NSR",
            "depreciation_method": "straight_line",
            "depreciation_years": 10,
            "loss_carry_forward": True,
        },
    }


def execute_check_dcf_readiness(args: dict[str, Any]) -> dict[str, Any]:
    """
    Validate DCF inputs and return a readiness report.

    Tells the LLM exactly what is present, what is missing, and what
    defaults would be applied — so it can make an informed decision
    about whether to proceed with the model run.
    """
    econ = args.get("economic_assumptions", {})
    mine = args.get("mine_plan", {})
    facts = args.get("project_facts", {})

    missing: list[str] = []
    present: list[str] = []
    defaults_that_will_apply: list[str] = []

    # Production schedule
    schedule = (mine.get("production_schedule") or [])
    valid_rows = [r for r in schedule if r.get("ore_tonnes")]
    if valid_rows:
        present.append(f"production_schedule ({len(valid_rows)} periods)")
    else:
        missing.append("production_schedule — no ore tonne data found")

    # CAPEX
    capex = econ.get("capex") or {}
    if capex.get("initial_capex"):
        present.append(f"initial_capex ({capex['initial_capex']} {capex.get('initial_capex_unit','')})")
    else:
        missing.append("initial_capex")

    # OPEX
    opex = econ.get("opex") or {}
    has_opex = any(opex.get(k) for k in ("mining_cost", "processing_cost", "total_cash_cost"))
    if has_opex:
        present.append("opex costs")
    else:
        missing.append("opex (mining_cost, processing_cost, or total_cash_cost)")

    # Commodity price
    econ_block = econ.get("economics") or {}
    prices = econ_block.get("commodity_price_assumptions") or []
    valid_prices = [p for p in prices if p.get("price")]
    if valid_prices:
        present.append(f"commodity_price_assumptions ({len(valid_prices)} price(s))")
    else:
        missing.append("commodity_price_assumptions — no price stated in document")

    # Discount rate
    if econ_block.get("discount_rate_percent"):
        present.append(f"discount_rate ({econ_block['discount_rate_percent']}%)")
    else:
        defaults_that_will_apply.append("discount_rate = 8.0% (industry default)")

    # Tax rate
    taxes = econ.get("taxes") or {}
    if taxes.get("corporate_tax_rate_percent"):
        present.append(f"corporate_tax_rate ({taxes['corporate_tax_rate_percent']}%)")
    else:
        defaults_that_will_apply.append("corporate_tax_rate = 30.0% (generic default — consider calling get_fiscal_terms)")

    # Metallurgical recovery
    grade_rows = [r for r in valid_rows if r.get("ore_grade_primary")]
    if not any(r.get("contained_metal") for r in valid_rows) and grade_rows:
        defaults_that_will_apply.append("metallurgical_recovery = 90% (default)")

    # Verdict
    can_run = len(missing) == 0

    return {
        "can_run_dcf": can_run,
        "present": present,
        "missing": missing,
        "defaults_that_will_apply": defaults_that_will_apply,
        "recommendation": (
            "DCF model can run. Defaults noted above will be applied and flagged in the report."
            if can_run else
            f"DCF model cannot run — missing: {', '.join(missing)}. "
            "Flag these gaps explicitly in the report rather than running an incomplete model."
        ),
    }


def execute_run_sensitivity(args: dict[str, Any]) -> dict[str, Any]:
    """Run sensitivity analysis via the existing sensitivity_runner."""
    econ = args.get("economic_assumptions", {})
    mine = args.get("mine_plan", {})
    facts = args.get("project_facts", {})
    axes = args.get("axes") or ["commodity_price", "capex", "opex", "recovery", "grade"]

    try:
        import dataclasses
        from engine.economics.input_builder import build_input_book_from_llm
        from engine.economics.sensitivity_runner import run_sensitivity

        input_book = build_input_book_from_llm(
            project_id="tool_call",
            economic_assumptions=econ,
            mine_plan=mine,
            project_facts=facts,
        )
        if not input_book:
            return {
                "success": False,
                "error": "Insufficient data to build economics model. Run check_dcf_readiness first.",
            }

        sensitivity = run_sensitivity(input_book, axes=axes)
        return {"success": True, "sensitivity": sensitivity.to_dict()}

    except Exception as exc:
        log.error("run_sensitivity_analysis failed: %s", exc)
        return {"success": False, "error": str(exc)}

"""
Central tool dispatcher.

When the LLM returns a tool_calls response, this module executes the
requested function and returns the result. Keeps tool routing logic
in one place so adding new tools only requires registering them here.

Usage:
    result = dispatch_tool(tool_name, tool_args)
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# Maps tool function name → Python executor function
_REGISTRY: dict[str, Any] = {}


def register(name: str):
    """Decorator to register a tool executor by its OpenAI function name."""
    def decorator(fn):
        _REGISTRY[name] = fn
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Economics tool executors (registered on import)
# ---------------------------------------------------------------------------

from engine.llm.tools.economics import (
    execute_lookup_commodity_price,
    execute_get_fiscal_terms,
    execute_check_dcf_readiness,
    execute_run_sensitivity,
)
from engine.llm.tools.cad import (
    execute_analyze_cad_geometry,
    execute_query_cad_feature,
    execute_measure_cad_distance,
)

_REGISTRY["lookup_commodity_price"]   = execute_lookup_commodity_price
_REGISTRY["get_fiscal_terms"]         = execute_get_fiscal_terms
_REGISTRY["check_dcf_readiness"]      = execute_check_dcf_readiness
_REGISTRY["run_sensitivity_analysis"] = execute_run_sensitivity
_REGISTRY["analyze_cad_geometry"]     = execute_analyze_cad_geometry
_REGISTRY["query_cad_feature"]        = execute_query_cad_feature
_REGISTRY["measure_cad_distance"]     = execute_measure_cad_distance


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def dispatch_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a tool by name and return its result as a dict.

    Returns an error dict if the tool is not found or raises an exception.
    The result is sent back to the LLM as a tool_result message.
    """
    executor = _REGISTRY.get(name)
    if executor is None:
        log.warning("Unknown tool requested: %s", name)
        return {"error": f"Tool '{name}' is not registered."}

    try:
        log.info("Executing tool: %s", name)
        return executor(args)
    except Exception as exc:
        log.error("Tool '%s' raised an exception: %s", name, exc)
        return {"error": f"Tool execution failed: {exc}"}


def available_tools() -> list[str]:
    """Return names of all registered tools."""
    return list(_REGISTRY.keys())

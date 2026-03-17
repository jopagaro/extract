"""
Summarize economic model outputs into a report-ready narrative.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def summarize_economics(
    economics_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Generate an economics summary narrative from DCF model outputs.

    Uses the economics analyst role. Returns a structured JSON with prose
    covering NPV, CAPEX, OPEX, production, revenue, and sensitivity — ready
    for the economics section of the technical report.
    """
    return await call_llm(
        role=LLMRole.ECONOMICS_ANALYST,
        task=LLMTask.SUMMARIZATION,
        task_name="summarize_economics",
        data=economics_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

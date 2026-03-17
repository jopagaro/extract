"""
Score the financing risk and bankability of the project.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def score_financing(
    financing_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Assess the financing risk and capital structure of the project.

    Uses the economics analyst role to evaluate CAPEX scale vs. returns,
    cash flow quality for debt service, offtake security, sponsor capacity,
    and jurisdiction risk. Returns a structured assessment per factor.
    """
    return await call_llm(
        role=LLMRole.ECONOMICS_ANALYST,
        task=LLMTask.SCORING,
        task_name="score_financing",
        data=financing_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

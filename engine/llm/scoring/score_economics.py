"""
Score the quality and robustness of the economic analysis.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def score_economics(
    economics_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Assess the quality and robustness of the economic analysis.

    Uses the critic role to evaluate CAPEX/OPEX estimate quality,
    price assumption reasonableness, tax modelling accuracy, and
    sensitivity analysis completeness. Returns a structured assessment
    per factor with economic direction tags and recommended actions.
    """
    return await call_llm(
        role=LLMRole.CRITIC,
        task=LLMTask.SCORING,
        task_name="score_economics",
        data=economics_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

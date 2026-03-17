"""
Score the overall project — synthesizing all domain assessments.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def score_overall(
    all_assessments: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Synthesize all domain scores into an overall project evaluation.

    Input should be a JSON string containing geology, economics, financing,
    and permitting assessments. Returns an overall summary with primary
    strength and risk identified, development readiness comment, and
    a prioritized list of next steps.
    """
    return await call_llm(
        role=LLMRole.CRITIC,
        task=LLMTask.SCORING,
        task_name="score_overall_project",
        data=all_assessments,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

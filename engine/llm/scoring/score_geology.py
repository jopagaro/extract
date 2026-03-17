"""
Score the quality and completeness of the geological data and resource estimate.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def score_geology(
    geology_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Assess the quality of the geological database and resource estimate.

    Uses the geology analyst role to evaluate data density, QA/QC quality,
    estimation methodology, domain model integrity, and qualified person
    credentials. Returns a structured assessment per factor with recommended actions.
    """
    return await call_llm(
        role=LLMRole.GEOLOGY_ANALYST,
        task=LLMTask.SCORING,
        task_name="score_geology",
        data=geology_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

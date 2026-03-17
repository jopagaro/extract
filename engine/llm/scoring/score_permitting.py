"""
Score the permitting and regulatory position of the project.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def score_permitting(
    permitting_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Assess the permitting and social licence status of the project.

    Uses the critic role to evaluate environmental assessment status,
    permit completeness, water rights, land access, indigenous consultation,
    and social licence. Returns a structured assessment per factor with
    critical path permits and recommended actions identified.
    """
    return await call_llm(
        role=LLMRole.CRITIC,
        task=LLMTask.SCORING,
        task_name="score_permitting",
        data=permitting_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

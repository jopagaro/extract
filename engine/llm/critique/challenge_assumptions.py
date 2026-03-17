"""
Challenge the key assumptions embedded in the project study.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def challenge_assumptions(
    project_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Identify and challenge the key assumptions in the project analysis.

    Uses the critic role to find stated and implied assumptions, assess
    whether they are conservative or aggressive, and flag those with
    material downside risk if wrong. Returns a structured list of
    challenged assumptions with direction of risk and materiality.
    """
    return await call_llm(
        role=LLMRole.CRITIC,
        task=LLMTask.CRITIQUE,
        task_name="challenge_assumptions",
        data=project_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

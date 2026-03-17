"""
Identify internal contradictions in the project data and report.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def flag_contradictions(
    project_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Identify contradictions within the project data and generated sections.

    Uses the critic role to compare figures, statements, and conclusions
    across all sections. Flags cases where the same metric is stated differently
    in two places, where a conclusion does not follow from the data, or where
    arithmetic errors exist in tables.
    Returns a structured list of contradictions with severity and economic impact.
    """
    return await call_llm(
        role=LLMRole.CRITIC,
        task=LLMTask.CRITIQUE,
        task_name="identify_contradictions",
        data=project_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

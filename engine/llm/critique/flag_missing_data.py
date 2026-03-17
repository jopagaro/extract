"""
Identify material data gaps in the project dataset.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def flag_missing_data(
    project_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Identify material data gaps across all analytical domains.

    Uses the critic role to assess each domain (geology, mining, metallurgy,
    infrastructure, environment, economics) for absent or incomplete data.
    Returns a structured list of gaps with urgency ratings and recommended actions.
    Distinguishes between gaps that block advancement and those that add uncertainty.
    """
    return await call_llm(
        role=LLMRole.CRITIC,
        task=LLMTask.CRITIQUE,
        task_name="check_missing_data",
        data=project_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

"""
NI 43-101 / JORC Code compliance checker.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def check_compliance(
    project_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Assess whether the project documentation meets NI 43-101 and/or JORC Code
    2012 requirements for mineral resource/reserve reporting.

    Returns a structured JSON with:
    - standard detected and assessed against
    - QP/CP details
    - per-requirement check results (met / partial / missing / not_applicable)
    - overall status and summary
    - critical and minor gap lists
    """
    return await call_llm(
        role=LLMRole.CRITIC,
        task=LLMTask.CRITIQUE,
        task_name="check_ni43101_jorc",
        data=project_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

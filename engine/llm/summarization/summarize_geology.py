"""
Summarize geological data into a report-ready narrative.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def summarize_geology(
    geology_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Generate a geology summary narrative from extracted geological data.

    Uses the geology analyst role for domain-appropriate language and structure.
    Returns a structured JSON with prose subsections ready for report assembly.
    """
    return await call_llm(
        role=LLMRole.GEOLOGY_ANALYST,
        task=LLMTask.SUMMARIZATION,
        task_name="summarize_geology",
        data=geology_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

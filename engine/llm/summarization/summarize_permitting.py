"""
Summarize permitting and regulatory status into a report-ready narrative.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def summarize_permitting(
    permitting_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Generate a permitting summary from extracted regulatory and permit data.

    Returns a structured JSON with prose covering permit status, critical path
    permits, social licence, and key permitting risks.
    """
    return await call_llm(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.SUMMARIZATION,
        task_name="summarize_permitting",
        data=permitting_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

"""
Summarize field notes, site visit transcripts, and qualitative observations.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def summarize_notes(
    notes_text: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Extract and summarize key observations from field notes and site visit records.

    Uses the data extractor role — focused on pulling factual observations
    rather than technical analysis. Returns a prose summary suitable for
    inclusion in the project notes or qualitative data sections.
    """
    return await call_llm(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.SUMMARIZATION,
        task_name="summarize_notes",
        data=notes_text,
        run_id=run_id,
        json_mode=False,
        extra_context=extra_context,
    )

"""
Verify report figures against source document extractions.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def compare_to_sources(
    report_and_sources: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Provenance check: verify report figures against extracted source data.

    Input should be a JSON string containing both the report text/figures
    and the original extracted source data for comparison.
    Uses the critic role to flag any discrepancies between what the report
    states and what the source documents contain.
    Returns a structured list of verified fields, mismatches, and unverifiable claims.
    """
    return await call_llm(
        role=LLMRole.CRITIC,
        task=LLMTask.CRITIQUE,
        task_name="compare_report_to_sources",
        data=report_and_sources,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

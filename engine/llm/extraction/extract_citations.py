"""
Trace report claims back to source documents to build a citation index.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def extract_citations(
    source_documents: str,
    *,
    run_id: str | None = None,
    report_sections: str | None = None,
) -> LLMResponse:
    """
    Build a source citation index for a report.

    Takes the source documents (labeled [Source: filename]) as the primary data
    and the assembled report sections as extra_context.  For each material claim
    in the report, identifies the supporting source file, verbatim quote, and
    location reference.

    Flags claims that cannot be traced to any source document (confidence =
    "not_found") — these may indicate LLM hallucinations and warrant analyst review.
    """
    return await call_llm(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.EXTRACTION,
        task_name="extract_citations",
        data=source_documents,
        run_id=run_id,
        json_mode=True,
        extra_context=report_sections,
    )

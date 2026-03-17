"""
Summarize CAD model semantics into a report-ready mine design narrative.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def summarize_cad(
    cad_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Generate a mine design narrative from extracted CAD semantic data.

    Returns a structured JSON with prose describing the mine layout,
    key design parameters, infrastructure, and design completeness —
    ready for the mine design section of the technical report.
    """
    return await call_llm(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.SUMMARIZATION,
        task_name="summarize_cad_model",
        data=cad_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

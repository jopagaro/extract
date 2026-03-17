"""
Assemble all generated report sections into a complete technical report.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def assemble_report_sections(
    all_sections: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Final assembly pass: check section consistency and produce the report manifest.

    Input should be a JSON string containing all written sections:
    executive summary, methodology, geology, mine design, economics, and risks.
    The model checks for cross-section consistency, flags contradictions,
    and returns a table of contents with a readiness assessment.
    """
    return await call_llm(
        role=LLMRole.REPORT_WRITER,
        task=LLMTask.REPORTING,
        task_name="assemble_full_report",
        data=all_sections,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

"""
Write the executive summary section of the technical report.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def write_executive_summary(
    project_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Generate the executive summary from synthesized project data.

    Input should be a JSON string containing all pre-summarized sections:
    project facts, resource summary, economics summary, and key risks.
    Returns a structured JSON with the executive summary text and a
    key metrics table.
    """
    return await call_llm(
        role=LLMRole.REPORT_WRITER,
        task=LLMTask.REPORTING,
        task_name="write_executive_summary",
        data=project_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

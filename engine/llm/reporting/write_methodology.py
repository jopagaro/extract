"""
Write the methodology and data sources section of the technical report.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def write_methodology(
    methodology_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Generate the methodology section describing how the analysis was conducted.

    Input should be a JSON string containing: source document list,
    extraction method descriptions, economic model parameters, and study level.
    Returns structured JSON with sub-sections covering scope, data sources,
    analysis process, and limitations.
    """
    return await call_llm(
        role=LLMRole.REPORT_WRITER,
        task=LLMTask.REPORTING,
        task_name="write_methodology",
        data=methodology_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

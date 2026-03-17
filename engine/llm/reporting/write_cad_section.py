"""
Write the mine design and infrastructure section of the technical report.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def write_cad_section(
    cad_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Generate the mine design section from summarized CAD model data.

    Input should be the CAD summary JSON produced by summarize_cad.
    Returns structured JSON with sub-sections covering mine type, key design
    parameters, infrastructure, and design completeness comment.
    """
    return await call_llm(
        role=LLMRole.REPORT_WRITER,
        task=LLMTask.REPORTING,
        task_name="write_cad_section",
        data=cad_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

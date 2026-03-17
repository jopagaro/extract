"""
Write the geology section of the technical report.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def write_geology_section(
    geology_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Generate the geology section of the technical report.

    Input should be the geology summary JSON produced by summarize_geology.
    Returns structured JSON with sub-sections (regional setting, local geology,
    mineralisation, drilling, resource estimate) ready for report assembly.
    """
    return await call_llm(
        role=LLMRole.REPORT_WRITER,
        task=LLMTask.REPORTING,
        task_name="write_geology_section",
        data=geology_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

"""
Write the risks and uncertainties section of the technical report.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def write_risk_section(
    risk_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Generate the risks and uncertainties section of the technical report.

    Input should be the risk summary JSON produced by summarize_risks,
    including categorized risks, data gaps, and top risk narrative.
    Returns structured JSON with per-category sub-sections.
    """
    return await call_llm(
        role=LLMRole.REPORT_WRITER,
        task=LLMTask.REPORTING,
        task_name="write_risk_section",
        data=risk_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

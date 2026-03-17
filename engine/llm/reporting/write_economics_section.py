"""
Write the financial analysis section of the technical report.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def write_economics_section(
    economics_data: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Generate the economics section of the technical report.

    Input should be the economics summary JSON produced by summarize_economics,
    including DCF outputs, CAPEX/OPEX breakdowns, sensitivity results, and
    fiscal terms. Returns structured JSON with sub-sections and a key metrics table.
    """
    return await call_llm(
        role=LLMRole.REPORT_WRITER,
        task=LLMTask.REPORTING,
        task_name="write_economics_section",
        data=economics_data,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

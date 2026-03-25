"""
Assess the confidence level of each section of a mining project report.

No numeric scores — plain-language descriptors only.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def assess_confidence(
    combined_report_data: str,
    *,
    run_id: str | None = None,
) -> LLMResponse:
    """
    Evaluate how much confidence should be placed in each section of the report.

    Uses the critic role to assess each analytical domain based on:
    - Number and quality of independent sources
    - Presence of assumptions stated without basis
    - Internal consistency across documents
    - Completeness of data for the conclusions drawn

    Returns plain-language confidence descriptors — no numeric ratings.
    The output is saved as 09_confidence.json and rendered as a dedicated
    report section.
    """
    return await call_llm(
        role=LLMRole.CRITIC,
        task=LLMTask.SCORING,
        task_name="assess_confidence",
        data=combined_report_data,
        run_id=run_id,
        json_mode=True,
    )

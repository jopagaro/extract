"""
Extract mine plan and production schedule inputs from a document using OpenAI tool calling.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.response import LLMResponse
from engine.llm.tools.extractor import extract_with_tool
from engine.llm.tools.schemas import MINE_PLAN_TOOL, TOOL_CHOICE_MINE_PLAN


async def extract_mine_plan_inputs(
    document_text: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Extract mine plan and production schedule parameters.

    Uses OpenAI tool calling to guarantee valid structured output.
    Production schedule feeds into the DCF cash flow model.
    """
    return await extract_with_tool(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.EXTRACTION,
        task_name="extract_mine_plan_inputs",
        data=document_text,
        tool=MINE_PLAN_TOOL,
        tool_choice=TOOL_CHOICE_MINE_PLAN,
        run_id=run_id,
        extra_context=extra_context,
    )

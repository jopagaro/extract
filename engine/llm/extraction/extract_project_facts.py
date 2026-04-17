"""
Extract core project facts from a document using OpenAI tool calling.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.response import LLMResponse
from engine.llm.tools.extractor import extract_with_tool
from engine.llm.tools.schemas import PROJECT_FACTS_TOOL, TOOL_CHOICE_PROJECT_FACTS


async def extract_project_facts(
    document_text: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Extract core project facts from a mining document.

    Uses OpenAI tool calling to guarantee a valid structured response
    matching the project facts schema on every call.
    """
    return await extract_with_tool(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.EXTRACTION,
        task_name="extract_project_facts",
        data=document_text,
        tool=PROJECT_FACTS_TOOL,
        tool_choice=TOOL_CHOICE_PROJECT_FACTS,
        run_id=run_id,
        extra_context=extra_context,
    )

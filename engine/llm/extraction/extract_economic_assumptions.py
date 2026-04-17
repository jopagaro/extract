"""
Extract CAPEX, OPEX, and economic assumptions from a document using OpenAI tool calling.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.response import LLMResponse
from engine.llm.tools.extractor import extract_with_tool
from engine.llm.tools.schemas import ECONOMIC_ASSUMPTIONS_TOOL, TOOL_CHOICE_ECONOMIC_ASSUMPTIONS


async def extract_economic_assumptions(
    document_text: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Extract capital costs, operating costs, and economic assumptions.

    Uses OpenAI tool calling to guarantee valid structured output.
    Economic figures feed directly into the DCF model so schema
    conformance here is critical.
    """
    return await extract_with_tool(
        role=LLMRole.ECONOMICS_ANALYST,
        task=LLMTask.EXTRACTION,
        task_name="extract_financial_terms",
        data=document_text,
        tool=ECONOMIC_ASSUMPTIONS_TOOL,
        tool_choice=TOOL_CHOICE_ECONOMIC_ASSUMPTIONS,
        run_id=run_id,
        extra_context=extra_context,
    )

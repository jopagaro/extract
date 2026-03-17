"""
Extract core project facts from a document using both LLM providers.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.dual_runner import call_llm_dual
from engine.llm.reconciler import DualLLMResponse


async def extract_project_facts(
    document_text: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> DualLLMResponse:
    """
    Extract core project facts from a mining document.

    Runs both Anthropic and OpenAI in parallel and reconciles the output.
    Returns agreed fields merged, disagreements flagged for analyst review.
    """
    return await call_llm_dual(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.EXTRACTION,
        task_name="extract_project_facts",
        data=document_text,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

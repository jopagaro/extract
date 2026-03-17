"""
Extract mine plan and production schedule inputs from a document.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.dual_runner import call_llm_dual
from engine.llm.reconciler import DualLLMResponse


async def extract_mine_plan_inputs(
    document_text: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> DualLLMResponse:
    return await call_llm_dual(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.EXTRACTION,
        task_name="extract_mine_plan_inputs",
        data=document_text,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

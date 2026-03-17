"""
Extract mineral resource and reserve estimates from a document.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.dual_runner import call_llm_dual
from engine.llm.reconciler import DualLLMResponse


async def extract_resource_summary(
    document_text: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> DualLLMResponse:
    """
    Extract resource and reserve estimate tables from a mining document.

    Resource figures are high-stakes — running both models and comparing
    field by field flags any discrepancy for analyst verification.
    """
    return await call_llm_dual(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.EXTRACTION,
        task_name="extract_resource_summary",
        data=document_text,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

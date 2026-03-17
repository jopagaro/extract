"""
Extract CAPEX, OPEX, and economic assumptions from a document.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.dual_runner import call_llm_dual
from engine.llm.reconciler import DualLLMResponse


async def extract_economic_assumptions(
    document_text: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> DualLLMResponse:
    """
    Extract capital costs, operating costs, and economic assumptions.

    Economic figures are the most consequential outputs of a technical study.
    Dual-model reconciliation flags any numeric disagreements before they
    enter the economic model.
    """
    return await call_llm_dual(
        role=LLMRole.ECONOMICS_ANALYST,
        task=LLMTask.EXTRACTION,
        task_name="extract_financial_terms",
        data=document_text,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

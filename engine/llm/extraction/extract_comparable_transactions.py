"""Extract comparable M&A and streaming transactions from source documents."""
from __future__ import annotations
from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def extract_comparable_transactions(
    source_documents: str,
    *,
    run_id: str | None = None,
) -> LLMResponse:
    """
    Extract M&A comps, royalty purchases, and streaming deals referenced
    in uploaded documents. Returns a JSON object with a 'transactions' array.
    """
    return await call_llm(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.EXTRACTION,
        task_name="extract_comparable_transactions",
        data=source_documents,
        run_id=run_id,
        json_mode=True,
    )

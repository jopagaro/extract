"""Extract royalty and streaming agreements from source documents."""
from __future__ import annotations
from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def extract_royalties(
    source_documents: str,
    *,
    run_id: str | None = None,
) -> LLMResponse:
    """
    Extract NSR, gross royalty, NPI, streaming, and other encumbrances
    from uploaded documents. Returns a JSON object with an 'agreements' array.
    """
    return await call_llm(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.EXTRACTION,
        task_name="extract_royalties",
        data=source_documents,
        run_id=run_id,
        json_mode=True,
    )

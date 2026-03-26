"""Extract capital structure, share count, warrants, streaming deals, and financial encumbrances."""
from __future__ import annotations
from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def extract_capital_structure(
    source_documents: str,
    *,
    run_id: str | None = None,
) -> LLMResponse:
    """
    Extract shares outstanding, fully diluted count, warrants, options, royalties,
    streaming agreements, earn-in deals, debt facilities, off-take agreements,
    and major shareholders. Flags all encumbrances on project economics.
    """
    return await call_llm(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.EXTRACTION,
        task_name="extract_capital_structure",
        data=source_documents,
        run_id=run_id,
        json_mode=True,
    )

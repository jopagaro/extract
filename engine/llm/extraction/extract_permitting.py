"""Extract permitting status, environmental approvals, and regulatory timeline from source documents."""
from __future__ import annotations
from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def extract_permitting(
    source_documents: str,
    *,
    run_id: str | None = None,
) -> LLMResponse:
    """
    Extract permit status (approved / applied / required / expired), environmental
    assessment status, water rights, land access agreements, Indigenous consultation
    outcomes, and estimated permitting timeline.
    """
    return await call_llm(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.EXTRACTION,
        task_name="extract_permitting",
        data=source_documents,
        run_id=run_id,
        json_mode=True,
    )

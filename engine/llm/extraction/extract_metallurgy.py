"""Extract metallurgical testwork results and recovery assumptions from source documents."""
from __future__ import annotations
from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def extract_metallurgy(
    source_documents: str,
    *,
    run_id: str | None = None,
) -> LLMResponse:
    """
    Extract process route, recovery rates, testwork type, concentrate specs,
    and metallurgical risks. Recovery rates feed directly into the DCF model.
    """
    return await call_llm(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.EXTRACTION,
        task_name="extract_metallurgy",
        data=source_documents,
        run_id=run_id,
        json_mode=True,
    )

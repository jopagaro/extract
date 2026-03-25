"""Extract mineral resource / reserve table from source documents."""
from __future__ import annotations
from engine.core.enums import LLMRole, LLMTask
from engine.llm.providers.router import call_llm
from engine.llm.response import LLMResponse


async def extract_resource_table(
    source_documents: str,
    *,
    run_id: str | None = None,
) -> LLMResponse:
    """
    Extract Measured / Indicated / Inferred resource rows from uploaded documents.
    Returns a JSON object with a 'rows' array matching the ResourceRow schema.
    """
    return await call_llm(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.EXTRACTION,
        task_name="extract_resource_table",
        data=source_documents,
        run_id=run_id,
        json_mode=True,
    )

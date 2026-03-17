"""
Extract risk factors from a document.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.dual_runner import call_llm_dual
from engine.llm.reconciler import DualLLMResponse


async def extract_risks(
    document_text: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> DualLLMResponse:
    """
    Extract stated and implied risk factors from a mining document.
    Uses the critic role — best at identifying problems and gaps.
    """
    return await call_llm_dual(
        role=LLMRole.CRITIC,
        task=LLMTask.EXTRACTION,
        task_name="extract_project_facts",  # update once extract_risks prompt is written
        data=document_text,
        run_id=run_id,
        json_mode=False,   # prose output — risk narrative, not structured table
        extra_context=extra_context,
    )

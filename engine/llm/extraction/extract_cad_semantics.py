"""
Extract semantic information from CAD model descriptions.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.llm.dual_runner import call_llm_dual
from engine.llm.reconciler import DualLLMResponse


async def extract_cad_semantics(
    cad_description: str,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> DualLLMResponse:
    """
    Extract structured mine design information from a CAD model description.

    Input is a text description of layer names, object types, and geometry
    produced by the CAD parser. Output is a structured JSON object describing
    the mine design elements present.
    """
    return await call_llm_dual(
        role=LLMRole.DATA_EXTRACTOR,
        task=LLMTask.EXTRACTION,
        task_name="extract_cad_semantics",
        data=cad_description,
        run_id=run_id,
        json_mode=True,
        extra_context=extra_context,
    )

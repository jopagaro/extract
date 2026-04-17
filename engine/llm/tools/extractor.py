"""
Tool-based structured extraction.

Replaces the json_mode + dual-runner pattern for extraction tasks.
OpenAI tool calling guarantees valid structured output — no JSON parse
failures, no reconciler needed, no retry logic for malformed responses.

The LLM is forced to call a specific tool (via tool_choice) whose
parameters define exactly what gets extracted. The arguments come back
as a validated dict every time.
"""

from __future__ import annotations

from engine.core.enums import LLMRole, LLMTask
from engine.core.errors import LLMProviderError
from engine.core.logging import get_logger
from engine.llm.prompt_loader import build_messages
from engine.llm.providers.openai_client import call_openai_with_tools
from engine.llm.response import LLMResponse

log = get_logger(__name__)


async def extract_with_tool(
    role: LLMRole,
    task: LLMTask,
    task_name: str,
    data: str,
    tool: dict,
    tool_choice: dict,
    *,
    run_id: str | None = None,
    extra_context: str | None = None,
) -> LLMResponse:
    """
    Run a structured extraction via OpenAI tool calling.

    The tool schema defines the exact output shape. The model is forced
    to call that tool, so response.structured is always a valid dict
    or None (only on a catastrophic API failure, not a format error).

    Parameters
    ----------
    role:       Analyst role — loads the appropriate system prompt.
    task:       Task category for model selection.
    task_name:  Prompt file name (same as before).
    data:       Document text to extract from.
    tool:       OpenAI tool definition dict (from schemas.py).
    tool_choice: Forced tool choice dict (from schemas.py).
    run_id:     Optional run ID for provenance.
    extra_context: Optional prior context appended to user message.
    """
    system_prompt, user_message = build_messages(
        role=role,
        task=task,
        task_name=task_name,
        data=data,
        extra_context=extra_context,
    )

    return await call_openai_with_tools(
        system_prompt=system_prompt,
        user_message=user_message,
        role=role,
        task=task,
        task_name=task_name,
        tools=[tool],
        tool_choice=tool_choice,
        run_id=run_id,
    )

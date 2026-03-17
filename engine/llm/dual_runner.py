"""
Dual LLM runner.

Calls both Anthropic and OpenAI in parallel for the same task,
then passes both responses to the reconciler.

This is the default mode for all extraction, summarization, and critique tasks.
Running both models simultaneously gives us:
  - Independent verification of extracted values
  - Flagged disagreements for analyst review
  - Higher confidence on agreed outputs
  - No added latency (parallel, not sequential)
"""

from __future__ import annotations

import asyncio

from engine.core.config import settings
from engine.core.enums import LLMProvider, LLMRole, LLMTask
from engine.core.errors import LLMProviderError
from engine.core.logging import get_logger
from engine.llm.prompt_loader import build_messages
from engine.llm.reconciler import DualLLMResponse, reconcile
from engine.llm.response import LLMResponse

log = get_logger(__name__)


async def call_llm_dual(
    role: LLMRole,
    task: LLMTask,
    task_name: str,
    data: str,
    *,
    run_id: str | None = None,
    json_mode: bool = True,
    extra_context: str | None = None,
) -> DualLLMResponse:
    """
    Run both Anthropic and OpenAI in parallel on the same task.
    Returns a DualLLMResponse with merged output and flagged disagreements.

    If only one API key is configured, runs that provider alone and
    returns a DualLLMResponse with only one side populated.

    Parameters
    ----------
    role:
        Analyst role (loads system + role prompts).
    task:
        Task category.
    task_name:
        Specific prompt file name.
    data:
        Document text or content to process.
    run_id:
        Optional run ID for provenance.
    json_mode:
        Should be True for extraction tasks so outputs are comparable.
    extra_context:
        Optional prior context (e.g. assessments from last run).
    """
    system_prompt, user_message = build_messages(
        role=role,
        task=task,
        task_name=task_name,
        data=data,
        extra_context=extra_context,
    )

    has_anthropic = settings.has_anthropic
    has_openai = settings.has_openai

    if not has_anthropic and not has_openai:
        raise LLMProviderError(
            "No LLM API keys configured. "
            "Set OPENAI_API_KEY and/or ANTHROPIC_API_KEY in your .env file."
        )

    # Build coroutines for whichever providers are available
    coroutines: list = []
    providers: list[LLMProvider] = []

    if has_anthropic:
        from engine.llm.providers.anthropic_client import call_anthropic
        coroutines.append(
            call_anthropic(
                system_prompt=system_prompt,
                user_message=user_message,
                role=role,
                task=task,
                task_name=task_name,
                run_id=run_id,
                json_mode=json_mode,
            )
        )
        providers.append(LLMProvider.ANTHROPIC)

    if has_openai:
        from engine.llm.providers.openai_client import call_openai
        coroutines.append(
            call_openai(
                system_prompt=system_prompt,
                user_message=user_message,
                role=role,
                task=task,
                task_name=task_name,
                run_id=run_id,
                json_mode=json_mode,
            )
        )
        providers.append(LLMProvider.OPENAI)

    log.info(
        "Dual LLM call | providers=%s role=%s task=%s name=%s",
        [p.value for p in providers],
        role.value, task.value, task_name,
    )

    # Run in parallel
    results = await asyncio.gather(*coroutines, return_exceptions=True)

    anthropic_response: LLMResponse | None = None
    openai_response: LLMResponse | None = None
    errors: list[str] = []

    for provider, result in zip(providers, results):
        if isinstance(result, Exception):
            log.error("Provider %s failed: %s", provider.value, result)
            errors.append(f"{provider.value}: {result}")
        elif provider == LLMProvider.ANTHROPIC:
            anthropic_response = result
        else:
            openai_response = result

    if anthropic_response is None and openai_response is None:
        raise LLMProviderError(
            f"Both providers failed:\n" + "\n".join(errors)
        )

    return reconcile(
        anthropic_response=anthropic_response,
        openai_response=openai_response,
        task=task,
        task_name=task_name,
        run_id=run_id,
    )

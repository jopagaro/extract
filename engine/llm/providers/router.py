"""
LLM router.

Single entry point for all LLM calls in the engine.
Selects the provider based on configs/llm/routing.yaml and key availability,
assembles the prompt, calls the provider, and returns an LLMResponse.

Usage:
    from engine.llm.providers.router import call_llm
    from engine.core.enums import LLMRole, LLMTask

    response = await call_llm(
        role=LLMRole.ECONOMICS_ANALYST,
        task=LLMTask.EXTRACTION,
        task_name="extract_economic_assumptions",
        data="<document text>",
    )

    print(response.content)          # full text output
    print(response.structured)       # parsed JSON (if json_mode=True)
    print(response.total_tokens)     # for cost tracking
"""

from __future__ import annotations

from engine.core.config import get_llm_config, settings
from engine.core.enums import LLMProvider, LLMRole, LLMTask
from engine.core.errors import LLMProviderError
from engine.core.logging import get_logger
from engine.llm.prompt_loader import build_messages
from engine.llm.response import LLMResponse

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Strategy resolution
# ---------------------------------------------------------------------------

def _resolve_provider(task: LLMTask) -> LLMProvider:
    """
    Decide which provider to use for a given task.

    Reads routing.yaml, then checks which API keys are actually available.
    Raises LLMProviderError if neither key is set.
    """
    try:
        routing = get_llm_config("routing")
    except Exception:
        routing = {}

    task_routing: dict = routing.get("task_routing", {})
    strategy: str = task_routing.get(
        task.value,
        routing.get("default_strategy", "prefer_anthropic"),
    )

    has_anthropic = settings.has_anthropic
    has_openai = settings.has_openai

    if strategy == "prefer_anthropic":
        if has_anthropic:
            return LLMProvider.ANTHROPIC
        if has_openai:
            log.info("Anthropic key not set — falling back to OpenAI for task=%s", task.value)
            return LLMProvider.OPENAI
    elif strategy == "prefer_openai":
        if has_openai:
            return LLMProvider.OPENAI
        if has_anthropic:
            log.info("OpenAI key not set — falling back to Anthropic for task=%s", task.value)
            return LLMProvider.ANTHROPIC
    elif strategy == "anthropic_only":
        if has_anthropic:
            return LLMProvider.ANTHROPIC
        raise LLMProviderError(
            "Task requires Anthropic (anthropic_only strategy) but ANTHROPIC_API_KEY is not set."
        )
    elif strategy == "openai_only":
        if has_openai:
            return LLMProvider.OPENAI
        raise LLMProviderError(
            "Task requires OpenAI (openai_only strategy) but OPENAI_API_KEY is not set."
        )

    raise LLMProviderError(
        "No LLM API keys are configured. "
        "Set OPENAI_API_KEY or ANTHROPIC_API_KEY in your .env file."
    )


# ---------------------------------------------------------------------------
# Main router
# ---------------------------------------------------------------------------

async def call_llm(
    role: LLMRole,
    task: LLMTask,
    task_name: str,
    data: str,
    *,
    run_id: str | None = None,
    json_mode: bool = False,
    extra_context: str | None = None,
    force_provider: LLMProvider | None = None,
) -> LLMResponse:
    """
    Make an LLM call through the router.

    Parameters
    ----------
    role:
        Analyst role to use (sets which system prompt loads).
        e.g. LLMRole.ECONOMICS_ANALYST
    task:
        Task category.
        e.g. LLMTask.EXTRACTION
    task_name:
        Specific prompt file name (without extension).
        e.g. "extract_economic_assumptions"
    data:
        The text/content for the LLM to process.
    run_id:
        Optional run ID for provenance tracking.
    json_mode:
        If True, instructs the model to return JSON only.
        response.structured will contain the parsed dict.
    extra_context:
        Optional additional context prepended to the user message
        (e.g. prior data assessments from a previous run).
    force_provider:
        Override routing and use a specific provider. Use only in tests.
    """
    provider = force_provider or _resolve_provider(task)

    system_prompt, user_message = build_messages(
        role=role,
        task=task,
        task_name=task_name,
        data=data,
        extra_context=extra_context,
    )

    log.info(
        "LLM call | provider=%s role=%s task=%s name=%s",
        provider.value, role.value, task.value, task_name,
    )

    if provider == LLMProvider.ANTHROPIC:
        from engine.llm.providers.anthropic_client import call_anthropic
        return await call_anthropic(
            system_prompt=system_prompt,
            user_message=user_message,
            role=role,
            task=task,
            task_name=task_name,
            run_id=run_id,
            json_mode=json_mode,
        )
    else:
        from engine.llm.providers.openai_client import call_openai
        return await call_openai(
            system_prompt=system_prompt,
            user_message=user_message,
            role=role,
            task=task,
            task_name=task_name,
            run_id=run_id,
            json_mode=json_mode,
        )

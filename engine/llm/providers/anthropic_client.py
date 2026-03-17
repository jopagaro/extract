"""
Anthropic API client.

Wraps the anthropic Python SDK. Do not call this directly —
use the router (engine.llm.providers.router) which selects the
right provider and handles fallback.
"""

from __future__ import annotations

import json

from engine.core.config import get_llm_config, settings
from engine.core.enums import LLMProvider, LLMRole, LLMTask
from engine.core.errors import LLMProviderError
from engine.core.logging import get_logger
from engine.llm.response import LLMResponse

log = get_logger(__name__)


def _get_model(task: LLMTask) -> str:
    config = get_llm_config("anthropic")
    task_models: dict = config.get("task_models", {})
    tier = task_models.get(task.value, "standard")
    models: dict = config.get("models", {})
    return models.get(tier, {}).get("id", config.get("default_model", "claude-sonnet-4-6"))


def _get_settings() -> dict:
    return get_llm_config("anthropic")


async def call_anthropic(
    system_prompt: str,
    user_message: str,
    role: LLMRole,
    task: LLMTask,
    task_name: str,
    *,
    run_id: str | None = None,
    json_mode: bool = False,
) -> LLMResponse:
    """
    Make an async call to the Anthropic Messages API.

    Raises LLMProviderError if the API key is not set or the call fails.
    """
    if not settings.has_anthropic:
        raise LLMProviderError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your .env file to use the Anthropic provider."
        )

    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        raise LLMProviderError("anthropic package is not installed. Run: pip install anthropic")

    cfg = _get_settings()
    model = _get_model(task)
    temperature = cfg.get("temperature", 0.1)
    timeout = cfg.get("request_timeout_seconds", 120)

    client = AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        timeout=timeout,
        max_retries=cfg.get("max_retries", 3),
    )

    # Anthropic uses system as a top-level param, not inside messages
    messages = [{"role": "user", "content": user_message}]

    # For JSON mode with Anthropic, we append an instruction to the system prompt
    active_system = system_prompt
    if json_mode:
        active_system += (
            "\n\nIMPORTANT: Your response must be valid JSON only. "
            "Do not include any text before or after the JSON object."
        )

    log.info("Anthropic call | model=%s task=%s", model, task_name)

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=cfg.get("models", {}).get("standard", {}).get("max_output_tokens", 4096),
            temperature=temperature,
            system=active_system,
            messages=messages,
        )
    except Exception as exc:
        raise LLMProviderError(f"Anthropic API call failed: {exc}") from exc

    content = response.content[0].text if response.content else ""
    usage = response.usage

    structured: dict | None = None
    if json_mode:
        try:
            # Strip markdown code fences if the model wrapped the JSON
            cleaned = content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            structured = json.loads(cleaned.strip())
        except json.JSONDecodeError:
            log.warning("Anthropic returned invalid JSON despite json_mode=True")

    return LLMResponse(
        content=content,
        provider=LLMProvider.ANTHROPIC,
        model=model,
        role=role,
        task=task,
        task_name=task_name,
        input_tokens=usage.input_tokens if usage else 0,
        output_tokens=usage.output_tokens if usage else 0,
        structured=structured,
        run_id=run_id,
    )

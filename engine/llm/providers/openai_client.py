"""
OpenAI API client.

Wraps the openai Python SDK. Do not call this directly —
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
    """Resolve the model ID for a given task from config."""
    config = get_llm_config("openai")
    task_models: dict = config.get("task_models", {})
    tier = task_models.get(task.value, "primary")
    models: dict = config.get("models", {})
    return models.get(tier, {}).get("id", config.get("default_model", "gpt-5.4"))


def _get_settings() -> dict:
    return get_llm_config("openai")


async def call_openai_with_tools(
    system_prompt: str,
    user_message: str,
    role: LLMRole,
    task: LLMTask,
    task_name: str,
    tools: list[dict],
    tool_choice: str | dict = "auto",
    *,
    run_id: str | None = None,
) -> LLMResponse:
    """
    Make an async OpenAI call with tool definitions.

    Forces a tool call and returns the arguments as structured output.
    Use tool_choice={"type": "function", "function": {"name": "..."}} to
    guarantee a specific tool is always called.
    """
    if not settings.has_openai:
        raise LLMProviderError(
            "OPENAI_API_KEY is not set. "
            "Add it to your .env file to use the OpenAI provider."
        )

    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise LLMProviderError("openai package is not installed. Run: pip install openai")

    cfg = _get_settings()
    model = _get_model(task)
    temperature = cfg.get("temperature", 0.1)
    timeout = cfg.get("request_timeout_seconds", 120)

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=timeout,
        max_retries=cfg.get("max_retries", 3),
    )

    log.info("OpenAI tool call | model=%s task=%s tools=%s", model, task_name, [t["function"]["name"] for t in tools])

    try:
        response = await client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            tools=tools,
            tool_choice=tool_choice,
        )
    except Exception as exc:
        raise LLMProviderError(f"OpenAI tool call failed: {exc}") from exc

    message = response.choices[0].message
    usage = response.usage

    structured: dict | None = None
    content = ""

    if message.tool_calls:
        tc = message.tool_calls[0]
        content = tc.function.arguments
        try:
            structured = json.loads(tc.function.arguments)
        except json.JSONDecodeError:
            log.warning("OpenAI tool call returned unparseable arguments for %s", task_name)
    else:
        content = message.content or ""
        log.warning("OpenAI returned no tool call for %s (finish_reason=%s)", task_name, response.choices[0].finish_reason)

    return LLMResponse(
        content=content,
        provider=LLMProvider.OPENAI,
        model=model,
        role=role,
        task=task,
        task_name=task_name,
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
        structured=structured,
        run_id=run_id,
    )


async def call_openai(
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
    Make an async call to the OpenAI Chat Completions API.

    Raises LLMProviderError if the API key is not set or the call fails.
    """
    if not settings.has_openai:
        raise LLMProviderError(
            "OPENAI_API_KEY is not set. "
            "Add it to your .env file to use the OpenAI provider."
        )

    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise LLMProviderError("openai package is not installed. Run: pip install openai")

    cfg = _get_settings()
    model = _get_model(task)
    temperature = cfg.get("temperature", 0.1)
    timeout = cfg.get("request_timeout_seconds", 120)

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=timeout,
        max_retries=cfg.get("max_retries", 3),
    )

    kwargs: dict = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    log.info("OpenAI call | model=%s task=%s", model, task_name)

    try:
        response = await client.chat.completions.create(**kwargs)
    except Exception as exc:
        raise LLMProviderError(f"OpenAI API call failed: {exc}") from exc

    content = response.choices[0].message.content or ""
    usage = response.usage

    structured: dict | None = None
    if json_mode:
        try:
            structured = json.loads(content)
        except json.JSONDecodeError:
            log.warning("OpenAI returned invalid JSON despite json_mode=True")

    return LLMResponse(
        content=content,
        provider=LLMProvider.OPENAI,
        model=model,
        role=role,
        task=task,
        task_name=task_name,
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
        structured=structured,
        run_id=run_id,
    )

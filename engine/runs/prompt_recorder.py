"""
Prompt recorder.

Records every LLM prompt sent and response received during a run.
Writes to prompts.jsonl in the run folder — one entry per LLM call.

This is the audit trail for all LLM-generated content:
  - What was the model asked to do?
  - What exactly did it return?
  - Which model / provider was used?
  - How many tokens did it cost?
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.core.logging import get_logger
from engine.core.paths import run_root

log = get_logger(__name__)

_PROMPTS_FILE = "prompts.jsonl"


def record_prompt(
    project_id: str,
    run_id: str,
    role: str,
    task: str,
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    response: str,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    elapsed_seconds: float | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Append a prompt/response record to prompts.jsonl.

    role: LLMRole value, e.g. "geology_analyst"
    task: LLMTask value or descriptive name, e.g. "deposit_model_hypothesis"
    provider: "openai" or "anthropic"
    model: model name, e.g. "gpt-4o", "claude-opus-4-6"
    system_prompt: the system/role prompt that was prepended
    user_prompt: the full user-turn text sent to the model
    response: the full text response received
    """
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "task": task,
        "provider": provider,
        "model": model,
        "system_prompt_length": len(system_prompt),
        "user_prompt_length": len(user_prompt),
        "response_length": len(response),
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "response": response,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "elapsed_seconds": elapsed_seconds,
    }
    if extra:
        entry["extra"] = extra

    prompts_path = _prompts_path(project_id, run_id)
    prompts_path.parent.mkdir(parents=True, exist_ok=True)
    with prompts_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    log.debug(
        "Prompt recorded | role=%s task=%s model=%s tokens=%s+%s",
        role, task, model, prompt_tokens, completion_tokens,
    )


def read_prompts(project_id: str, run_id: str) -> list[dict[str, Any]]:
    """
    Return all recorded prompts for a run, in chronological order.
    """
    path = _prompts_path(project_id, run_id)
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def total_tokens(project_id: str, run_id: str) -> dict[str, int]:
    """
    Sum prompt and completion tokens across all recorded calls for a run.
    Returns {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}.
    """
    records = read_prompts(project_id, run_id)
    p = sum(r.get("prompt_tokens") or 0 for r in records)
    c = sum(r.get("completion_tokens") or 0 for r in records)
    return {"prompt_tokens": p, "completion_tokens": c, "total_tokens": p + c}


def _prompts_path(project_id: str, run_id: str) -> Path:
    return run_root(project_id, run_id) / _PROMPTS_FILE

"""
LLM response model.

All provider clients return an LLMResponse. Callers always receive
the same structure regardless of which provider was used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from engine.core.enums import LLMProvider, LLMRole, LLMTask


@dataclass
class LLMResponse:
    """
    Structured response from any LLM provider call.

    content        — the raw text output from the model
    provider       — which provider was used
    model          — which model was used
    role           — which analyst role was active
    task           — which task category was run
    task_name      — which specific prompt was used
    input_tokens   — tokens consumed by the input (for cost tracking)
    output_tokens  — tokens in the response
    structured     — parsed JSON if the response was a structured extraction
    run_id         — the run this call belongs to, if known
    called_at      — UTC timestamp of the call
    """
    content: str
    provider: LLMProvider
    model: str
    role: LLMRole
    task: LLMTask
    task_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    structured: dict[str, Any] | None = None
    run_id: str | None = None
    called_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "provider": self.provider.value,
            "model": self.model,
            "role": self.role.value,
            "task": self.task.value,
            "task_name": self.task_name,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "structured": self.structured,
            "run_id": self.run_id,
            "called_at": self.called_at,
        }

"""
LLM response reconciler.

Compares Anthropic and OpenAI outputs field by field and produces:
  - A merged output where they agree
  - Flagged disagreements where they differ
  - A review_required flag if any disagreements exist

For JSON extraction responses, comparison is done field by field.
For prose responses, both versions are preserved side by side.

The analyst sees:
  - merged fields they can trust
  - disagreement cards showing both answers for fields they need to verify
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from engine.core.enums import LLMTask
from engine.core.logging import get_logger
from engine.llm.response import LLMResponse

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Disagreement model
# ---------------------------------------------------------------------------

@dataclass
class Disagreement:
    """
    A single field where the two models returned different values.
    Both answers are preserved for the analyst to review.
    """
    field_path: str                  # dot-notation path e.g. "capex.initial_capex_musd"
    anthropic_value: Any             # what Anthropic returned
    openai_value: Any                # what OpenAI returned
    note: str = ""                   # optional explanation of why this may differ


# ---------------------------------------------------------------------------
# Dual response model
# ---------------------------------------------------------------------------

@dataclass
class DualLLMResponse:
    """
    The result of running both providers on the same task.

    merged            — agreed fields (or the only response if one provider was unavailable)
    disagreements     — fields where the two models returned different values
    review_required   — True if the analyst should check disagreements before using the output
    anthropic         — raw Anthropic response (None if key not set or call failed)
    openai            — raw OpenAI response (None if key not set or call failed)
    task_name         — which task produced this
    run_id            — run this belongs to
    both_available    — True if both providers ran successfully
    generated_at      — UTC timestamp
    """
    merged: dict[str, Any]
    disagreements: list[Disagreement]
    review_required: bool
    anthropic: LLMResponse | None
    openai: LLMResponse | None
    task_name: str
    run_id: str | None = None
    both_available: bool = False
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def total_input_tokens(self) -> int:
        a = self.anthropic.input_tokens if self.anthropic else 0
        b = self.openai.input_tokens if self.openai else 0
        return a + b

    @property
    def total_output_tokens(self) -> int:
        a = self.anthropic.output_tokens if self.anthropic else 0
        b = self.openai.output_tokens if self.openai else 0
        return a + b

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_name": self.task_name,
            "run_id": self.run_id,
            "both_available": self.both_available,
            "review_required": self.review_required,
            "generated_at": self.generated_at,
            "merged": self.merged,
            "disagreements": [
                {
                    "field_path": d.field_path,
                    "anthropic_value": d.anthropic_value,
                    "openai_value": d.openai_value,
                    "note": d.note,
                }
                for d in self.disagreements
            ],
            "token_usage": {
                "total_input": self.total_input_tokens,
                "total_output": self.total_output_tokens,
                "anthropic_input": self.anthropic.input_tokens if self.anthropic else 0,
                "anthropic_output": self.anthropic.output_tokens if self.anthropic else 0,
                "openai_input": self.openai.input_tokens if self.openai else 0,
                "openai_output": self.openai.output_tokens if self.openai else 0,
            },
        }


# ---------------------------------------------------------------------------
# Reconciliation logic
# ---------------------------------------------------------------------------

def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    """
    Flatten a nested dict into dot-notation keys.
    e.g. {"capex": {"initial": 150}} → {"capex.initial": 150}
    """
    items: dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.update(_flatten(v, key))
            else:
                items[key] = v
    else:
        items[prefix] = obj
    return items


def _values_equivalent(a: Any, b: Any) -> bool:
    """
    Check if two extracted values are equivalent.
    Handles numeric near-equality, case-insensitive strings, and nulls.
    """
    if a is None and b is None:
        return True
    if a is None or b is None:
        # One is null — treat as disagreement only if the other is non-trivial
        other = b if a is None else a
        if isinstance(other, str) and other.strip() in ("", "not stated", "unknown"):
            return True
        return False

    # Numeric near-equality (within 0.5% — handles minor rounding differences)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b:
            return True
        avg = (abs(a) + abs(b)) / 2
        if avg == 0:
            return True
        return abs(a - b) / avg < 0.005

    # String case-insensitive comparison
    if isinstance(a, str) and isinstance(b, str):
        return a.strip().lower() == b.strip().lower()

    return a == b


def _reconcile_json(
    a_data: dict[str, Any],
    b_data: dict[str, Any],
) -> tuple[dict[str, Any], list[Disagreement]]:
    """
    Compare two JSON extraction results field by field.

    Returns:
        merged        — fields where both agree (or where only one has a value)
        disagreements — fields where the values differ materially
    """
    a_flat = _flatten(a_data)
    b_flat = _flatten(b_data)
    all_keys = set(a_flat) | set(b_flat)

    merged: dict[str, Any] = {}
    disagreements: list[Disagreement] = []

    for key in sorted(all_keys):
        a_val = a_flat.get(key)
        b_val = b_flat.get(key)

        if _values_equivalent(a_val, b_val):
            # Prefer the non-null value, or Anthropic's value if both present
            merged[key] = a_val if a_val is not None else b_val
        else:
            disagreements.append(
                Disagreement(
                    field_path=key,
                    anthropic_value=a_val,
                    openai_value=b_val,
                )
            )
            # Still include in merged as null — analyst will fill from disagreement review
            merged[key] = None

    return merged, disagreements


def reconcile(
    anthropic_response: LLMResponse | None,
    openai_response: LLMResponse | None,
    task: LLMTask,
    task_name: str,
    run_id: str | None = None,
) -> DualLLMResponse:
    """
    Reconcile two provider responses into a DualLLMResponse.

    Handles all cases:
    - Both available → full comparison
    - Only one available → pass through, no comparison
    - JSON extraction → field-by-field comparison
    - Prose output → both versions preserved, no merging
    """
    both_available = anthropic_response is not None and openai_response is not None

    # Only one provider available — pass through
    if not both_available:
        sole = anthropic_response or openai_response
        assert sole is not None
        merged = sole.structured or {"content": sole.content}
        return DualLLMResponse(
            merged=merged,
            disagreements=[],
            review_required=False,
            anthropic=anthropic_response,
            openai=openai_response,
            task_name=task_name,
            run_id=run_id,
            both_available=False,
        )

    assert anthropic_response is not None
    assert openai_response is not None

    # Both available — compare
    a_struct = anthropic_response.structured
    b_struct = openai_response.structured

    if a_struct is not None and b_struct is not None:
        # Structured JSON extraction — field-by-field comparison
        merged, disagreements = _reconcile_json(a_struct, b_struct)
    else:
        # Prose response — keep both, no field merging
        merged = {
            "anthropic": anthropic_response.content,
            "openai": openai_response.content,
        }
        disagreements = []

    review_required = len(disagreements) > 0

    if disagreements:
        log.info(
            "Reconciliation: %d disagreements in task=%s — review required",
            len(disagreements), task_name,
        )
    else:
        log.info("Reconciliation: full agreement on task=%s", task_name)

    return DualLLMResponse(
        merged=merged,
        disagreements=disagreements,
        review_required=review_required,
        anthropic=anthropic_response,
        openai=openai_response,
        task_name=task_name,
        run_id=run_id,
        both_available=True,
    )

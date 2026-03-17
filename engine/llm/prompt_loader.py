"""
Prompt loader and assembler.

Loads system, role, and task prompt files from prompts/ and assembles
them into the message format expected by the API clients.

Prompt layer order (from prompt_policies.yaml):
  1. base_system.md      — identity, compliance rules, output standards
  2. {role}.md           — which analyst role the LLM is acting as
  3. {task_name}.md      — specific instructions for this task

The assembled system prompt is passed as the system message.
The data (document text, extracted values, etc.) is passed as the user message.
"""

from __future__ import annotations

from pathlib import Path

from engine.core.config import get_llm_config
from engine.core.enums import LLMRole, LLMTask
from engine.core.errors import PromptNotFoundError
from engine.core.logging import get_logger
from engine.core.paths import system_prompt_file, task_prompt_file

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Individual prompt loaders
# ---------------------------------------------------------------------------

def load_system_prompt(role: LLMRole) -> str:
    """
    Load and assemble the full system prompt for a given role.

    Always includes base_system.md first, then the role-specific prompt.
    Returns the combined text as a single string.
    """
    base_path = system_prompt_file("base_system")
    role_path = system_prompt_file(role.value)

    if not base_path.exists():
        raise PromptNotFoundError(f"Base system prompt not found: {base_path}")

    parts: list[str] = [base_path.read_text(encoding="utf-8").strip()]

    if role != LLMRole.BASE:
        if not role_path.exists():
            raise PromptNotFoundError(f"Role prompt not found: {role_path}")
        parts.append(role_path.read_text(encoding="utf-8").strip())

    return "\n\n---\n\n".join(parts)


def load_task_prompt(task: LLMTask, task_name: str) -> str:
    """
    Load the task-specific prompt.

    task:      the category (extraction, summarization, etc.)
    task_name: the specific prompt file name without extension
    """
    path = task_prompt_file(task.value, task_name)
    if not path.exists():
        raise PromptNotFoundError(
            f"Task prompt not found: {path}\n"
            f"Create prompts/{task.value}/{task_name}.md to define this task."
        )
    return path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Assembled message builder
# ---------------------------------------------------------------------------

def build_messages(
    role: LLMRole,
    task: LLMTask,
    task_name: str,
    data: str,
    *,
    extra_context: str | None = None,
) -> tuple[str, str]:
    """
    Assemble the full prompt and return (system_prompt, user_message).

    system_prompt — the assembled base + role + task instructions
    user_message  — the data the LLM should analyse

    Parameters
    ----------
    role:
        Which analyst role to load (e.g. LLMRole.ECONOMICS_ANALYST).
    task:
        Task category (e.g. LLMTask.EXTRACTION).
    task_name:
        Specific prompt file name (e.g. "extract_economic_assumptions").
    data:
        The raw text/content the LLM should process.
    extra_context:
        Optional additional context (e.g. prior data assessments) appended
        to the user message before the data.
    """
    system_prompt = load_system_prompt(role)
    task_instructions = load_task_prompt(task, task_name)

    # Append task instructions to system prompt
    full_system = f"{system_prompt}\n\n---\n\n{task_instructions}"

    # Build user message
    user_parts: list[str] = []
    if extra_context:
        user_parts.append(f"## Additional Context\n\n{extra_context}")
    user_parts.append(f"## Data\n\n{data}")
    user_message = "\n\n".join(user_parts)

    _check_prompt_length(full_system, user_message)

    return full_system, user_message


def _check_prompt_length(system: str, user: str) -> None:
    """Warn if the assembled prompt is very large."""
    try:
        config = get_llm_config("prompt_policies")
        limit = config.get("max_prompt_chars", 400_000)
    except Exception:
        limit = 400_000

    total = len(system) + len(user)
    if total > limit:
        log.warning(
            "Assembled prompt is %d chars, exceeds soft limit of %d. "
            "Consider chunking the input data.",
            total,
            limit,
        )

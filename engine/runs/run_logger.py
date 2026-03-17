"""
Run event logger.

Appends structured JSON log entries to a run's events.jsonl file.
Every significant step the engine takes during a run is recorded here
so runs can be audited and replayed.

Format: one JSON object per line (JSONL), ordered chronologically.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.core.logging import get_logger
from engine.core.paths import run_root

log = get_logger(__name__)

_EVENTS_FILE = "events.jsonl"


def log_event(
    project_id: str,
    run_id: str,
    event_type: str,
    message: str,
    data: dict[str, Any] | None = None,
    level: str = "info",
) -> None:
    """
    Append a structured event to the run's events.jsonl file.

    event_type: a short dotted string, e.g. "geology.risk_assessment.started"
    message: human-readable summary
    data: optional extra structured payload
    level: "info", "warning", "error"
    """
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event_type,
        "message": message,
    }
    if data:
        entry["data"] = data

    events_path = _events_path(project_id, run_id)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def log_step_start(project_id: str, run_id: str, step: str) -> None:
    """Convenience: log the start of a named pipeline step."""
    log_event(project_id, run_id, f"{step}.started", f"Step started: {step}")


def log_step_complete(
    project_id: str,
    run_id: str,
    step: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Convenience: log the completion of a named pipeline step."""
    log_event(project_id, run_id, f"{step}.completed", f"Step completed: {step}", data=data)


def log_step_error(project_id: str, run_id: str, step: str, error: str) -> None:
    """Convenience: log a step-level error."""
    log_event(
        project_id, run_id, f"{step}.error",
        f"Step failed: {step} — {error}",
        data={"error": error},
        level="error",
    )


def read_events(project_id: str, run_id: str) -> list[dict[str, Any]]:
    """
    Return all events for a run as a list of dicts, in file order.
    Returns an empty list if no events file exists.
    """
    path = _events_path(project_id, run_id)
    if not path.exists():
        return []
    events = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def _events_path(project_id: str, run_id: str) -> Path:
    return run_root(project_id, run_id) / _EVENTS_FILE

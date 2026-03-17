"""
Structured logging setup for the engine.

Uses Python's standard logging module configured for:
- Human-readable output in the terminal
- JSON-structured output when LOG_FORMAT=json (for log aggregation tools)
- Log level controlled by LOG_LEVEL environment variable
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON for structured log ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            payload.update(record.extra)  # type: ignore[arg-type]
        return json.dumps(payload, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup_logging(
    level: str | None = None,
    fmt: str | None = None,
) -> None:
    """
    Configure root logging for the engine.

    Called once at startup (CLI entry point or API startup).

    Parameters
    ----------
    level:
        Override for LOG_LEVEL env var. Defaults to INFO.
    fmt:
        Override for LOG_FORMAT env var. "json" for structured, anything else for human.
    """
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    log_format = (fmt or os.getenv("LOG_FORMAT", "human")).lower()

    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove any existing handlers (avoid duplicate logs on re-init)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)

    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.

    Usage:
        log = get_logger(__name__)
        log.info("Processing project %s", project_id)
    """
    return logging.getLogger(name)

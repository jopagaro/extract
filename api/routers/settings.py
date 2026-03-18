"""Settings router — manage API keys and application configuration."""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["settings"])

# Stored at platform root
SETTINGS_FILE = Path(__file__).resolve().parent.parent.parent / "user_settings.json"


class AppSettings(BaseModel):
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


def _load() -> dict:
    if not SETTINGS_FILE.exists():
        return {}
    with SETTINGS_FILE.open() as f:
        return json.load(f)


def _save(data: dict) -> None:
    with SETTINGS_FILE.open("w") as f:
        json.dump(data, f, indent=2)


def load_and_apply_settings() -> None:
    """Called at API startup — pushes saved keys into os.environ if not already set."""
    data = _load()
    if data.get("openai_api_key"):
        os.environ.setdefault("OPENAI_API_KEY", data["openai_api_key"])
    if data.get("anthropic_api_key"):
        os.environ.setdefault("ANTHROPIC_API_KEY", data["anthropic_api_key"])


@router.get("", response_model=AppSettings)
def get_settings() -> AppSettings:
    return AppSettings(**_load())


@router.post("", response_model=AppSettings)
def save_settings(body: AppSettings) -> AppSettings:
    existing = _load()
    data = existing.copy()

    if body.openai_api_key is not None:
        if body.openai_api_key.strip():
            data["openai_api_key"] = body.openai_api_key.strip()
            os.environ["OPENAI_API_KEY"] = body.openai_api_key.strip()
        else:
            data.pop("openai_api_key", None)
            os.environ.pop("OPENAI_API_KEY", None)

    if body.anthropic_api_key is not None:
        if body.anthropic_api_key.strip():
            data["anthropic_api_key"] = body.anthropic_api_key.strip()
            os.environ["ANTHROPIC_API_KEY"] = body.anthropic_api_key.strip()
        else:
            data.pop("anthropic_api_key", None)
            os.environ.pop("ANTHROPIC_API_KEY", None)

    _save(data)
    return AppSettings(**data)

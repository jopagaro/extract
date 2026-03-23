"""Settings router — manage API keys and application configuration."""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["settings"])


def _settings_file() -> Path:
    """Return the settings file path.

    Priority:
    1. EXTRACT_DATA_DIR env var  — set by Tauri shell for the standalone app
    2. Source tree root          — development fallback (next to pyproject.toml)
    """
    data_dir = os.getenv("EXTRACT_DATA_DIR")
    if data_dir:
        p = Path(data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p / "user_settings.json"
    return Path(__file__).resolve().parent.parent.parent / "user_settings.json"


SETTINGS_FILE = _settings_file()


class AppSettings(BaseModel):
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    license_key: str | None = None
    license_verified: bool = False


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

    if body.license_key is not None:
        if body.license_key.strip():
            data["license_key"] = body.license_key.strip().upper()
        else:
            data.pop("license_key", None)
            data.pop("license_verified", None)

    if body.license_verified:
        data["license_verified"] = True

    _save(data)
    return AppSettings(**data)

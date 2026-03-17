"""
Configuration loader.

Loads YAML config files from configs/ and makes them available as typed
Python objects. Configs are cached after first load so repeated access
doesn't hit the filesystem repeatedly during a run.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from engine.core.errors import ConfigNotFoundError
from engine.core.paths import (
    global_config_file,
    llm_config_file,
    price_deck_config_file,
    fiscal_regime_config_file,
    get_projects_root,
)

load_dotenv()


# ---------------------------------------------------------------------------
# Low-level loader
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and return its contents as a dict."""
    if not path.exists():
        raise ConfigNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# Cached config accessors
# ---------------------------------------------------------------------------

@lru_cache(maxsize=64)
def get_global_config(name: str) -> dict[str, Any]:
    """Load a file from configs/global/. Results are cached."""
    return load_yaml(global_config_file(name))


@lru_cache(maxsize=32)
def get_llm_config(name: str) -> dict[str, Any]:
    """Load a file from configs/llm/. Results are cached."""
    return load_yaml(llm_config_file(name))


@lru_cache(maxsize=16)
def get_price_deck(scenario: str) -> dict[str, Any]:
    """Load a price deck config by scenario name (e.g. 'base_case')."""
    return load_yaml(price_deck_config_file(scenario))


@lru_cache(maxsize=16)
def get_fiscal_regime(jurisdiction: str) -> dict[str, Any]:
    """Load a fiscal regime config by jurisdiction slug (e.g. 'canada')."""
    return load_yaml(fiscal_regime_config_file(jurisdiction))


# ---------------------------------------------------------------------------
# Environment-level settings
# (not from YAML — from .env / environment variables)
# ---------------------------------------------------------------------------

class Settings:
    """
    Flat access to environment-level settings.
    Read once at import time. Immutable after that.
    """

    # LLM API keys
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")

    # Paths
    projects_root: str = os.getenv(
        "MINING_PROJECTS_ROOT",
        str(get_projects_root()),
    )

    # API server
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "human")

    # Environment
    env: str = os.getenv("ENV", "development")

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)


# Module-level singleton — import this everywhere
settings = Settings()

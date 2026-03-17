"""
Environment snapshot.

Captures the current Python/platform/package environment for reproducibility.
"""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import packages_distributions, version as pkg_version
from pathlib import Path
from typing import Any

import yaml

from engine.core.logging import get_logger
from engine.core.paths import get_engine_root, run_root

log = get_logger(__name__)

ENGINE_VERSION = "0.1.0"

_KEY_PACKAGES = [
    "polars",
    "pyarrow",
    "openai",
    "anthropic",
    "fastapi",
    "uvicorn",
    "typer",
    "rich",
    "pydantic",
    "httpx",
    "numpy",
    "pandas",
    "openpyxl",
    "pdfplumber",
    "shapely",
    "geopandas",
    "ezdxf",
    "yaml",
    "python-dotenv",
]


def _safe_version(package: str) -> str:
    """Return installed version of a package or 'not_installed'."""
    try:
        return pkg_version(package)
    except Exception:
        # Try alternate names
        alt_names = {
            "yaml": "pyyaml",
            "python-dotenv": "python-dotenv",
        }
        alt = alt_names.get(package)
        if alt:
            try:
                return pkg_version(alt)
            except Exception:
                pass
        return "not_installed"


def capture_environment() -> dict[str, Any]:
    """
    Capture the current execution environment:
    - Python version
    - Platform (OS, arch)
    - Key installed packages and versions
    - Engine version
    - Timestamp
    Returns a dict suitable for writing to environment.yaml.
    """
    packages: dict[str, str] = {}
    for pkg in _KEY_PACKAGES:
        packages[pkg] = _safe_version(pkg)

    return {
        "python_version": sys.version,
        "python_version_info": {
            "major": sys.version_info.major,
            "minor": sys.version_info.minor,
            "micro": sys.version_info.micro,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_implementation": platform.python_implementation(),
        },
        "engine_version": ENGINE_VERSION,
        "engine_root": str(get_engine_root()),
        "packages": packages,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }


def write_environment_snapshot(project_id: str, run_id: str) -> None:
    """Write environment.yaml to the run folder."""
    env = capture_environment()
    run_dir = run_root(project_id, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = run_dir / "environment.yaml"
    with snapshot_path.open("w", encoding="utf-8") as f:
        yaml.dump(env, f, default_flow_style=False, allow_unicode=True)
    log.info("Environment snapshot written to %s", snapshot_path)

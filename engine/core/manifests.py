"""
Manifest reading and writing.

Manifests are JSON files that record what files exist, what was processed,
and what state a project or run is in. They are the engine's memory of
what has happened.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.core.errors import MiningEngineError


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file. Returns empty dict if the file does not exist."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict[str, Any], *, indent: int = 2) -> None:
    """Write a dict to a JSON file, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False, default=str)


def read_source_manifest(project_id: str, projects_root: Path) -> dict[str, Any]:
    """Read the source manifest for a project."""
    from engine.core.paths import project_normalized
    path = project_normalized(project_id) / "metadata" / "source_manifest.json"
    return read_json(path)


def write_source_manifest(
    project_id: str,
    projects_root: Path,
    manifest: dict[str, Any],
) -> None:
    """Write the source manifest for a project."""
    from engine.core.paths import project_normalized
    path = project_normalized(project_id) / "metadata" / "source_manifest.json"
    write_json(path, manifest)


def read_project_metadata(project_id: str) -> dict[str, Any]:
    """Read the project_metadata.json for a project."""
    from engine.core.paths import project_metadata_file
    return read_json(project_metadata_file(project_id))


def update_project_metadata(project_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """
    Merge updates into an existing project_metadata.json and write it back.
    Returns the updated metadata dict.
    """
    from engine.core.paths import project_metadata_file
    path = project_metadata_file(project_id)
    current = read_json(path)
    current.update(updates)
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json(path, current)
    return current


def read_run_config(project_id: str, run_id: str) -> dict[str, Any]:
    """Read the config.yaml for a specific run."""
    from engine.core.paths import run_root
    import yaml
    path = run_root(project_id, run_id) / "config.yaml"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def read_data_assessments(project_id: str) -> list[dict[str, Any]]:
    """
    Read the data_assessments.json for a project.
    Returns an empty list if the file does not exist yet
    (engine hasn't run a critique pass yet).
    """
    from engine.core.paths import project_assessments_file
    data = read_json(project_assessments_file(project_id))
    return data.get("assessments", [])


def write_data_assessments(
    project_id: str,
    assessments: list[dict[str, Any]],
    run_id: str | None = None,
) -> None:
    """
    Write the data_assessments.json for a project.
    Wraps the list in a standard envelope with metadata.
    """
    from engine.core.paths import project_assessments_file
    payload: dict[str, Any] = {
        "project_id": project_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "assessments": assessments,
    }
    write_json(project_assessments_file(project_id), payload)

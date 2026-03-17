"""
Artifact tracker.

Records every output file produced during a run.
Writes an artifacts.json manifest to the run folder listing each artifact
with its type, path, and SHA-256 hash so outputs can be verified later.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.core.hashing import hash_file
from engine.core.logging import get_logger
from engine.core.paths import run_root

log = get_logger(__name__)

_ARTIFACT_MANIFEST = "artifacts.json"


def register_artifact(
    project_id: str,
    run_id: str,
    artifact_type: str,
    file_path: Path,
    description: str = "",
) -> dict[str, Any]:
    """
    Register a produced file as an artifact for this run.

    artifact_type: e.g. "dcf_table", "geology_picture", "report_pdf"
    file_path: absolute path to the produced file
    description: optional human-readable label

    Appends the entry to artifacts.json in the run folder and returns the entry.
    """
    entry: dict[str, Any] = {
        "artifact_type": artifact_type,
        "file_path": str(file_path),
        "description": description,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "sha256": None,
        "size_bytes": None,
    }

    if file_path.exists():
        try:
            entry["sha256"] = hash_file(file_path)
            entry["size_bytes"] = file_path.stat().st_size
        except Exception as e:
            log.warning("Could not hash artifact %s: %s", file_path, e)
    else:
        log.warning("Artifact registered but file not found: %s", file_path)

    manifest = _read_manifest(project_id, run_id)
    manifest["artifacts"].append(entry)
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_manifest(project_id, run_id, manifest)

    log.debug("Artifact registered | type=%s path=%s", artifact_type, file_path)
    return entry


def list_artifacts(
    project_id: str,
    run_id: str,
    artifact_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return all registered artifacts for a run.
    If artifact_type is given, filter to that type only.
    """
    manifest = _read_manifest(project_id, run_id)
    artifacts = manifest.get("artifacts", [])
    if artifact_type:
        artifacts = [a for a in artifacts if a.get("artifact_type") == artifact_type]
    return artifacts


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _manifest_path(project_id: str, run_id: str) -> Path:
    return run_root(project_id, run_id) / _ARTIFACT_MANIFEST


def _read_manifest(project_id: str, run_id: str) -> dict[str, Any]:
    path = _manifest_path(project_id, run_id)
    if not path.exists():
        return {
            "project_id": project_id,
            "run_id": run_id,
            "artifacts": [],
            "updated_at": None,
        }
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_manifest(project_id: str, run_id: str, manifest: dict[str, Any]) -> None:
    path = _manifest_path(project_id, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)

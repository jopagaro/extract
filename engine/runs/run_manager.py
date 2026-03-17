"""
Run manager.

Creates, updates, and finalises run records.
Each run is a single execution of the engine against a project — with a
unique run_id, a status, and a folder on disk for all its outputs.

Run lifecycle:
    create_run() → start_run() → complete_run() / fail_run()
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.core.enums import RunStatus
from engine.core.logging import get_logger
from engine.core.paths import project_runs, run_root

log = get_logger(__name__)

_RUN_MANIFEST_FILE = "run_manifest.json"


def create_run(project_id: str, run_id: str, config: dict[str, Any] | None = None) -> Path:
    """
    Create the run folder and initialise run_manifest.json with PENDING status.

    Returns the run root path.
    """
    run_dir = run_root(project_id, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "project_id": project_id,
        "run_id": run_id,
        "status": RunStatus.PENDING.value,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
        "failed_at": None,
        "failure_reason": None,
        "config": config or {},
    }
    _write_manifest(run_dir, manifest)
    log.info("Run created | project=%s run=%s", project_id, run_id)
    return run_dir


def start_run(project_id: str, run_id: str) -> None:
    """Transition run status to RUNNING and record start timestamp."""
    run_dir = run_root(project_id, run_id)
    manifest = _read_manifest(run_dir)
    manifest["status"] = RunStatus.RUNNING.value
    manifest["started_at"] = datetime.now(timezone.utc).isoformat()
    _write_manifest(run_dir, manifest)
    log.info("Run started | project=%s run=%s", project_id, run_id)


def complete_run(project_id: str, run_id: str, notes: str = "") -> None:
    """Transition run status to COMPLETE and record completion timestamp."""
    run_dir = run_root(project_id, run_id)
    manifest = _read_manifest(run_dir)
    manifest["status"] = RunStatus.COMPLETE.value
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    if notes:
        manifest["notes"] = notes
    _write_manifest(run_dir, manifest)
    log.info("Run complete | project=%s run=%s", project_id, run_id)


def fail_run(project_id: str, run_id: str, reason: str) -> None:
    """Transition run status to FAILED and record the failure reason."""
    run_dir = run_root(project_id, run_id)
    manifest = _read_manifest(run_dir)
    manifest["status"] = RunStatus.FAILED.value
    manifest["failed_at"] = datetime.now(timezone.utc).isoformat()
    manifest["failure_reason"] = reason
    _write_manifest(run_dir, manifest)
    log.error("Run failed | project=%s run=%s reason=%s", project_id, run_id, reason)


def get_run_status(project_id: str, run_id: str) -> str:
    """Return the current RunStatus value for a run."""
    run_dir = run_root(project_id, run_id)
    if not run_dir.exists():
        return RunStatus.PENDING.value
    manifest = _read_manifest(run_dir)
    return manifest.get("status", RunStatus.PENDING.value)


def list_runs(project_id: str) -> list[dict[str, Any]]:
    """
    Return run manifests for a project, ordered newest first.
    """
    runs_dir = project_runs(project_id)
    if not runs_dir.exists():
        return []
    manifests = []
    for run_dir in sorted(runs_dir.iterdir(), reverse=True):
        if run_dir.is_dir():
            manifest_path = run_dir / _RUN_MANIFEST_FILE
            if manifest_path.exists():
                manifests.append(_read_manifest(run_dir))
    return manifests


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _manifest_path(run_dir: Path) -> Path:
    return run_dir / _RUN_MANIFEST_FILE


def _read_manifest(run_dir: Path) -> dict[str, Any]:
    path = _manifest_path(run_dir)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    path = _manifest_path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)

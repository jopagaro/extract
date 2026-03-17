"""
Normalisation orchestrator.

Runs all normalizers for a project in dependency order and returns
a NormalizeResult with full details of what succeeded, failed, and warned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.core.ids import run_id as make_run_id
from engine.core.logging import get_logger
from engine.core.manifests import write_json
from engine.core.paths import project_normalized

log = get_logger(__name__)


@dataclass
class NormalizeResult:
    project_id: str
    run_id: str
    success: bool
    layers_completed: list[str]
    layers_failed: list[str]
    warnings: list[str]
    errors: list[str]
    files_written: list[str]
    started_at: str
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "success": self.success,
            "layers_completed": self.layers_completed,
            "layers_failed": self.layers_failed,
            "warnings": self.warnings,
            "errors": self.errors,
            "files_written": self.files_written,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "warning_count": len(self.warnings),
            "error_count": len(self.errors),
        }


# Layer definitions: (name, import_path, function_name)
_LAYERS = [
    ("metadata", "engine.normalize.metadata_normalizer", "normalise_metadata"),
    ("drilling", "engine.normalize.drilling_normalizer", "normalise_drilling"),
    ("assays", "engine.normalize.assay_normalizer", "normalise_assays"),
    ("geology", "engine.normalize.geology_normalizer", "normalise_geology"),
    ("metallurgy", "engine.normalize.metallurgy_normalizer", "normalise_metallurgy"),
    ("engineering", "engine.normalize.engineering_normalizer", "normalise_engineering"),
    ("economics", "engine.normalize.economics_normalizer", "normalise_economics"),
    ("document_index", "engine.normalize.document_index_normalizer", "normalise_document_index"),
]


def _collect_written_files(project_id: str) -> list[str]:
    """Collect relative paths of all files written under normalized/."""
    norm_root = project_normalized(project_id)
    if not norm_root.exists():
        return []
    files: list[str] = []
    for f in sorted(norm_root.rglob("*")):
        if f.is_file():
            try:
                files.append(str(f.relative_to(norm_root.parent)))
            except ValueError:
                files.append(str(f))
    return files


def normalise_project(project_id: str, run_id: str | None = None) -> NormalizeResult:
    """
    Run all normalizers for a project in dependency order:
    1. metadata
    2. drilling (collars → surveys → assays)
    3. geology (domains, resource)
    4. metallurgy
    5. engineering
    6. economics (builds input book from all above)
    7. document_index

    Each normalizer is called in a try/except — one failure doesn't stop the rest.
    Results are logged and returned in NormalizeResult.
    Writes a normalisation_manifest.json to normalized/metadata/.
    """
    if run_id is None:
        run_id = make_run_id(project_id)

    started_at = datetime.now(timezone.utc).isoformat()
    log.info("Starting normalisation | project=%s run=%s", project_id, run_id)

    layers_completed: list[str] = []
    layers_failed: list[str] = []
    all_warnings: list[str] = []
    all_errors: list[str] = []

    for layer_name, module_path, func_name in _LAYERS:
        log.info("Normalising layer: %s", layer_name)
        try:
            import importlib
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            layer_warnings = func(project_id, run_id)
            layers_completed.append(layer_name)
            all_warnings.extend(
                [f"[{layer_name}] {w}" for w in (layer_warnings or [])]
            )
            log.info(
                "Layer %s complete | %d warnings",
                layer_name, len(layer_warnings or []),
            )
        except Exception as exc:
            layers_failed.append(layer_name)
            error_msg = f"[{layer_name}] {type(exc).__name__}: {exc}"
            all_errors.append(error_msg)
            log.error("Layer %s FAILED: %s", layer_name, exc, exc_info=True)

    completed_at = datetime.now(timezone.utc).isoformat()
    success = len(layers_failed) == 0
    files_written = _collect_written_files(project_id)

    result = NormalizeResult(
        project_id=project_id,
        run_id=run_id,
        success=success,
        layers_completed=layers_completed,
        layers_failed=layers_failed,
        warnings=all_warnings,
        errors=all_errors,
        files_written=files_written,
        started_at=started_at,
        completed_at=completed_at,
    )

    # Write normalisation manifest
    manifest_dir = project_normalized(project_id) / "metadata"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    write_json(manifest_dir / "normalisation_manifest.json", result.to_dict())
    log.info(
        "Normalisation complete | layers_ok=%d layers_failed=%d warnings=%d errors=%d",
        len(layers_completed), len(layers_failed), len(all_warnings), len(all_errors),
    )

    return result

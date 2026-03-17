"""
Metadata normalizer.

Validates and fills defaults in project_metadata.json.
"""

from __future__ import annotations

from datetime import datetime, timezone

from engine.core.logging import get_logger
from engine.core.manifests import read_project_metadata, update_project_metadata
from engine.core.paths import project_normalized

log = get_logger(__name__)

SCHEMA_VERSION = "1.0"


def normalise_metadata(project_id: str, run_id: str) -> list[str]:
    """
    Reads normalized/metadata/project_metadata.json.
    Validates required fields (project_id, schema_version, created_at).
    If fields are missing, fills defaults and writes back.
    Updates status field based on what data is present.
    Returns list of warnings.
    """
    warnings: list[str] = []
    log.info("Normalising metadata for project=%s", project_id)

    metadata = read_project_metadata(project_id)

    if not metadata:
        warnings.append(
            "project_metadata.json not found or empty — creating minimal stub."
        )
        metadata = {}

    changed = False

    if not metadata.get("project_id"):
        metadata["project_id"] = project_id
        warnings.append("project_id was missing — set from argument.")
        changed = True

    if not metadata.get("schema_version"):
        metadata["schema_version"] = SCHEMA_VERSION
        warnings.append(f"schema_version was missing — defaulted to {SCHEMA_VERSION}.")
        changed = True

    if not metadata.get("created_at"):
        metadata["created_at"] = datetime.now(timezone.utc).isoformat()
        warnings.append("created_at was missing — set to current UTC time.")
        changed = True

    # Detect which data layers are present
    normalized_root = project_normalized(project_id)
    layers_present: list[str] = []
    for layer in ("drilling", "assays", "geology", "metallurgy", "engineering", "economics"):
        layer_path = normalized_root / layer
        if layer_path.exists() and any(layer_path.iterdir()):
            layers_present.append(layer)

    metadata["data_layers_present"] = layers_present
    metadata["last_normalised_run"] = run_id
    metadata["last_normalised_at"] = datetime.now(timezone.utc).isoformat()
    changed = True

    if changed:
        update_project_metadata(project_id, metadata)
        log.info("project_metadata.json updated.")

    log.info("Metadata normalisation complete | %d warnings", len(warnings))
    return warnings

"""
Data validation utilities.

Validates dicts and files against JSON schemas from the schemas/ folder.
Used by normalizers and the critic to confirm data meets structural requirements
before it is written to normalized/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.core.errors import SchemaViolationError
from engine.core.paths import schema_file


def load_schema(category: str, name: str) -> dict[str, Any]:
    """Load a JSON schema from schemas/<category>/<name>.schema.json."""
    path = schema_file(category, name)
    if not path.exists():
        raise SchemaViolationError(f"Schema not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_against_schema(
    data: dict[str, Any],
    category: str,
    name: str,
) -> list[str]:
    """
    Validate a dict against a JSON schema.

    Returns a list of validation error messages.
    An empty list means the data is valid.

    Uses jsonschema if installed, otherwise falls back to required-fields-only check.
    """
    schema = load_schema(category, name)
    errors: list[str] = []

    try:
        import jsonschema  # optional dependency
        validator = jsonschema.Draft202012Validator(schema)
        for error in sorted(validator.iter_errors(data), key=str):
            errors.append(f"{'.'.join(str(p) for p in error.absolute_path)}: {error.message}")
    except ImportError:
        # Fallback: check required fields only
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")

    return errors


def assert_valid(data: dict[str, Any], category: str, name: str) -> None:
    """
    Validate data and raise SchemaViolationError if invalid.
    Use this inside normalizers where invalid data should halt the pipeline.
    """
    errors = validate_against_schema(data, category, name)
    if errors:
        raise SchemaViolationError(
            f"Data failed schema validation ({category}/{name}):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


def validate_required_fields(data: dict[str, Any], required: list[str]) -> list[str]:
    """
    Quick check for required fields without loading a schema file.
    Returns a list of missing field names.
    """
    return [field for field in required if data.get(field) is None]

"""
YAML I/O utilities.

Read/write YAML files using PyYAML's safe_load / safe_dump.

Only the safe loader/dumper is used — no arbitrary Python object
serialisation. This is intentional: YAML files in this platform
are configuration and data files, not Python pickle replacements.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_yaml(path: Path | str, *, encoding: str = "utf-8") -> Any:
    """
    Read a YAML file and return the parsed Python object.

    Returns an empty dict if the file does not exist.

    Parameters
    ----------
    path:
        Path to the YAML file.
    encoding:
        File encoding. Defaults to UTF-8.
    """
    path = Path(path)
    if not path.exists():
        return {}
    with path.open("r", encoding=encoding) as fh:
        result = yaml.safe_load(fh)
    # safe_load returns None for an empty file
    return result if result is not None else {}


def write_yaml(
    path: Path | str,
    data: Any,
    *,
    default_flow_style: bool = False,
    allow_unicode: bool = True,
    indent: int = 2,
    encoding: str = "utf-8",
) -> None:
    """
    Serialise *data* to a YAML file, creating parent directories as needed.

    Parameters
    ----------
    path:
        Destination file path.
    data:
        Any YAML-serialisable object (dict, list, str, etc.).
    default_flow_style:
        If False (default), use block-style YAML (human-readable).
        If True, use flow-style (compact, JSON-like).
    allow_unicode:
        Allow non-ASCII characters in output. Defaults to True.
    indent:
        Number of spaces for indentation. Defaults to 2.
    encoding:
        File encoding. Defaults to UTF-8.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding) as fh:
        yaml.safe_dump(
            data,
            fh,
            default_flow_style=default_flow_style,
            allow_unicode=allow_unicode,
            indent=indent,
            sort_keys=False,
        )


def dumps_yaml(
    data: Any,
    *,
    default_flow_style: bool = False,
    allow_unicode: bool = True,
    indent: int = 2,
) -> str:
    """
    Serialise *data* to a YAML string (in-memory, no file I/O).
    """
    return yaml.safe_dump(
        data,
        default_flow_style=default_flow_style,
        allow_unicode=allow_unicode,
        indent=indent,
        sort_keys=False,
    )


def loads_yaml(text: str) -> Any:
    """Parse a YAML string and return the Python object."""
    result = yaml.safe_load(text)
    return result if result is not None else {}


def update_yaml(path: Path | str, updates: dict[str, Any]) -> dict[str, Any]:
    """
    Read an existing YAML mapping, merge *updates* into it, and write it back.

    If the file does not exist, it is created with *updates* as content.
    Returns the merged dict.
    """
    current = read_yaml(path)
    if not isinstance(current, dict):
        raise TypeError(
            f"Cannot merge updates into a non-mapping YAML file: {path}"
        )
    current.update(updates)
    write_yaml(path, current)
    return current

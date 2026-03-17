"""
JSON I/O utilities.

Read/write JSON files with support for:
- Pretty-printing with configurable indentation
- Custom default serialiser for datetime, Path, and dataclass objects
- UTF-8 encoding throughout
"""

from __future__ import annotations

import dataclasses
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Default serialiser
# ---------------------------------------------------------------------------

def _default(obj: Any) -> Any:
    """
    JSON serialiser for types not handled by the stdlib json module.

    Handles:
    - datetime / date  → ISO-8601 string
    - pathlib.Path     → POSIX string
    - dataclasses      → dict via dataclasses.asdict
    - objects with __dict__ → their __dict__
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Path):
        return obj.as_posix()
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serialisable")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_json(path: Path | str, *, encoding: str = "utf-8") -> Any:
    """
    Read a JSON file and return the parsed Python object.

    Returns an empty dict if the file does not exist (consistent with
    engine.core.manifests behaviour).

    Parameters
    ----------
    path:
        Path to the JSON file.
    encoding:
        File encoding. Defaults to UTF-8.
    """
    path = Path(path)
    if not path.exists():
        return {}
    with path.open("r", encoding=encoding) as fh:
        return json.load(fh)


def write_json(
    path: Path | str,
    data: Any,
    *,
    indent: int = 2,
    sort_keys: bool = False,
    encoding: str = "utf-8",
) -> None:
    """
    Serialise *data* to a JSON file, creating parent directories as needed.

    Parameters
    ----------
    path:
        Destination file path.
    data:
        Any JSON-serialisable object (dict, list, str, etc.).
        datetime, Path, and dataclass objects are handled automatically.
    indent:
        Number of spaces for pretty-printing. Use 0 or None for compact output.
    sort_keys:
        Sort dict keys alphabetically. Useful for deterministic diffs.
    encoding:
        File encoding. Defaults to UTF-8.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding) as fh:
        json.dump(
            data,
            fh,
            indent=indent or None,
            sort_keys=sort_keys,
            ensure_ascii=False,
            default=_default,
        )


def dumps_json(
    data: Any,
    *,
    indent: int = 2,
    sort_keys: bool = False,
) -> str:
    """
    Serialise *data* to a JSON string (in-memory, no file I/O).

    Useful for building API responses or embedding JSON in other documents.
    """
    return json.dumps(
        data,
        indent=indent or None,
        sort_keys=sort_keys,
        ensure_ascii=False,
        default=_default,
    )


def loads_json(text: str) -> Any:
    """Parse a JSON string and return the Python object."""
    return json.loads(text)


def update_json(path: Path | str, updates: dict[str, Any]) -> dict[str, Any]:
    """
    Read an existing JSON object, merge *updates* into it, and write it back.

    If the file does not exist, it is created with *updates* as content.
    Returns the merged dict.
    """
    current = read_json(path)
    if not isinstance(current, dict):
        raise TypeError(
            f"Cannot merge updates into a non-dict JSON file: {path}"
        )
    current.update(updates)
    write_json(path, current)
    return current

"""
File hashing utilities.

Used by the source registry to detect when raw files change between runs
and to ensure reproducibility — each run records the hash of every input file.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def hash_file(path: Path, algorithm: str = "sha256", chunk_size: int = 65_536) -> str:
    """
    Return the hex digest of a file using the specified algorithm.

    Reads in chunks so large files (CAD models, GeoTIFFs) don't exhaust memory.
    """
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def hash_string(value: str, algorithm: str = "sha256") -> str:
    """Return the hex digest of a UTF-8 string."""
    h = hashlib.new(algorithm)
    h.update(value.encode("utf-8"))
    return h.hexdigest()


def hash_dict(data: dict, algorithm: str = "sha256") -> str:
    """
    Return a stable hex digest of a dict.

    Keys are sorted before hashing so insertion order does not affect the result.
    """
    import json
    serialised = json.dumps(data, sort_keys=True, ensure_ascii=True)
    return hash_string(serialised, algorithm)


def short_hash(value: str, length: int = 8) -> str:
    """Return a short hash prefix useful for human-readable IDs."""
    return hash_string(value)[:length]

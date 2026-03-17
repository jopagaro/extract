"""
Provenance tracking.

Every value written to normalized/ should be traceable back to:
  - which source file it came from
  - which run produced it
  - which extraction method (LLM / parser / manual override)

This module provides the SourceReference model and helpers for
attaching provenance to data records.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class ExtractionMethod(StrEnum):
    LLM_EXTRACTION = "llm_extraction"
    PARSER = "parser"
    MANUAL_ENTRY = "manual_entry"
    MANUAL_OVERRIDE = "manual_override"
    DERIVED = "derived"          # calculated from other normalised values
    ASSUMED = "assumed"          # not in source — taken from config defaults


@dataclass
class SourceReference:
    """
    Records where a piece of data came from.

    Attached to every extracted or normalised value so the critic and
    reviewers can trace any claim back to its origin.
    """
    source_id: str                          # from source registry
    file_path: str                          # relative to project raw/
    file_hash: str                          # sha256 at time of extraction
    extraction_method: ExtractionMethod
    run_id: str
    extracted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    page: int | None = None                 # for PDF sources
    section: str | None = None             # document section heading
    table: str | None = None               # table identifier if from a table
    notes: str | None = None               # free text — e.g. "unit converted from oz to g"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def attach_provenance(
    record: dict[str, Any],
    source_ref: SourceReference,
    *,
    key: str = "_source",
) -> dict[str, Any]:
    """
    Return a copy of record with a provenance block attached under `key`.
    Does not mutate the input.
    """
    return {**record, key: source_ref.to_dict()}


def strip_provenance(record: dict[str, Any], *, key: str = "_source") -> dict[str, Any]:
    """Return a copy of record with the provenance block removed."""
    return {k: v for k, v in record.items() if k != key}

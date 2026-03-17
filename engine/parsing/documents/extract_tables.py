"""
Table extractor and classifier.

After ``parse_pdf`` and ``parse_xlsx`` produce raw tables, this module
provides functions to:

1. Classify tables by type — resource estimates, cost schedules, production
   schedules, metallurgical recovery tables, etc.
2. Score tables for relevance — how likely is this table to contain
   economically important data?
3. Filter and rank tables for LLM extraction — return only the tables
   worth sending to the LLM, in priority order.

This keeps the LLM context lean: instead of feeding every table in a 300-
page technical report to the LLM, we score and select the high-value ones.

Table classification is heuristic and conservative — when uncertain, a
table is labelled "unknown" rather than misclassified. The downstream LLM
extraction layer handles ambiguity correctly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from engine.core.logging import get_logger
from engine.parsing.documents.parse_pdf import ParsedTable

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Table type taxonomy
# ---------------------------------------------------------------------------

class TableType:
    RESOURCE_ESTIMATE  = "resource_estimate"
    RESERVE_ESTIMATE   = "reserve_estimate"
    PRODUCTION_SCHEDULE = "production_schedule"
    CAPEX_SCHEDULE     = "capex_schedule"
    OPEX_SCHEDULE      = "opex_schedule"
    METALLURGICAL      = "metallurgical_recovery"
    FISCAL_TERMS       = "fiscal_terms"
    SENSITIVITY        = "sensitivity_analysis"
    DRILLHOLE_COLLAR   = "drillhole_collar"
    DRILLHOLE_ASSAY    = "drillhole_assay"
    SUMMARY_ECONOMICS  = "summary_economics"
    GENERAL_DATA       = "general_data"
    UNKNOWN            = "unknown"


# ---------------------------------------------------------------------------
# Keyword signatures per table type
# ---------------------------------------------------------------------------
# Each entry is (required_keywords, optional_bonus_keywords, base_score)
# required_keywords: ALL must appear somewhere in the header/content
# optional_bonus_keywords: each match adds +1 to the score

_TYPE_SIGNATURES: list[tuple[str, frozenset[str], frozenset[str], int]] = [
    (
        TableType.RESOURCE_ESTIMATE,
        frozenset({"tonne", "grade"}),
        frozenset({"measured", "indicated", "inferred", "resource", "contained", "m&i", "cut"}),
        6,
    ),
    (
        TableType.RESERVE_ESTIMATE,
        frozenset({"tonne", "grade"}),
        frozenset({"proven", "probable", "reserve", "dilution", "recovery", "mining"}),
        6,
    ),
    (
        TableType.PRODUCTION_SCHEDULE,
        frozenset({"year", "ore"}),
        frozenset({"tonne", "grade", "recovery", "production", "throughput", "metal", "mine"}),
        5,
    ),
    (
        TableType.CAPEX_SCHEDULE,
        frozenset({"capital", "cost"}),
        frozenset({"initial", "sustaining", "closure", "contingency", "musd", "total", "capex"}),
        5,
    ),
    (
        TableType.OPEX_SCHEDULE,
        frozenset({"operating", "cost"}),
        frozenset({"mining", "processing", "g&a", "unit", "tonne", "aisc", "total", "opex"}),
        5,
    ),
    (
        TableType.METALLURGICAL,
        frozenset({"recovery"}),
        frozenset({"metallurgy", "processing", "concentrate", "reagent", "leach", "flotation", "test"}),
        4,
    ),
    (
        TableType.FISCAL_TERMS,
        frozenset({"tax"}),
        frozenset({"royalty", "corporate", "depreciation", "jurisdiction", "fiscal", "rate", "regime"}),
        4,
    ),
    (
        TableType.SENSITIVITY,
        frozenset({"npv", "irr"}),
        frozenset({"sensitivity", "price", "capex", "opex", "base", "case", "change", "percent"}),
        5,
    ),
    (
        TableType.SUMMARY_ECONOMICS,
        frozenset({"npv"}),
        frozenset({"irr", "payback", "summary", "valuation", "economics", "scenario"}),
        5,
    ),
]


# ---------------------------------------------------------------------------
# Scored / classified table
# ---------------------------------------------------------------------------

@dataclass
class ClassifiedTable:
    """A parsed table with a classification label and relevance score."""
    table: ParsedTable
    table_type: str
    relevance_score: int               # higher = more likely to contain key economic data
    matched_keywords: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = self.table.to_dict()
        d["table_type"] = self.table_type
        d["relevance_score"] = self.relevance_score
        d["matched_keywords"] = self.matched_keywords
        return d


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_tables(tables: list[ParsedTable]) -> list[ClassifiedTable]:
    """
    Classify and score a list of ``ParsedTable`` objects.

    Each table is matched against the type signatures and assigned the
    best-matching type. Unmatched tables are labelled UNKNOWN.

    Returns a list of ``ClassifiedTable`` objects, ordered by relevance
    score (descending).
    """
    classified = [_classify_one(t) for t in tables]
    classified.sort(key=lambda c: c.relevance_score, reverse=True)
    return classified


def get_high_value_tables(
    tables: list[ParsedTable],
    min_score: int = 4,
    max_tables: int | None = None,
) -> list[ClassifiedTable]:
    """
    Return only tables likely to contain economically important data.

    Parameters
    ----------
    tables:
        All tables from the document.
    min_score:
        Minimum relevance score to include. Default 4.
    max_tables:
        If set, return at most this many tables (highest-scored first).
    """
    classified = classify_tables(tables)
    high_value = [c for c in classified if c.relevance_score >= min_score]
    if max_tables:
        high_value = high_value[:max_tables]
    return high_value


def tables_to_markdown(tables: list[ParsedTable | ClassifiedTable]) -> str:
    """
    Convert a list of tables to Markdown format for LLM input.

    Each table is rendered as a Markdown table preceded by its page number
    and type (if classified). This is the format passed to the LLM in
    extraction prompts.
    """
    parts: list[str] = []
    for item in tables:
        t = item.table if isinstance(item, ClassifiedTable) else item
        label = (
            f"**Table (p.{t.page_number}, type: {item.table_type})**"
            if isinstance(item, ClassifiedTable)
            else f"**Table (p.{t.page_number})**"
        )
        parts.append(label + "\n\n" + _table_to_md(t))
    return "\n\n---\n\n".join(parts)


def table_to_text(table: ParsedTable) -> str:
    """
    Convert a single table to a compact text representation.
    Header | row1 | row2 format. Suitable for inclusion in LLM context.
    """
    lines = [" | ".join(table.headers)]
    lines.append(" | ".join(["---"] * len(table.headers)))
    for row in table.rows:
        lines.append(" | ".join(str(v) for v in row))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _classify_one(table: ParsedTable) -> ClassifiedTable:
    """Score a single table against all type signatures."""
    # Build a normalised text blob from headers + first few rows
    text_blob = _table_text_blob(table)

    best_type = TableType.UNKNOWN
    best_score = 0
    best_keywords: list[str] = []

    for type_label, required, bonus, base in _TYPE_SIGNATURES:
        matched = [kw for kw in required if kw in text_blob]
        if len(matched) < len(required):
            continue  # required keywords not all present

        score = base + sum(1 for kw in bonus if kw in text_blob)
        bonus_matched = [kw for kw in bonus if kw in text_blob]
        all_matched = matched + bonus_matched

        if score > best_score:
            best_score = score
            best_type = type_label
            best_keywords = all_matched

    return ClassifiedTable(
        table=table,
        table_type=best_type,
        relevance_score=best_score,
        matched_keywords=best_keywords,
    )


def _table_text_blob(table: ParsedTable) -> str:
    """Create a lowercase text blob from headers and first 5 rows."""
    parts = list(table.headers)
    for row in table.rows[:5]:
        parts.extend(str(v) for v in row if v)
    return " ".join(parts).lower()


def _table_to_md(table: ParsedTable) -> str:
    """Render a ParsedTable as a Markdown table string."""
    if not table.headers:
        return "(empty table)"
    sep = " | ".join(["---"] * len(table.headers))
    header_line = " | ".join(str(h) for h in table.headers)
    row_lines = [
        " | ".join(str(v) if v is not None else "" for v in row)
        for row in table.rows
    ]
    return "\n".join([header_line, sep] + row_lines)

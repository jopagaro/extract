"""
Jurisdiction Risk Lookup
========================
Loads the curated jurisdictions.yaml database and provides fuzzy lookup
by name, alias, or country.  No LLM call — pure static data lookup.

Public API
----------
get_jurisdiction_risk(name: str) -> dict | None
    Return the full risk profile for the best-matching jurisdiction.
    Returns None when no plausible match is found.

detect_jurisdiction(project_facts: dict) -> str | None
    Extract a jurisdiction string from LLM-extracted project facts dict.

list_jurisdictions() -> list[dict]
    Return all jurisdiction entries (id, name, country, risk_tier, risk_level).
"""

from __future__ import annotations

import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_JURISDICTIONS_YAML = (
    Path(__file__).resolve().parents[2] / "configs" / "global" / "jurisdictions.yaml"
)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_database() -> list[dict]:
    """Load and cache the jurisdictions database."""
    with _JURISDICTIONS_YAML.open() as f:
        data = yaml.safe_load(f)
    return data.get("jurisdictions", [])


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return ascii_str.lower().strip()


def _tokens(text: str) -> set[str]:
    """Split normalised text into word-tokens."""
    import re
    return set(re.split(r"[\s,/_\-]+", _normalise(text)))


# ---------------------------------------------------------------------------
# Core lookup
# ---------------------------------------------------------------------------

def get_jurisdiction_risk(name: str) -> dict | None:
    """
    Return the jurisdiction risk profile for *name*.

    Matching strategy (in order):
    1. Exact id match
    2. Exact alias match
    3. Normalised alias substring / superset match
    4. Token-overlap score — pick best if score > 0.4
    5. Return None
    """
    if not name or not name.strip():
        return None

    db = _load_database()
    norm_query = _normalise(name)
    query_tokens = _tokens(name)

    # 1 & 2 — exact id / alias
    for entry in db:
        if norm_query == _normalise(entry["id"]):
            return _enrich(entry)
        for alias in entry.get("aliases", []):
            if norm_query == _normalise(alias):
                return _enrich(entry)

    # 3 — alias substring in either direction
    for entry in db:
        entry_norm = _normalise(entry["name"])
        if norm_query in entry_norm or entry_norm in norm_query:
            return _enrich(entry)
        for alias in entry.get("aliases", []):
            a = _normalise(alias)
            if norm_query in a or a in norm_query:
                return _enrich(entry)

    # 4 — token overlap
    best_score = 0.0
    best_entry = None
    for entry in db:
        candidate_tokens: set[str] = set()
        candidate_tokens.update(_tokens(entry["name"]))
        candidate_tokens.update(_tokens(entry.get("country", "")))
        for alias in entry.get("aliases", []):
            candidate_tokens.update(_tokens(alias))

        if not candidate_tokens:
            continue
        overlap = len(query_tokens & candidate_tokens)
        union = len(query_tokens | candidate_tokens)
        score = overlap / union if union else 0.0
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_score >= 0.35 and best_entry is not None:
        return _enrich(best_entry)

    return None


def _enrich(entry: dict) -> dict:
    """Return a copy of the entry with a computed summary field."""
    result = dict(entry)
    tier = entry.get("risk_tier", 3)
    level = entry.get("risk_level", "moderate")
    stability = entry.get("political_stability", "moderate")

    result["summary"] = (
        f"Tier {tier} jurisdiction ({level.replace('_', ' ')} risk). "
        f"Political stability: {stability.replace('_', ' ')}. "
        f"Corporate tax: {entry.get('corporate_tax_rate_pct', 'n/a')}%. "
        f"Royalty: {entry.get('royalty_rate', 'n/a')}."
    )
    return result


# ---------------------------------------------------------------------------
# Project-facts auto-detector
# ---------------------------------------------------------------------------

_JURISDICTION_KEYS = [
    "jurisdiction",
    "country",
    "project_location",
    "location",
    "state_province",
    "region",
    "project_location.country",
    "project_location.state_province",
]


def detect_jurisdiction(facts: dict) -> str | None:
    """
    Walk the project-facts dict looking for jurisdiction/country fields.
    Returns the first non-empty, non-generic value found.
    """
    _SKIP = {"unknown", "not specified", "n/a", "none", "tbd", "various", ""}

    def _get_nested(d: Any, key: str) -> str | None:
        parts = key.split(".")
        val = d
        for part in parts:
            if not isinstance(val, dict):
                return None
            val = val.get(part)
        if isinstance(val, str) and val.strip().lower() not in _SKIP:
            return val.strip()
        return None

    if not isinstance(facts, dict):
        return None

    for key in _JURISDICTION_KEYS:
        v = _get_nested(facts, key)
        if v:
            return v

    # Recursive shallow search one level deep
    for value in facts.values():
        if isinstance(value, dict):
            for key in _JURISDICTION_KEYS:
                v = _get_nested(value, key)
                if v:
                    return v

    return None


# ---------------------------------------------------------------------------
# List all
# ---------------------------------------------------------------------------

def list_jurisdictions() -> list[dict]:
    """Return minimal summary rows for all jurisdictions."""
    return [
        {
            "id":           e["id"],
            "name":         e["name"],
            "country":      e.get("country", ""),
            "region":       e.get("region", ""),
            "risk_tier":    e.get("risk_tier", 3),
            "risk_level":   e.get("risk_level", "moderate"),
            "fraser_rank_approx": e.get("fraser_rank_approx"),
        }
        for e in _load_database()
    ]

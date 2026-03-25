"""
Fetch recent news and developments for a mining project.

Uses gpt-4o-search-preview for real-time web search, returning structured
news items stored per-project and refreshed on demand.

Search strategy (tiered):
  1. Project-specific search  — project name + operator + jurisdiction
  2. Jurisdiction + commodity  — if tier-1 returns < 3 items, broaden to
                                  regional mining news for the same commodity
  3. Commodity market          — if still sparse, add broad commodity news
     (gold, copper, etc.)

This ensures the feed always has something useful even for unknown or
fictitious project names.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

SEARCH_MODEL   = "gpt-4o-search-preview"
FALLBACK_MODEL = "gpt-4o"

NEWS_CATEGORIES = frozenset({
    "resource_update", "financing", "permitting", "acquisition",
    "production", "management", "esg", "market", "other",
})
SENTIMENTS = frozenset({"positive", "negative", "neutral"})
RELEVANCES = frozenset({"high", "medium", "low"})


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _call_search_model(client, prompt: str) -> str:
    try:
        resp = client.chat.completions.create(
            model=SEARCH_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""
    except Exception as primary_exc:
        logger.warning("gpt-4o-search-preview unavailable (%s), using fallback", primary_exc)
        try:
            resp = client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a mining industry news analyst. "
                            "Note explicitly that responses are based on training data only "
                            "and may not reflect current events."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
            )
            content = resp.choices[0].message.content or ""
            return f"[TRAINING DATA ONLY — not real-time]\n\n{content}"
        except Exception as fallback_exc:
            raise RuntimeError(
                f"Both search and fallback failed: {primary_exc}; {fallback_exc}"
            ) from fallback_exc


def _extract_json(raw: str) -> str | None:
    """
    Try multiple strategies to extract a JSON string from a model response.
    Returns the raw JSON string if found, None otherwise.
    """
    # 1. Strip markdown fences
    cleaned = re.sub(r'^```(?:json)?\s*', '', raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned.strip(), flags=re.MULTILINE)
    cleaned = cleaned.strip()

    # 2. Try the whole cleaned string first
    for candidate in [cleaned, raw.strip()]:
        try:
            json.loads(candidate)
            return candidate
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. Try to find {"items": [...]} object
    m = re.search(r'\{\s*"items"\s*:\s*\[[\s\S]*?\]\s*\}', cleaned)
    if m:
        return m.group()

    # 4. Try any top-level JSON object
    m = re.search(r'\{[\s\S]+\}', cleaned)
    if m:
        try:
            json.loads(m.group())
            return m.group()
        except (json.JSONDecodeError, ValueError):
            pass

    # 5. Try any JSON array
    m = re.search(r'\[[\s\S]+\]', cleaned)
    if m:
        try:
            json.loads(m.group())
            return m.group()
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def _parse_news_items(
    raw: str,
    fallback_headline: str,
    commodity: str,
    default_relevance: str = "medium",
) -> list[dict]:
    """
    Extract a list of structured news items from the model's raw text response.
    Falls back to an empty list (not a prose blob) so callers can handle missing data cleanly.
    """
    json_str = _extract_json(raw)
    if json_str:
        try:
            parsed = json.loads(json_str)
            items = parsed if isinstance(parsed, list) else parsed.get("items", [])
            normalised: list[dict] = []
            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                relevance = item.get("relevance")
                if relevance not in RELEVANCES:
                    relevance = default_relevance
                normalised.append({
                    "news_id":   item.get("news_id") or f"N{i+1:03d}",
                    "headline":  str(item.get("headline") or "Untitled"),
                    "date":      str(item.get("date") or ""),
                    "source":    str(item.get("source") or ""),
                    "url":       item.get("url") or None,
                    "summary":   str(item.get("summary") or ""),
                    "category":  item.get("category") if item.get("category") in NEWS_CATEGORIES else "other",
                    "sentiment": item.get("sentiment") if item.get("sentiment") in SENTIMENTS else "neutral",
                    "relevance": relevance,
                    "tags":      item.get("tags") if isinstance(item.get("tags"), list) else [],
                })
            if normalised:
                return normalised
        except (json.JSONDecodeError, TypeError):
            pass

    # If the model returned prose (not JSON), return empty — the tier logic
    # will fall through to context search rather than showing a JSON blob.
    logger.warning("Could not parse news JSON from model response (len=%d)", len(raw))
    return []


def _is_sparse(items: list[dict]) -> bool:
    """True if the item list has fewer than 3 real (non-summary) entries."""
    real = [i for i in items if not i.get("headline", "").endswith("— recent developments")]
    return len(real) < 3


def _dedupe(items: list[dict]) -> list[dict]:
    """Remove items whose headline is a near-duplicate of an earlier one."""
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        key = re.sub(r'\W+', '', item.get("headline", "")).lower()[:40]
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _renumber(items: list[dict]) -> list[dict]:
    for i, item in enumerate(items):
        item["news_id"] = f"N{i+1:03d}"
    return items


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _project_prompt(
    project_name: str,
    operator: str | None,
    commodity: str,
    jurisdiction: str | None,
    today: str,
    max_items: int,
) -> str:
    search_term = project_name
    if operator:
        search_term += f" ({operator})"
    if jurisdiction:
        search_term += f" {jurisdiction}"
    search_term += " mining"

    return f"""Today is {today}.

Search for the most recent news and developments about this specific mining project or company:
"{search_term}"

Find up to {max_items} individual news items from the past 18 months covering:
- Resource or reserve estimate updates
- Drilling results and exploration activity
- Permitting approvals or regulatory filings
- Financing rounds, equity offerings, debt facilities
- Acquisitions, mergers, joint ventures, royalty/stream deals
- Production updates, commissioning milestones
- Management changes
- ESG, environmental, or community developments
- Market or analyst commentary specific to this project/company

Return a JSON object with this exact structure and nothing else:

{{
  "items": [
    {{
      "news_id": "N001",
      "headline": "string — concise, 10 words max",
      "date": "YYYY-MM-DD or approximate e.g. 'March 2026'",
      "source": "publication or newswire name",
      "url": "URL if known, otherwise null",
      "summary": "2–3 sentence summary",
      "category": "resource_update | financing | permitting | acquisition | production | management | esg | market | other",
      "sentiment": "positive | negative | neutral",
      "relevance": "high | medium | low",
      "tags": ["tag1", "tag2"]
    }}
  ]
}}

If you cannot find any specific news for this project, return an empty items array: {{"items": []}}
Return only the JSON object — no markdown fences, no preamble."""


def _context_prompt(
    commodity: str,
    jurisdiction: str | None,
    today: str,
    max_items: int,
) -> str:
    """Broader fallback: jurisdiction + commodity mining news."""
    scope = f"{jurisdiction} {commodity}" if jurisdiction else commodity
    return f"""Today is {today}.

Search for the most recent mining industry news relevant to {scope} mining.

Find up to {max_items} news items from the past 12 months covering:
- Major project announcements or discoveries in {jurisdiction or "the region"}
- Regulatory changes, permitting updates, or policy developments affecting {commodity} mining
- {commodity} commodity price movements, forecasts, and analyst commentary
- Significant M&A, royalty deals, or financings in the {commodity} mining sector
- Technology or processing developments relevant to {commodity} extraction

Return a JSON object with this exact structure and nothing else:

{{
  "items": [
    {{
      "news_id": "N001",
      "headline": "string — concise, 10 words max",
      "date": "YYYY-MM-DD or approximate",
      "source": "publication or newswire name",
      "url": "URL if known, otherwise null",
      "summary": "2–3 sentence summary",
      "category": "resource_update | financing | permitting | acquisition | production | management | esg | market | other",
      "sentiment": "positive | negative | neutral",
      "relevance": "low",
      "tags": ["tag1", "tag2"]
    }}
  ]
}}

Set relevance to "low" for all items — these are sector/regional context, not project-specific.
Return only the JSON object — no markdown fences, no preamble."""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def fetch_project_news(
    project_name: str,
    operator:     str | None,
    commodity:    str,
    jurisdiction: str | None,
    *,
    max_items: int = 15,
) -> dict[str, Any]:
    """
    Fetch structured recent news for a mining project.

    Returns a news-feed dict:
        {
            "fetched_at":    ISO timestamp,
            "project_name":  str,
            "commodity":     str,
            "jurisdiction":  str | None,
            "items":         list[NewsItem],
            "error":         str | None
        }
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _error_feed(project_name, commodity, jurisdiction,
                           "No OpenAI API key configured — news search unavailable.")

    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    today  = datetime.now(timezone.utc).strftime("%B %d, %Y")

    # ── Tier 1: project-specific search ──────────────────────────────────────
    try:
        raw1 = await asyncio.to_thread(
            _call_search_model, client,
            _project_prompt(project_name, operator, commodity, jurisdiction, today, max_items),
        )
        project_items = _parse_news_items(
            raw1,
            fallback_headline=f"{project_name} — recent developments",
            commodity=commodity,
            default_relevance="high",
        )
    except Exception as exc:
        logger.error("Tier-1 news search failed for %s: %s", project_name, exc)
        project_items = []

    # ── Tier 2: jurisdiction + commodity context (always run in parallel) ────
    # Run the context search regardless so we can merge it if tier-1 is sparse
    context_items: list[dict] = []
    if commodity or jurisdiction:
        try:
            raw2 = await asyncio.to_thread(
                _call_search_model, client,
                _context_prompt(commodity, jurisdiction, today, max_items),
            )
            context_items = _parse_news_items(
                raw2,
                fallback_headline=f"{commodity} mining sector — recent developments",
                commodity=commodity,
                default_relevance="low",
            )
        except Exception as exc:
            logger.warning("Tier-2 context search failed: %s", exc)

    # ── Merge ─────────────────────────────────────────────────────────────────
    # If tier-1 produced real project-specific items, show those first and
    # append context items as background colour.
    # If tier-1 came up empty, context items are the main feed.
    if _is_sparse(project_items):
        combined = project_items + context_items
    else:
        # Cap context items to avoid drowning out project news
        combined = project_items + context_items[:5]

    combined = _dedupe(combined)
    combined = _renumber(combined)

    if not combined:
        return _error_feed(
            project_name, commodity, jurisdiction,
            "No news found for this project or region.",
        )

    return {
        "fetched_at":   datetime.now(timezone.utc).isoformat(),
        "project_name": project_name,
        "commodity":    commodity,
        "jurisdiction": jurisdiction,
        "items":        combined[:max_items],
        "error":        None,
    }


def _error_feed(
    project_name: str,
    commodity: str,
    jurisdiction: str | None,
    error: str,
) -> dict[str, Any]:
    return {
        "fetched_at":   datetime.now(timezone.utc).isoformat(),
        "project_name": project_name,
        "commodity":    commodity,
        "jurisdiction": jurisdiction,
        "items":        [],
        "error":        error,
    }

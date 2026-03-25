"""
Fetch recent news and developments for a mining project.

Uses gpt-4o-search-preview for real-time web search, returning structured
news items stored per-project and refreshed on demand.

Search strategy (tiered):
  1. Project-specific search  — project name + operator + jurisdiction
  2. Jurisdiction + commodity  — if tier-1 returns < 3 items, broaden to
                                  regional mining news for the same commodity
  3. Always returns something useful even for unknown project names.
"""

from __future__ import annotations

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
            return resp.choices[0].message.content or ""
        except Exception as fallback_exc:
            raise RuntimeError(
                f"Both search and fallback failed: {primary_exc}; {fallback_exc}"
            ) from fallback_exc


def _extract_json_object(text: str) -> str | None:
    """
    Find the first complete JSON object or array in text using bracket matching.
    This is robust against prose before/after the JSON and nested arrays.
    """
    # Strip markdown fences first
    cleaned = re.sub(r'```(?:json)?\s*', '', text)
    cleaned = re.sub(r'```', '', cleaned).strip()

    # Try the whole cleaned string first (ideal case: model returned pure JSON)
    try:
        json.loads(cleaned)
        return cleaned
    except (json.JSONDecodeError, ValueError):
        pass

    # Walk character by character to find a valid JSON object or array
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        pos = cleaned.find(start_char)
        while pos != -1:
            depth = 0
            in_str = False
            escape = False
            for i in range(pos, len(cleaned)):
                ch = cleaned[i]
                if escape:
                    escape = False
                    continue
                if ch == '\\' and in_str:
                    escape = True
                    continue
                if ch == '"':
                    in_str = not in_str
                    continue
                if in_str:
                    continue
                if ch == start_char:
                    depth += 1
                elif ch == end_char:
                    depth -= 1
                    if depth == 0:
                        candidate = cleaned[pos:i+1]
                        try:
                            json.loads(candidate)
                            return candidate
                        except (json.JSONDecodeError, ValueError):
                            break  # This start position didn't work, try next
            pos = cleaned.find(start_char, pos + 1)

    return None


def _parse_news_items(
    raw: str,
    default_relevance: str = "medium",
) -> list[dict]:
    """
    Extract a list of structured news items from the model's raw text response.
    Returns an empty list if nothing parseable is found.
    """
    json_str = _extract_json_object(raw)
    if not json_str:
        logger.warning("Could not find JSON in model response (len=%d, preview=%r)",
                       len(raw), raw[:120])
        return []

    try:
        parsed = json.loads(json_str)
        items = parsed if isinstance(parsed, list) else parsed.get("items", [])
        if not isinstance(items, list):
            return []

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
        return normalised

    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("JSON parse error: %s", exc)
        return []


def _is_sparse(items: list[dict]) -> bool:
    """True if the list has fewer than 3 genuine items."""
    return len(items) < 3


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
- Acquisitions, mergers, joint ventures
- Production updates, commissioning milestones
- Management changes
- ESG or community developments
- Market or analyst commentary

You MUST respond with ONLY a valid JSON object. No prose, no markdown, no explanation.
The JSON must have this exact structure:

{{"items": [{{"news_id": "N001", "headline": "string max 10 words", "date": "YYYY-MM-DD", "source": "publication name", "url": "URL or null", "summary": "2-3 sentence summary", "category": "resource_update|financing|permitting|acquisition|production|management|esg|market|other", "sentiment": "positive|negative|neutral", "relevance": "high|medium|low", "tags": ["tag1"]}}]}}

If no specific news exists for this project, return: {{"items": []}}
IMPORTANT: Return ONLY the JSON object. Nothing else."""


def _context_prompt(
    commodity: str,
    jurisdiction: str | None,
    today: str,
    max_items: int,
) -> str:
    scope = f"{jurisdiction} {commodity}" if jurisdiction else commodity
    return f"""Today is {today}.

Search for the most recent mining industry news relevant to {scope} mining.

Find up to {max_items} news items from the past 12 months covering:
- Major project announcements or discoveries in {jurisdiction or "the region"}
- Regulatory changes or policy developments affecting {commodity} mining
- {commodity} price movements, forecasts, and analyst commentary
- Significant M&A or financings in the {commodity} mining sector

You MUST respond with ONLY a valid JSON object. No prose, no markdown, no explanation.

{{"items": [{{"news_id": "N001", "headline": "string max 10 words", "date": "YYYY-MM-DD", "source": "publication name", "url": "URL or null", "summary": "2-3 sentence summary", "category": "resource_update|financing|permitting|acquisition|production|management|esg|market|other", "sentiment": "positive|negative|neutral", "relevance": "low", "tags": ["tag1"]}}]}}

Set relevance to "low" for all items.
IMPORTANT: Return ONLY the JSON object. Nothing else."""


# ---------------------------------------------------------------------------
# Main entry point  (sync — called directly from FastAPI sync endpoint)
# ---------------------------------------------------------------------------

def fetch_project_news_sync(
    project_name: str,
    operator:     str | None,
    commodity:    str,
    jurisdiction: str | None,
    *,
    max_items: int = 15,
) -> dict[str, Any]:
    """
    Fetch structured recent news for a mining project (synchronous version).

    Returns:
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
    project_items: list[dict] = []
    try:
        raw1 = _call_search_model(
            client,
            _project_prompt(project_name, operator, commodity, jurisdiction, today, max_items),
        )
        project_items = _parse_news_items(raw1, default_relevance="high")
        logger.info("Tier-1 returned %d items for '%s'", len(project_items), project_name)
    except Exception as exc:
        logger.error("Tier-1 news search failed: %s", exc)

    # ── Tier 2: jurisdiction + commodity context ───────────────────────────
    context_items: list[dict] = []
    if commodity or jurisdiction:
        try:
            raw2 = _call_search_model(
                client,
                _context_prompt(commodity, jurisdiction, today, max_items),
            )
            context_items = _parse_news_items(raw2, default_relevance="low")
            logger.info("Tier-2 returned %d context items", len(context_items))
        except Exception as exc:
            logger.warning("Tier-2 context search failed: %s", exc)

    # ── Merge ─────────────────────────────────────────────────────────────────
    if _is_sparse(project_items):
        combined = project_items + context_items
    else:
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


# Keep async wrapper for any callers that use it
async def fetch_project_news(
    project_name: str,
    operator:     str | None,
    commodity:    str,
    jurisdiction: str | None,
    *,
    max_items: int = 15,
) -> dict[str, Any]:
    """Async wrapper around fetch_project_news_sync."""
    import asyncio
    return await asyncio.to_thread(
        fetch_project_news_sync,
        project_name, operator, commodity, jurisdiction,
        max_items=max_items,
    )


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

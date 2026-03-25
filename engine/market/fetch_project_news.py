"""
Fetch recent news and developments for a mining project.

Uses gpt-4o-search-preview for real-time web search, returning structured
news items that can be stored per-project and refreshed on demand.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

SEARCH_MODEL  = "gpt-4o-search-preview"
FALLBACK_MODEL = "gpt-4o"

NEWS_CATEGORIES = frozenset({
    "resource_update", "financing", "permitting", "acquisition",
    "production", "management", "esg", "market", "other",
})
SENTIMENTS  = frozenset({"positive", "negative", "neutral"})
RELEVANCES  = frozenset({"high", "medium", "low"})


# ---------------------------------------------------------------------------
# Search + parse
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


def _parse_news_items(raw: str, project_name: str, commodity: str) -> list[dict]:
    """
    Extract a list of structured news items from the model's raw text response.

    First tries to parse embedded JSON.  If that fails, wraps the whole response
    as a single 'market' summary item so the caller always gets something useful.
    """
    # Try to extract a JSON array or object from the response
    json_match = re.search(r'\{[\s\S]*"items"[\s\S]*\}', raw)
    if not json_match:
        json_match = re.search(r'\[[\s\S]*\]', raw)

    if json_match:
        try:
            parsed = json.loads(json_match.group())
            items = parsed if isinstance(parsed, list) else parsed.get("items", [])
            normalised = []
            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                normalised.append({
                    "news_id":  item.get("news_id") or f"N{i+1:03d}",
                    "headline": str(item.get("headline") or "Untitled"),
                    "date":     str(item.get("date") or ""),
                    "source":   str(item.get("source") or ""),
                    "url":      item.get("url") or None,
                    "summary":  str(item.get("summary") or ""),
                    "category": item.get("category") if item.get("category") in NEWS_CATEGORIES else "other",
                    "sentiment":item.get("sentiment") if item.get("sentiment") in SENTIMENTS else "neutral",
                    "relevance":item.get("relevance") if item.get("relevance") in RELEVANCES else "medium",
                    "tags":     item.get("tags") if isinstance(item.get("tags"), list) else [],
                })
            if normalised:
                return normalised
        except (json.JSONDecodeError, TypeError):
            pass

    # Fallback: the model returned prose — store it as a single summary item
    # Strip any training-data notice for display
    display_text = re.sub(r'^\[TRAINING DATA ONLY.*?\]\n\n', '', raw, flags=re.DOTALL).strip()
    is_training_only = "[TRAINING DATA ONLY" in raw
    return [
        {
            "news_id":  "N001",
            "headline": f"{project_name} — recent developments",
            "date":     datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "source":   "AI summary (training data only)" if is_training_only else "AI summary",
            "url":      None,
            "summary":  display_text[:1000],
            "category": "market",
            "sentiment": "neutral",
            "relevance": "medium",
            "tags":     [commodity] if commodity else [],
        }
    ]


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
            "error":         str | None   — set if search failed
        }
    """
    import asyncio

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _error_feed(project_name, commodity, jurisdiction,
                           "No OpenAI API key configured — news search unavailable.")

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    today       = datetime.now(timezone.utc).strftime("%B %d, %Y")
    search_term = project_name
    if operator:
        search_term += f" {operator}"
    if jurisdiction:
        search_term += f" {jurisdiction}"
    search_term += " mining"

    prompt = f"""Today is {today}.

Search for the most recent news and developments about this mining project or company:
"{search_term}"

Find up to {max_items} individual news items from the past 18 months covering:
- Resource or reserve estimate updates
- Drilling results and exploration activity
- Permitting approvals or regulatory filings
- Financing rounds, equity offerings, debt facilities
- Acquisitions, mergers, joint ventures, royalty/stream deals
- Production updates, commissioning milestones
- Management changes (CEO, CFO, board appointments)
- ESG, environmental, or community developments
- Market or analyst commentary specific to this project/company

Return your answer as a JSON object with this exact structure and nothing else:

{{
  "items": [
    {{
      "news_id": "N001",
      "headline": "string — concise headline, 10 words max",
      "date": "YYYY-MM-DD or approximate e.g. 'March 2026'",
      "source": "publication or newswire name",
      "url": "URL if known, otherwise null",
      "summary": "2–3 sentence summary of the development",
      "category": "resource_update | financing | permitting | acquisition | production | management | esg | market | other",
      "sentiment": "positive | negative | neutral",
      "relevance": "high | medium | low",
      "tags": ["tag1", "tag2"]
    }}
  ]
}}

Sort items by date descending (newest first).
If you cannot find any specific news, return an items array with one item summarising what you did find.
Return only the JSON object — no markdown fences, no preamble."""

    try:
        raw = await asyncio.to_thread(_call_search_model, client, prompt)
        items = _parse_news_items(raw, project_name, commodity)
        return {
            "fetched_at":   datetime.now(timezone.utc).isoformat(),
            "project_name": project_name,
            "commodity":    commodity,
            "jurisdiction": jurisdiction,
            "items":        items[:max_items],
            "error":        None,
        }
    except Exception as exc:
        logger.error("News fetch failed for %s: %s", project_name, exc)
        return _error_feed(project_name, commodity, jurisdiction, str(exc))


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

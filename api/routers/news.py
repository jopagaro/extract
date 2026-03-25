"""
News router — per-project news feed and portfolio-level news aggregation.

Endpoints:
  GET  /projects/{id}/news            return cached feed (or empty)
  POST /projects/{id}/news/refresh    fetch fresh news via web search, save, return
  GET  /portfolio/news                aggregate news from all projects
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.core.paths import project_root, get_projects_root

router = APIRouter(tags=["news"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class NewsItem(BaseModel):
    news_id:   str
    headline:  str
    date:      str
    source:    str
    url:       str | None = None
    summary:   str
    category:  str
    sentiment: str
    relevance: str
    tags:      list[str] = []


class NewsFeed(BaseModel):
    fetched_at:   str
    project_name: str
    commodity:    str
    jurisdiction: str | None = None
    items:        list[NewsItem] = []
    error:        str | None = None


class PortfolioNewsItem(NewsItem):
    project_id:   str
    project_name: str


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _news_path(project_id: str) -> Path:
    path = project_root(project_id) / "normalized" / "metadata" / "news_feed.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_feed(project_id: str) -> dict:
    p = _news_path(project_id)
    if not p.exists():
        return {}
    with p.open() as f:
        return json.load(f)


def _save_feed(project_id: str, data: dict) -> None:
    with _news_path(project_id).open("w") as f:
        json.dump(data, f, indent=2)


def _project_exists(project_id: str) -> None:
    if not project_root(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")


# ---------------------------------------------------------------------------
# Project identity helpers
# ---------------------------------------------------------------------------

def _get_project_identity(project_id: str) -> dict:
    """
    Pull project_name, operator, commodity, jurisdiction from the latest run's
    01_project_facts.json.  Falls back to deriving a human name from the project_id.
    """
    runs_dir = project_root(project_id) / "runs"
    if runs_dir.exists():
        for run_dir in sorted(runs_dir.iterdir(), reverse=True):
            facts_file = run_dir / "01_project_facts.json"
            if facts_file.exists():
                try:
                    with facts_file.open() as f:
                        facts = json.load(f)
                    return {
                        "project_name": _field(facts, ["project_name", "name", "property_name"],
                                               _humanise(project_id)),
                        "operator":     _field(facts, ["operator", "company", "developer", "owner"], None),
                        "commodity":    _field(facts, ["commodity", "primary_commodity",
                                                       "commodity_primary", "metal"], "gold"),
                        "jurisdiction": _field(facts, ["jurisdiction", "country",
                                                       "project_location.country",
                                                       "location"], None),
                    }
                except Exception:
                    break

    # No facts found — use project_id as name
    return {
        "project_name": _humanise(project_id),
        "operator":     None,
        "commodity":    "gold",
        "jurisdiction": None,
    }


def _field(d: dict, keys: list[str], default):
    for key in keys:
        # Support dotted paths like "project_location.country"
        parts = key.split(".")
        val = d
        for part in parts:
            if not isinstance(val, dict):
                val = None
                break
            val = val.get(part)
        if val and str(val).strip().lower() not in ("unknown", "not specified", "n/a", "none", ""):
            return val
    return default


def _humanise(project_id: str) -> str:
    return project_id.replace("_", " ").replace("-", " ").title()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/news", response_model=NewsFeed)
def get_news(project_id: str) -> NewsFeed:
    """Return the cached news feed for this project (or an empty feed)."""
    _project_exists(project_id)
    data = _load_feed(project_id)
    if not data:
        identity = _get_project_identity(project_id)
        return NewsFeed(
            fetched_at=datetime.now(timezone.utc).isoformat(),
            project_name=identity["project_name"],
            commodity=identity["commodity"],
            jurisdiction=identity["jurisdiction"],
            items=[],
            error=None,
        )
    return NewsFeed(**data)


@router.post("/projects/{project_id}/news/refresh", response_model=NewsFeed)
def refresh_news(project_id: str) -> NewsFeed:
    """
    Fetch fresh news for this project via web search and cache the result.
    This is a synchronous endpoint — the caller waits for the search to complete.
    """
    _project_exists(project_id)
    identity = _get_project_identity(project_id)

    from engine.market.fetch_project_news import fetch_project_news

    feed_data = asyncio.run(
        fetch_project_news(
            project_name=identity["project_name"],
            operator=identity["operator"],
            commodity=identity["commodity"],
            jurisdiction=identity["jurisdiction"],
        )
    )

    _save_feed(project_id, feed_data)
    return NewsFeed(**feed_data)


@router.get("/portfolio/news")
def portfolio_news(limit: int = 50) -> dict:
    """
    Return recent news items from all projects, sorted newest first.
    Only includes projects that have a cached news feed.
    """
    root = get_projects_root()
    if not root.exists():
        return {"items": [], "total": 0}

    all_items = []
    for project_dir in root.iterdir():
        if not project_dir.is_dir():
            continue
        project_id = project_dir.name
        feed_path = project_dir / "normalized" / "metadata" / "news_feed.json"
        if not feed_path.exists():
            continue
        try:
            with feed_path.open() as f:
                data = json.load(f)
            proj_name = data.get("project_name", _humanise(project_id))
            for item in (data.get("items") or []):
                all_items.append({**item, "project_id": project_id, "project_name": proj_name})
        except Exception:
            continue

    # Sort: high relevance first, then by date descending
    relevance_order = {"high": 0, "medium": 1, "low": 2}
    all_items.sort(
        key=lambda x: (relevance_order.get(x.get("relevance", "medium"), 1), x.get("date", "")),
        reverse=False,
    )
    # Re-sort by date desc within groups is tricky; do a simple date-desc sort
    all_items.sort(key=lambda x: x.get("date", ""), reverse=True)

    return {"items": all_items[:limit], "total": len(all_items)}

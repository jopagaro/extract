"""
Market intelligence gathering — real-time web search via OpenAI's search model.

Uses gpt-4o-search-preview (or gpt-4o with web_search_preview tool) to perform
three parallel searches:

  1. Project-specific intelligence  — news, operator updates, drilling results,
                                      permitting, financing, analyst coverage
  2. Commodity market context       — current prices, supply/demand, price drivers,
                                      analyst forecasts, major producers
  3. Macro & geopolitical context   — interest rates, inflation, FX, equity markets,
                                      sanctions, ESG regulatory environment,
                                      jurisdictional risk for the project country

Results are structured and returned as a dict for injection into the analysis.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

SEARCH_MODEL = "gpt-5-search-api"
FALLBACK_MODEL = "gpt-5.4"


# ---------------------------------------------------------------------------
# Individual search functions
# ---------------------------------------------------------------------------

async def _search_project(
    project_name: str,
    company: str | None,
    commodity: str,
    jurisdiction: str | None,
    client,
) -> dict[str, Any]:
    """Search for news and updates on the specific mining project."""
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")

    parts = [project_name]
    if company:
        parts.append(company)
    parts.append("mining")
    if jurisdiction:
        parts.append(jurisdiction)
    search_subject = " ".join(parts)

    prompt = f"""Today is {today}.

Search for the latest information about this mining project: "{search_subject}"

Find and summarise:
1. The most recent development status (exploration, PEA, PFS, construction, production)
2. Any recent news in the past 12 months (drilling results, resource updates, permitting, financing, partnerships, acquisitions)
3. The operator/owner company status (listed exchange, market cap if available, management notes)
4. Any analyst commentary or coverage
5. Environmental or community issues if any

Be specific with dates and figures. If you cannot find information about this exact project, say so clearly and note what you did find.

Format as structured plain text with clear headings."""

    try:
        response = await asyncio.to_thread(
            _call_search_model, client, prompt
        )
        return {
            "search_subject": search_subject,
            "findings": response,
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.warning("Project search failed: %s", exc)
        return {
            "search_subject": search_subject,
            "findings": f"Search unavailable: {exc}",
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }


async def _search_commodity_market(
    commodity: str,
    client,
) -> dict[str, Any]:
    """Search for current commodity market conditions."""
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")

    prompt = f"""Today is {today}.

Provide a comprehensive current market summary for {commodity} as a commodity.

Cover:
1. Current spot price and recent price trend (past 3–6 months)
2. Key price drivers right now (supply disruptions, demand shifts, geopolitical factors)
3. Major producers and any supply-side developments
4. Demand outlook (end-use markets, EV transition if relevant, industrial demand)
5. Analyst price forecasts for next 12–24 months (name the bank/firm if possible)
6. Currency and inflation impact on the real price
7. Comparison to historical prices — how does today's price compare to 5-year average?

Use real, current data. Include specific numbers and dates.
Format as structured plain text with clear headings."""

    try:
        response = await asyncio.to_thread(
            _call_search_model, client, prompt
        )
        return {
            "commodity": commodity,
            "analysis": response,
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.warning("Commodity search failed: %s", exc)
        return {
            "commodity": commodity,
            "analysis": f"Search unavailable: {exc}",
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }


async def _search_macro_context(
    commodity: str,
    jurisdiction: str | None,
    client,
) -> dict[str, Any]:
    """Search for macroeconomic and geopolitical context."""
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    jurisdiction_clause = f" with specific note on {jurisdiction}" if jurisdiction else ""

    prompt = f"""Today is {today}.

Provide a current macroeconomic and geopolitical context briefing relevant to a {commodity} mining project{jurisdiction_clause}.

Cover:
1. Current US Federal Reserve policy — rate level, recent decisions, forward guidance
2. Global inflation environment — current CPI in major economies
3. US Dollar strength (DXY trend) and impact on commodity prices
4. Global equity markets sentiment (risk-on/risk-off environment)
5. Mining sector investment environment — capital availability, ESG pressures, streaming/royalty activity
6. Any sanctions, trade restrictions, or tariffs affecting mining supply chains
7. Energy costs — diesel/electricity cost trends relevant to mining operations
8. Labour cost environment in the mining sector
{f"9. Jurisdiction-specific risks for {jurisdiction} — political, regulatory, tax, royalty environment" if jurisdiction else ""}

Use real current data. Include specific rates, percentages, and dates.
Format as structured plain text with clear headings."""

    try:
        response = await asyncio.to_thread(
            _call_search_model, client, prompt
        )
        return {
            "jurisdiction": jurisdiction,
            "analysis": response,
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.warning("Macro search failed: %s", exc)
        return {
            "jurisdiction": jurisdiction,
            "analysis": f"Search unavailable: {exc}",
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# OpenAI search model call
# ---------------------------------------------------------------------------

def _call_search_model(client, prompt: str) -> str:
    """
    Call gpt-4o-search-preview. Falls back to gpt-4o if search model
    is not available on this account.
    """
    try:
        response = client.chat.completions.create(
            model=SEARCH_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""
    except Exception as primary_exc:
        # Search model not available — fall back to gpt-4o without live search
        logger.warning(
            "gpt-5-search-api unavailable (%s), falling back to gpt-5.4 "
            "without web search — results will be based on training data only.",
            primary_exc,
        )
        try:
            response = client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a mining industry analyst. Answer based on your "
                            "training data. Clearly note that this is based on training "
                            "data and not real-time web search, and state your knowledge "
                            "cutoff date where relevant."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1500,
            )
            content = response.choices[0].message.content or ""
            return f"[Note: Based on AI training data only — live web search unavailable]\n\n{content}"
        except Exception as fallback_exc:
            raise RuntimeError(
                f"Both search model and fallback failed: {primary_exc}; {fallback_exc}"
            ) from fallback_exc


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def gather_market_intelligence(
    project_facts: dict,
    commodity_prices: dict | None = None,
    macro_snapshot: dict | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """
    Run all three searches in parallel and assemble the market intelligence package.

    Args:
        project_facts:    The extracted project facts dict (from extract_project_facts)
        commodity_prices: Live prices from engine.market.live_prices (optional, pre-fetched)
        macro_snapshot:   Macro indicators from engine.market.live_prices (optional)
        run_id:           For logging

    Returns a structured dict with project_search, commodity_market, macro_context,
    and the live prices data.
    """
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "error": "No OpenAI API key configured — market intelligence unavailable.",
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }

    client = OpenAI(api_key=api_key)

    # Extract identifiers from project facts
    project_name  = _extract_field(project_facts, ["project_name", "name", "property_name"], "Unknown Project")
    company       = _extract_field(project_facts, ["operator", "company", "developer", "owner"], None)
    commodity     = _extract_field(project_facts, ["commodity", "primary_commodity", "metal"], "gold")
    jurisdiction  = _extract_field(project_facts, ["jurisdiction", "country", "location", "province_state"], None)
    today         = datetime.now(timezone.utc).strftime("%B %d, %Y")

    logger.info("Gathering market intelligence for %s (%s) | %s", project_name, commodity, today)

    # Run all three searches in parallel
    project_result, commodity_result, macro_result = await asyncio.gather(
        _search_project(project_name, company, commodity, jurisdiction, client),
        _search_commodity_market(commodity, client),
        _search_macro_context(commodity, jurisdiction, client),
        return_exceptions=False,
    )

    return {
        "gathered_at":       today,
        "run_id":            run_id,
        "project_name":      project_name,
        "commodity":         commodity,
        "jurisdiction":      jurisdiction,
        # Live market data (from yfinance)
        "live_prices":       commodity_prices or {},
        "macro_indicators":  macro_snapshot or {},
        # Web search results
        "project_intelligence": project_result,
        "commodity_market":     commodity_result,
        "macro_context":        macro_result,
        "notice": (
            f"Market intelligence gathered via web search on {today}. "
            "Commodity prices and macroeconomic conditions reflect the state of markets "
            "at the time of this analysis run. All figures should be verified against "
            "primary sources before use in formal studies."
        ),
    }


def _extract_field(facts: dict, keys: list[str], default: Any) -> Any:
    """Try multiple key names in a possibly nested facts dict."""
    for key in keys:
        # Top-level
        val = facts.get(key)
        if val and str(val).strip().lower() not in ("unknown", "not specified", "n/a", "none", ""):
            return val
        # One level deep
        for v in facts.values():
            if isinstance(v, dict):
                val = v.get(key)
                if val and str(val).strip().lower() not in ("unknown", "not specified", "n/a", "none", ""):
                    return val
    return default

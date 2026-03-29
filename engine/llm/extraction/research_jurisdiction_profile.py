"""
research_jurisdiction_profile.py
=================================
Live web search for the mining fiscal regime, royalty structure, and
regulatory environment of any jurisdiction detected from project facts.

Uses gpt-4o-search-preview so results reflect current law and recent
policy changes — not a static database.  Falls back to gpt-4o on
training data if the search model is unavailable.

Public API
----------
research_jurisdiction_profile(jurisdiction, client) -> dict
    Returns a structured profile dict saved as 12_jurisdiction_risk.json.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

SEARCH_MODEL  = "gpt-5-search-api"
FALLBACK_MODEL = "gpt-5.4"


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

def _build_prompt(jurisdiction: str) -> str:
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    return f"""Today is {today}.

You are a mining industry regulatory and tax specialist.

Research and provide a current, accurate profile of the mining fiscal regime
and regulatory environment for: **{jurisdiction}**

Search for the following and return findings as a JSON object:

1. **corporate_tax_rate_pct** — The current corporate income tax rate applicable
   to mining companies (combined federal + state/provincial if relevant). Provide
   a number (e.g. 26.5) or a description if tiered.

2. **royalty_type** — The type of royalty applied to mining production (e.g.
   "Net Smelter Return", "Net Profit Interest", "Gross Revenue", "Mining Tax on
   annual profit", "Ad valorem on production value").

3. **royalty_rate** — The current royalty rate or formula as a plain English
   description (e.g. "3% NSR", "10% of annual mining profit above $500K; 5%
   thereafter", "graduated 2%–5% depending on commodity price").

4. **permitting_overview** — A plain English summary of the main permitting
   pathway for a new mine (key legislation, agencies, approximate timeline,
   any recent changes to process).

5. **key_regulatory_bodies** — List of the main government agencies or bodies
   that approve or oversee mining projects (e.g. environmental assessment body,
   mines ministry, securities regulator).

6. **indigenous_consultation** — Summary of Indigenous or First Nations
   consultation requirements (duty to consult, consent frameworks, impact
   benefit agreement norms, any recent legal changes).

7. **recent_policy_changes** — Any significant changes to mining law, tax,
   royalty, or environmental rules in the past 2–3 years that would affect
   project economics or permitting.

8. **key_strengths** — 3–5 bullet points: what makes this jurisdiction
   attractive for mining investment (infrastructure, geology, stability,
   incentives, capital markets access, etc.).

9. **key_risks** — 3–5 bullet points: material risks to mining projects in
   this jurisdiction (political, environmental, social, regulatory, cost).

10. **fraser_rank** — Fraser Institute Annual Survey of Mining Companies most
    recent ranking for this jurisdiction (the survey rates investment
    attractiveness). Provide the rank number and year if available, or null.

11. **political_stability** — A brief (1–2 sentence) assessment of current
    political stability as it relates to mining investment security.

12. **risk_tier** — Your overall assessment: 1 (low risk, Tier 1 jurisdiction),
    2 (moderate risk), or 3 (elevated risk, frontier/high-risk jurisdiction).

Return ONLY a valid JSON object with these exact keys. Do not include markdown
fences or any text outside the JSON.

Example structure (fill with real researched data):
{{
  "jurisdiction": "{jurisdiction}",
  "corporate_tax_rate_pct": null,
  "royalty_type": null,
  "royalty_rate": null,
  "permitting_overview": null,
  "key_regulatory_bodies": [],
  "indigenous_consultation": null,
  "recent_policy_changes": null,
  "key_strengths": [],
  "key_risks": [],
  "fraser_rank": null,
  "political_stability": null,
  "risk_tier": null,
  "researched_at": "{datetime.now(timezone.utc).isoformat()}",
  "data_source": "live_web_search"
}}

Use real, current, sourced information. If a value is genuinely unknown
after searching, use null rather than guessing."""


# ---------------------------------------------------------------------------
# LLM call (mirrors gather_market_intelligence pattern)
# ---------------------------------------------------------------------------

def _call_search_model(client, prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model=SEARCH_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""
    except Exception as primary_exc:
        logger.warning(
            "gpt-4o-search-preview unavailable (%s), falling back to gpt-4o "
            "for jurisdiction profile — results based on training data.",
            primary_exc,
        )
        try:
            response = client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a mining industry regulatory and tax specialist. "
                            "Answer based on your training data. State your knowledge "
                            "cutoff date where relevant and flag any values that may "
                            "have changed since your training."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            return content
        except Exception as fallback_exc:
            raise RuntimeError(
                f"Both search and fallback failed: {primary_exc}; {fallback_exc}"
            ) from fallback_exc


def _parse_json_response(raw: str, jurisdiction: str) -> dict[str, Any]:
    """Extract JSON from the model response — handles markdown fences."""
    # Strip markdown fences if present
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Find first { ... } block
        brace_match = re.search(r"\{[\s\S]+\}", text)
        if brace_match:
            try:
                data = json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}

    # Ensure mandatory fields always present
    data.setdefault("jurisdiction", jurisdiction)
    data.setdefault("researched_at", datetime.now(timezone.utc).isoformat())
    data.setdefault("data_source", "live_web_search")
    return data


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def research_jurisdiction_profile(
    jurisdiction: str,
    client: Any,
) -> dict[str, Any]:
    """
    Research the current mining fiscal and regulatory profile for *jurisdiction*
    via live web search.

    Args:
        jurisdiction:  Human-readable jurisdiction string, e.g. "Ontario, Canada",
                       "Nevada, United States", "Chile", "Ghana".
        client:        An initialised openai.OpenAI client instance.

    Returns a structured dict ready to be saved as 12_jurisdiction_risk.json.
    """
    prompt = _build_prompt(jurisdiction)
    today  = datetime.now(timezone.utc).isoformat()

    try:
        raw = await asyncio.to_thread(_call_search_model, client, prompt)
        data = _parse_json_response(raw, jurisdiction)
        logger.info("Jurisdiction profile researched for: %s", jurisdiction)
        return data
    except Exception as exc:
        logger.warning("Jurisdiction profile research failed for %s: %s", jurisdiction, exc)
        return {
            "jurisdiction": jurisdiction,
            "error": str(exc),
            "researched_at": today,
            "data_source": "failed",
            "note": (
                "Live web search for jurisdiction profile failed. "
                "Re-run analysis to retry, or consult primary sources for "
                "current tax rates and royalty structures."
            ),
        }

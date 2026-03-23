"""
Live market prices — commodity spot prices and macro indicators.

Fetches real-time data via yfinance for injection into the analysis pipeline.
Falls back gracefully if a ticker is unavailable.

Commodity detection uses the project_facts commodity field to decide which
tickers are most relevant.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ticker maps
# ---------------------------------------------------------------------------

# Commodity keyword → (yfinance ticker, unit label, scale)
COMMODITY_TICKERS: dict[str, tuple[str, str, float]] = {
    "gold":       ("GC=F",   "USD/oz",    1.0),
    "silver":     ("SI=F",   "USD/oz",    1.0),
    "copper":     ("HG=F",   "USD/lb",    1.0),
    "platinum":   ("PL=F",   "USD/oz",    1.0),
    "palladium":  ("PA=F",   "USD/oz",    1.0),
    "nickel":     ("NI=F",   "USD/t",     1.0),
    "zinc":       ("ZNC=F",  "USD/t",     1.0),
    "lead":       ("LD=F",   "USD/t",     1.0),
    "iron":       ("TIO=F",  "USD/t",     1.0),
    "uranium":    ("UX=F",   "USD/lb",    1.0),
    "coal":       ("MTF=F",  "USD/t",     1.0),
    "oil":        ("CL=F",   "USD/bbl",   1.0),
    "crude":      ("CL=F",   "USD/bbl",   1.0),
    "lithium":    ("LITH",   "USD/t",     1.0),   # ETF proxy
    "cobalt":     ("COBA",   "USD/t",     1.0),   # ETF proxy
}

MACRO_TICKERS: dict[str, tuple[str, str]] = {
    "us_10yr_treasury":  ("^TNX",        "% yield"),
    "us_2yr_treasury":   ("^IRX",        "% yield"),
    "dxy_dollar_index":  ("DX-Y.NYB",   "index"),
    "sp500":             ("^GSPC",       "index"),
    "gold_etf_gld":      ("GLD",         "USD/share"),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_commodity_keywords(commodity_str: str) -> list[str]:
    """Return normalised keyword list from a project commodity field."""
    c = commodity_str.lower()
    found = []
    for keyword in COMMODITY_TICKERS:
        if keyword in c:
            found.append(keyword)
    return found or ["gold"]          # default to gold if nothing matches


def _fetch_ticker(ticker: str) -> float | None:
    """Return the latest close price for a ticker, or None on failure."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception as exc:
        logger.debug("yfinance fetch failed for %s: %s", ticker, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_commodity_prices(commodity: str) -> dict[str, Any]:
    """
    Fetch live spot prices for the commodities relevant to this project.

    Returns a dict like:
        {
          "fetched_at": "2025-03-23T14:22:00Z",
          "prices": {
              "gold": {"price": 3120.50, "unit": "USD/oz", "ticker": "GC=F"},
              ...
          }
        }
    """
    keywords = _detect_commodity_keywords(commodity)
    prices: dict[str, Any] = {}

    for kw in keywords:
        ticker, unit, scale = COMMODITY_TICKERS[kw]
        price = _fetch_ticker(ticker)
        if price is not None:
            prices[kw] = {
                "price": round(price * scale, 2),
                "unit": unit,
                "ticker": ticker,
            }

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "commodity_keywords": keywords,
        "prices": prices,
    }


def get_macro_snapshot() -> dict[str, Any]:
    """
    Fetch key macroeconomic indicators.

    Returns a dict like:
        {
          "fetched_at": "...",
          "indicators": {
              "us_10yr_treasury": {"value": 4.42, "unit": "% yield"},
              ...
          }
        }
    """
    indicators: dict[str, Any] = {}

    for name, (ticker, unit) in MACRO_TICKERS.items():
        val = _fetch_ticker(ticker)
        if val is not None:
            indicators[name] = {"value": round(val, 4), "unit": unit}

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "indicators": indicators,
    }


def build_price_context_string(
    commodity_prices: dict,
    macro: dict,
    as_of_date: str | None = None,
) -> str:
    """Format price + macro data as a plain-text context string for the LLM."""
    lines = [
        f"LIVE MARKET PRICES ({as_of_date or datetime.now(timezone.utc).strftime('%Y-%m-%d')})",
        "",
    ]

    prices = commodity_prices.get("prices", {})
    if prices:
        lines.append("Commodity Spot Prices:")
        for name, data in prices.items():
            lines.append(f"  {name.capitalize()}: {data['price']:,.2f} {data['unit']}")
        lines.append("")

    indicators = macro.get("indicators", {})
    if indicators:
        lines.append("Macroeconomic Indicators:")
        label_map = {
            "us_10yr_treasury": "US 10-Year Treasury Yield",
            "us_2yr_treasury":  "US 2-Year Treasury Yield",
            "dxy_dollar_index": "US Dollar Index (DXY)",
            "sp500":            "S&P 500",
            "gold_etf_gld":     "GLD ETF",
        }
        for name, data in indicators.items():
            label = label_map.get(name, name.replace("_", " ").title())
            lines.append(f"  {label}: {data['value']:,.4f} {data['unit']}")

    return "\n".join(lines)

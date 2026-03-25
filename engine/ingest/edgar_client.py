"""
SEC EDGAR API Client
====================
Programmatic access to the SEC's EDGAR full-text search and document API.
No API key required; only a User-Agent header identifying the caller.

Supported filing types that contain mineral resource / technical report data:
  - 40-F   Annual report (Canada-registered, cross-listed on US exchanges)
  - 10-K   Annual report (US domestic)
  - 20-F   Annual report (foreign private issuer)
  - 6-K    Report of foreign private issuer (press releases, interim reports)
  - 8-K    Current report (US — press releases, material events)
  - S-1    Registration statement (exploration-stage)
  - ARS    Annual report to shareholders

Public API
----------
search_companies(query: str, *, max_results: int = 10) -> list[dict]
    Fuzzy search for company names or tickers.

list_filings(
    cik: str,
    *,
    form_types: list[str] | None = None,
    max_results: int = 20,
    after_date: str | None = None,    # "YYYY-MM-DD"
) -> list[dict]
    List filings for a given CIK, newest first.

get_filing_index(cik: str, accession_number: str) -> list[dict]
    List all documents in a specific filing.

download_edgar_document(url: str) -> bytes
    Download a specific document (PDF, HTML, etc.) from EDGAR.

get_company_facts(cik: str) -> dict
    Return the company's full submission facts (name, ticker, etc.).
"""

from __future__ import annotations

import re
import time
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE = "https://data.sec.gov"
_SEARCH_BASE = "https://efts.sec.gov/LATEST/search-index"
_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
_COMPANY_SEARCH = "https://efts.sec.gov/LATEST/search-index"
_COMPANY_TICKERS = "https://www.sec.gov/files/company_tickers.json"
_COMPANY_TICKERS_EXCHANGE = "https://www.sec.gov/files/company_tickers_exchange.json"

# SEC requires: "Sample Company Name AdminContact@example.com"
_HEADERS = {
    "User-Agent": "Extract Mining Intelligence extract@example.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov",
}
_HEADERS_WWW = {
    "User-Agent": "Extract Mining Intelligence extract@example.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov",
}

# Rate limit: SEC allows 10 req/s; we stay conservative
_MIN_INTERVAL = 0.12   # ~8 req/s
_last_request: float = 0.0


def _throttle() -> None:
    global _last_request
    now = time.monotonic()
    wait = _MIN_INTERVAL - (now - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


# ---------------------------------------------------------------------------
# Company search
# ---------------------------------------------------------------------------

def search_companies(query: str, *, max_results: int = 10) -> list[dict]:
    """
    Search for companies by name or ticker using the EDGAR company search.

    Returns a list of dicts:
        {cik, name, ticker, exchanges, sic, sic_description}
    """
    query = query.strip()
    if not query:
        return []

    # Try the EDGAR full-text company search
    try:
        _throttle()
        url = f"https://efts.sec.gov/LATEST/search-index?q=%22{query}%22&dateRange=custom&startdt=2010-01-01&forms=40-F,10-K,20-F&_source=period_of_report,entity_name,file_num,period_of_report,form_type,biz_location,inc_states,category,file_date,id"
        r = httpx.get(url, headers={"User-Agent": "Extract Mining Intelligence extract@example.com"}, timeout=15)
        # Fall through to ticker search if this doesn't work well
    except Exception:
        pass

    # Primary: use the EDGAR company_tickers.json for name/ticker lookup
    try:
        _throttle()
        headers = {"User-Agent": "Extract Mining Intelligence extract@example.com"}
        r = httpx.get(_COMPANY_TICKERS_EXCHANGE, headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            # data["data"] is a list; data["fields"] has column names
            fields = data.get("fields", [])
            rows   = data.get("data", [])
            cik_idx    = fields.index("cik")    if "cik"    in fields else 0
            name_idx   = fields.index("name")   if "name"   in fields else 1
            ticker_idx = fields.index("ticker") if "ticker" in fields else 2
            exch_idx   = fields.index("exchange") if "exchange" in fields else 3

            q_lower = query.lower()
            matches: list[tuple[float, dict]] = []
            for row in rows:
                name   = str(row[name_idx]   if len(row) > name_idx   else "")
                ticker = str(row[ticker_idx] if len(row) > ticker_idx else "")
                cik    = str(row[cik_idx]    if len(row) > cik_idx    else "").zfill(10)
                exch   = str(row[exch_idx]   if len(row) > exch_idx   else "")

                name_lower   = name.lower()
                ticker_lower = ticker.lower()

                # Score: exact ticker > starts with > contains
                score = 0.0
                if ticker_lower == q_lower:
                    score = 1.0
                elif name_lower == q_lower:
                    score = 0.95
                elif ticker_lower.startswith(q_lower):
                    score = 0.8
                elif name_lower.startswith(q_lower):
                    score = 0.75
                elif q_lower in name_lower:
                    score = 0.5
                elif q_lower in ticker_lower:
                    score = 0.4

                if score > 0:
                    matches.append((score, {
                        "cik":    cik,
                        "name":   name,
                        "ticker": ticker,
                        "exchange": exch,
                    }))

            matches.sort(key=lambda x: -x[0])
            return [m[1] for m in matches[:max_results]]
    except Exception:
        pass

    # Fallback: EDGAR full-text search
    try:
        _throttle()
        headers = {"User-Agent": "Extract Mining Intelligence extract@example.com"}
        params = {"company": query, "action": "getcompany", "output": "atom", "count": str(max_results)}
        r = httpx.get("https://www.sec.gov/cgi-bin/browse-edgar", params=params, headers=headers, timeout=15)
        if r.status_code == 200:
            # Parse the Atom feed for company entries
            results = []
            for m in re.finditer(r'<entity-name>(.*?)</entity-name>.*?<CIK>(\d+)</CIK>', r.text, re.DOTALL):
                results.append({
                    "cik":    str(m.group(2)).zfill(10),
                    "name":   m.group(1).strip(),
                    "ticker": "",
                    "exchange": "",
                })
            return results[:max_results]
    except Exception:
        pass

    return []


# ---------------------------------------------------------------------------
# Filings list
# ---------------------------------------------------------------------------

_DEFAULT_FORMS = ["40-F", "10-K", "20-F", "6-K", "8-K", "ARS"]

def list_filings(
    cik: str,
    *,
    form_types: list[str] | None = None,
    max_results: int = 20,
    after_date: str | None = None,
) -> list[dict]:
    """
    Return filings for a given CIK (zero-padded to 10 digits).

    Each entry:
        {accession_number, form_type, filing_date, report_date, primary_document,
         primary_doc_description, filing_url}
    """
    cik = str(cik).lstrip("0") or "0"
    cik_padded = cik.zfill(10)
    want_forms = set(form_types or _DEFAULT_FORMS)

    try:
        _throttle()
        url = f"{_BASE}/submissions/CIK{cik_padded}.json"
        r = httpx.get(url, headers=_HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        raise RuntimeError(f"EDGAR submissions fetch failed for CIK {cik}: {exc}")

    filings_block = data.get("filings", {}).get("recent", {})
    accessions    = filings_block.get("accessionNumber", [])
    form_list     = filings_block.get("form", [])
    dates         = filings_block.get("filingDate", [])
    report_dates  = filings_block.get("reportDate", [])
    primary_docs  = filings_block.get("primaryDocument", [])
    primary_descs = filings_block.get("primaryDocDescription", [])

    results: list[dict] = []
    for i, acc in enumerate(accessions):
        form = form_list[i] if i < len(form_list) else ""
        if form not in want_forms:
            continue
        date = dates[i] if i < len(dates) else ""
        if after_date and date < after_date:
            continue

        acc_no_dashes = acc.replace("-", "")
        primary = primary_docs[i] if i < len(primary_docs) else ""
        desc    = primary_descs[i] if i < len(primary_descs) else ""
        filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dashes}/{primary}" if primary else ""
        index_url  = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dashes}/{acc}-index.htm"

        results.append({
            "accession_number":       acc,
            "form_type":              form,
            "filing_date":            date,
            "report_date":            report_dates[i] if i < len(report_dates) else "",
            "primary_document":       primary,
            "primary_doc_description": desc,
            "filing_url":             filing_url,
            "index_url":              index_url,
            "cik":                    cik_padded,
        })
        if len(results) >= max_results:
            break

    return results


# ---------------------------------------------------------------------------
# Filing index
# ---------------------------------------------------------------------------

def get_filing_index(cik: str, accession_number: str) -> list[dict]:
    """
    Return all documents contained in a specific filing.

    Each entry:
        {sequence, filename, description, document_type, size_bytes, url}
    """
    cik_padded = str(cik).zfill(10)
    acc_no_dashes = accession_number.replace("-", "")
    cik_unpadded  = str(int(cik_padded))

    index_json_url = (
        f"{_BASE}/submissions/CIK{cik_padded}.json"  # already fetched — not ideal
    )
    # Use the filing-submissions index instead
    idx_url = f"https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{acc_no_dashes}/{accession_number}-index.json"

    try:
        _throttle()
        r = httpx.get(idx_url, headers=_HEADERS_WWW, timeout=15)
        r.raise_for_status()
        data = r.json()
        docs: list[dict] = []
        for item in data.get("directory", {}).get("item", []):
            if not isinstance(item, dict):
                continue
            name = item.get("name", "")
            if not name or name.endswith("-index.htm"):
                continue
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext not in ("pdf", "htm", "html", "txt", "xlsx", "xls", "doc", "docx"):
                continue
            docs.append({
                "sequence":     item.get("name", ""),
                "filename":     name,
                "description":  item.get("name", ""),
                "document_type": ext.upper(),
                "size_bytes":   _parse_size(item.get("size", "0")),
                "url": f"https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{acc_no_dashes}/{name}",
            })
        return docs
    except Exception:
        pass

    # Fallback: scrape the HTML index page
    idx_html_url = f"https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{acc_no_dashes}/{accession_number}-index.htm"
    try:
        _throttle()
        r = httpx.get(idx_html_url, headers=_HEADERS_WWW, timeout=15)
        r.raise_for_status()
        docs = []
        for m in re.finditer(
            r'<a href="(/Archives/edgar/data/[^"]+\.(?:pdf|htm|html|txt|xlsx|docx?))"[^>]*>([^<]+)</a>',
            r.text, re.IGNORECASE,
        ):
            href, label = m.group(1), m.group(2).strip()
            fname = href.rsplit("/", 1)[-1]
            docs.append({
                "sequence":     fname,
                "filename":     fname,
                "description":  label,
                "document_type": fname.rsplit(".", 1)[-1].upper() if "." in fname else "?",
                "size_bytes":   0,
                "url": f"https://www.sec.gov{href}",
            })
        return docs
    except Exception as exc:
        raise RuntimeError(f"Could not fetch filing index for {accession_number}: {exc}")


def _parse_size(s: str) -> int:
    try:
        return int(str(s).replace(",", "").strip())
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Document downloader
# ---------------------------------------------------------------------------

def download_edgar_document(url: str, *, timeout: int = 60) -> bytes:
    """Download a document from EDGAR (www.sec.gov) and return raw bytes."""
    _throttle()
    headers = {"User-Agent": "Extract Mining Intelligence extract@example.com"}
    r = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    return r.content


# ---------------------------------------------------------------------------
# Company facts
# ---------------------------------------------------------------------------

def get_company_facts(cik: str) -> dict[str, Any]:
    """Return the full submission record for a CIK (name, tickers, SIC, etc.)."""
    cik_padded = str(cik).zfill(10)
    _throttle()
    r = httpx.get(f"{_BASE}/submissions/CIK{cik_padded}.json", headers=_HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    tickers  = data.get("tickers", [])
    exchanges = data.get("exchanges", [])
    return {
        "cik":        cik_padded,
        "name":       data.get("name", ""),
        "tickers":    tickers,
        "exchanges":  exchanges,
        "sic":        data.get("sic", ""),
        "sic_description": data.get("sicDescription", ""),
        "state_of_inc":    data.get("stateOfIncorporation", ""),
        "fiscal_year_end": data.get("fiscalYearEnd", ""),
        "category":        data.get("category", ""),
        "website":         data.get("website", ""),
    }

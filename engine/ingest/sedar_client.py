"""
SEDAR+ Client
=============
SEDAR+ (sedarplus.ca) replaced the legacy SEDAR system in 2023.  There is
no official programmatic API.  This module provides two capabilities:

1. **URL-based import** — if the caller already has a SEDAR+ document URL
   (obtained from the website), fetch it directly.  SEDAR+ PDFs are publicly
   accessible at predictable URLs.

2. **Search stub** — SEDAR+ search is a JavaScript-rendered SPA that cannot
   be scraped reliably without a headless browser.  This module returns a
   helpful deep-link URL the user can open manually and then paste the
   document URL back into the app.

Public API
----------
is_sedar_url(url: str) -> bool
    Returns True if the URL points to a SEDAR+ document.

fetch_sedar_document(url: str) -> tuple[bytes, str]
    Download a SEDAR+ document and return (bytes, suggested_filename).
    Raises ValueError for non-SEDAR URLs.

get_sedar_search_url(company_name: str, form_type: str | None = None) -> str
    Returns a SEDAR+ search deep-link URL for manual use.

SEDAR+ Document URL patterns
-----------------------------
Direct filing PDFs are served from:
  https://www.sedarplus.ca/csa-party/records/document.html?id=<doc-id>
  (the actual PDF bytes come from the download endpoint)

Download endpoint (PDF):
  https://www.sedarplus.ca/prod/csa-internet/documents/download/<doc-id>
"""

from __future__ import annotations

import re
import urllib.parse
from pathlib import PurePosixPath

import httpx

# ---------------------------------------------------------------------------
# SEDAR+ URL patterns
# ---------------------------------------------------------------------------

_SEDARPLUS_HOSTS = {
    "www.sedarplus.ca",
    "sedarplus.ca",
    "sedar.com",         # legacy — no longer active but recognised
    "www.sedar.com",
}

_SEDARPLUS_DOWNLOAD_PATTERN = re.compile(
    r"https?://(?:www\.)?sedarplus\.ca/.*?(?:download|document).*?(?:[?&]id=|/)([A-Za-z0-9_\-]+)",
    re.IGNORECASE,
)


def is_sedar_url(url: str) -> bool:
    """Return True if the URL looks like a SEDAR or SEDAR+ document link."""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        return parsed.netloc.lower() in _SEDARPLUS_HOSTS
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Fetch SEDAR+ document
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream,text/html,*/*",
    "Accept-Language": "en-CA,en;q=0.9",
}


def fetch_sedar_document(url: str) -> tuple[bytes, str]:
    """
    Fetch a SEDAR+ document by URL.

    Handles:
    - Direct PDF download URLs
    - Document viewer URLs (tries to extract the underlying PDF link)

    Returns:
        (raw_bytes, suggested_filename)

    Raises:
        ValueError: URL is not a SEDAR/SEDAR+ URL
        RuntimeError: download failed
    """
    url = url.strip()
    if not is_sedar_url(url):
        raise ValueError(f"Not a SEDAR/SEDAR+ URL: {url!r}")

    # If the URL is a viewer page, try to convert to a download URL
    download_url = _resolve_download_url(url)

    try:
        r = httpx.get(download_url, headers=_HEADERS, timeout=60, follow_redirects=True)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"SEDAR+ download failed ({exc.response.status_code}): {download_url}")
    except Exception as exc:
        raise RuntimeError(f"SEDAR+ fetch error: {exc}")

    raw = r.content
    if not raw:
        raise RuntimeError("SEDAR+ returned empty response")

    # Suggest a filename
    filename = _infer_filename(r, download_url)
    return raw, filename


def _resolve_download_url(url: str) -> str:
    """
    Convert a SEDAR+ document viewer URL to a direct download URL where possible.

    SEDAR+ document viewer:
      https://www.sedarplus.ca/csa-party/records/document.html?id=<id>
    Direct download:
      https://www.sedarplus.ca/prod/csa-internet/documents/download/<id>
    """
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)

    # Viewer URL with ?id= param
    if "id" in qs:
        doc_id = qs["id"][0]
        return f"https://www.sedarplus.ca/prod/csa-internet/documents/download/{doc_id}"

    # Already looks like a download URL
    if "download" in parsed.path:
        return url

    # Try as-is
    return url


def _infer_filename(response: httpx.Response, url: str) -> str:
    """Infer a reasonable filename from response headers or URL."""
    cd = response.headers.get("content-disposition", "")
    if cd:
        m = re.search(r'filename[^;=\n]*=(["\']?)([^\n"\']+)\1', cd, re.IGNORECASE)
        if m:
            name = m.group(2).strip()
            if name:
                return _sanitise_filename(name)

    # From URL path
    path = PurePosixPath(urllib.parse.urlparse(url).path)
    stem = path.stem or "sedar_document"
    stem = _sanitise_filename(stem)

    # Detect content type
    ct = response.headers.get("content-type", "").split(";")[0].strip().lower()
    ext_map = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-excel": ".xls",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/html": ".html",
        "text/plain": ".txt",
    }
    ext = ext_map.get(ct, path.suffix or ".pdf")
    return f"{stem}{ext}"


def _sanitise_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name[:120].strip("._")


# ---------------------------------------------------------------------------
# SEDAR+ search deep-link
# ---------------------------------------------------------------------------

def get_sedar_search_url(company_name: str, form_type: str | None = None) -> str:
    """
    Return a SEDAR+ search URL that the user can open in a browser.

    SEDAR+ search is a JavaScript SPA — this provides a deep link rather
    than programmatic search results.
    """
    q = urllib.parse.quote(company_name)
    base = f"https://www.sedarplus.ca/csa-party/records/search.html?keyword={q}"
    if form_type:
        base += f"&formType={urllib.parse.quote(form_type)}"
    return base

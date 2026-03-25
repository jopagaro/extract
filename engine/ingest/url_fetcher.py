"""
URL Fetcher — fetch a web page and convert it to clean plain text
so it can be ingested as a source document like any uploaded file.

Handles:
  - Press releases
  - News articles
  - Company website pages
  - EDGAR filing index pages
  - Any publicly accessible HTML page

Returns a plain-text string and a suggested filename derived from the URL.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


# Tags whose content we always strip entirely (scripts, styles, nav clutter)
_STRIP_TAGS = {
    "script", "style", "noscript", "nav", "header", "footer",
    "aside", "form", "button", "iframe", "svg", "img",
    "advertisement", "cookie-banner",
}

# Tags we treat as block-level — insert a newline after
_BLOCK_TAGS = {
    "p", "div", "section", "article", "h1", "h2", "h3",
    "h4", "h5", "h6", "li", "tr", "br", "hr", "blockquote",
    "pre", "figure", "figcaption", "table", "thead", "tbody",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _extract_text(soup: BeautifulSoup) -> str:
    """Walk the soup tree and produce clean readable text."""
    # Remove noise tags entirely
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()

    lines: list[str] = []

    def _walk(node) -> None:
        if hasattr(node, "children"):
            name = getattr(node, "name", None)
            if name in _BLOCK_TAGS:
                # Collect child text, then emit as a block
                child_parts: list[str] = []
                for child in node.children:
                    if hasattr(child, "get_text"):
                        t = child.get_text(" ", strip=True)
                    else:
                        t = str(child).strip()
                    if t:
                        child_parts.append(t)
                line = " ".join(child_parts).strip()
                if line:
                    lines.append(line)
            else:
                for child in node.children:
                    _walk(child)
        else:
            text = str(node).strip()
            if text:
                lines.append(text)

    _walk(soup.body or soup)

    # Join, collapse runs of blank lines
    raw = "\n".join(lines)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    raw = re.sub(r"[ \t]+", " ", raw)
    return raw.strip()


def _slug_from_url(url: str) -> str:
    """Turn a URL into a safe filename stem."""
    parsed = urlparse(url)
    # Use domain + path, strip scheme
    parts = parsed.netloc.replace("www.", "") + parsed.path
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", parts).strip("_")
    return slug[:80] or "webpage"


def fetch_url_as_text(url: str, timeout: float = 20.0) -> tuple[str, str]:
    """
    Fetch a URL and return (clean_text, suggested_filename).

    Raises:
        httpx.HTTPError — on network/HTTP errors
        ValueError — if the page returns non-HTML content
    """
    with httpx.Client(
        headers=_HEADERS,
        follow_redirects=True,
        timeout=timeout,
    ) as client:
        response = client.get(url)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")

    # If it's a PDF, return the raw bytes path for the caller to handle separately
    if "pdf" in content_type:
        raise ValueError(
            f"URL returns a PDF ({content_type}). "
            "Download the file and upload it directly instead."
        )

    if "html" not in content_type and "text" not in content_type:
        raise ValueError(
            f"URL returns non-HTML content ({content_type}). "
            "Only HTML pages are supported by URL ingestion."
        )

    soup = BeautifulSoup(response.text, "html.parser")

    # Try to find a good page title for the header
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # Build the text document
    body_text = _extract_text(soup)

    if not body_text.strip():
        raise ValueError("Page returned no readable text content.")

    # Prepend source metadata header
    header = f"[Source URL: {url}]\n"
    if title:
        header += f"[Page Title: {title}]\n"
    header += "\n"

    full_text = header + body_text

    filename = _slug_from_url(url) + ".txt"
    return full_text, filename

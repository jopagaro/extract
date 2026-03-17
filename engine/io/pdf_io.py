"""
PDF text extraction utilities.

Uses pdfplumber as the primary PDF parser (preferred for structured
text, tables, and coordinate-based extraction). Falls back to pypdf
if pdfplumber is not available.

Neither pdfplumber nor pypdf is listed in pyproject.toml.
Install at least one with:
    pip install pdfplumber          # preferred
    pip install pypdf               # fallback

Both imports are wrapped in try/except blocks so this module can be
imported in environments where neither is installed; functions raise a
clear ImportError with installation instructions when called.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Optional dependency detection
# ---------------------------------------------------------------------------

try:
    import pdfplumber  # noqa: F401
    _PDFPLUMBER_AVAILABLE = True
except ImportError:
    _PDFPLUMBER_AVAILABLE = False

try:
    import pypdf  # noqa: F401
    _PYPDF_AVAILABLE = True
except ImportError:
    # Older name was PyPDF2
    try:
        import PyPDF2 as pypdf  # type: ignore[no-redef]  # noqa: F401, N812
        _PYPDF_AVAILABLE = True
    except ImportError:
        _PYPDF_AVAILABLE = False

_PDF_INSTALL_MSG = (
    "A PDF parsing library is required but none is installed.\n"
    "Install pdfplumber (preferred):  pip install pdfplumber\n"
    "  or pypdf (fallback):           pip install pypdf\n"
    "Add one of these to your pyproject.toml optional dependencies."
)


def _require_pdf_library() -> None:
    if not _PDFPLUMBER_AVAILABLE and not _PYPDF_AVAILABLE:
        raise ImportError(_PDF_INSTALL_MSG)


# ---------------------------------------------------------------------------
# pdfplumber implementation
# ---------------------------------------------------------------------------

def _extract_pages_pdfplumber(path: Path) -> list[str]:
    """Return one string per page using pdfplumber."""
    import pdfplumber
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)
    return pages


def _count_pages_pdfplumber(path: Path) -> int:
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        return len(pdf.pages)


# ---------------------------------------------------------------------------
# pypdf implementation
# ---------------------------------------------------------------------------

def _extract_pages_pypdf(path: Path) -> list[str]:
    """Return one string per page using pypdf."""
    try:
        import pypdf as _pypdf
    except ImportError:
        import PyPDF2 as _pypdf  # type: ignore[no-redef]
    pages: list[str] = []
    reader = _pypdf.PdfReader(str(path))
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return pages


def _count_pages_pypdf(path: Path) -> int:
    try:
        import pypdf as _pypdf
    except ImportError:
        import PyPDF2 as _pypdf  # type: ignore[no-redef]
    reader = _pypdf.PdfReader(str(path))
    return len(reader.pages)


# ---------------------------------------------------------------------------
# Internal dispatch
# ---------------------------------------------------------------------------

def _get_pages(path: Path) -> list[str]:
    """Use pdfplumber if available, else pypdf."""
    if _PDFPLUMBER_AVAILABLE:
        return _extract_pages_pdfplumber(path)
    return _extract_pages_pypdf(path)


def _get_page_count(path: Path) -> int:
    if _PDFPLUMBER_AVAILABLE:
        return _count_pages_pdfplumber(path)
    return _count_pages_pypdf(path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def count_pages(path: Path | str) -> int:
    """
    Return the number of pages in a PDF.

    Parameters
    ----------
    path:
        Path to the PDF file.

    Returns
    -------
    int
    """
    _require_pdf_library()
    return _get_page_count(Path(path))


def extract_text_by_page(path: Path | str) -> list[str]:
    """
    Extract the text of each page as a separate string.

    Parameters
    ----------
    path:
        Path to the PDF file.

    Returns
    -------
    list[str]
        One string per page. Empty pages produce an empty string.
    """
    _require_pdf_library()
    return _get_pages(Path(path))


def extract_text(path: Path | str) -> str:
    """
    Extract all text from a PDF as a single string.

    Pages are joined with a double newline separator.

    Parameters
    ----------
    path:
        Path to the PDF file.

    Returns
    -------
    str
        Full text content of the PDF.
    """
    pages = extract_text_by_page(path)
    return "\n\n".join(pages)


def extract_page_range(
    path: Path | str,
    start_page: int,
    end_page: int,
) -> str:
    """
    Extract text from a range of pages (inclusive, 1-based).

    Parameters
    ----------
    path:
        Path to the PDF file.
    start_page:
        First page to extract (1-based).
    end_page:
        Last page to extract (1-based, inclusive).

    Returns
    -------
    str
        Concatenated text from the requested pages.
    """
    pages = extract_text_by_page(path)
    # Convert to 0-based index
    start_idx = max(0, start_page - 1)
    end_idx = min(len(pages), end_page)
    selected = pages[start_idx:end_idx]
    return "\n\n".join(selected)


def find_pages_with_keywords(
    path: Path | str,
    keywords: list[str],
) -> list[int]:
    """
    Return the 1-based page numbers of pages containing any of the keywords.

    The search is case-insensitive.

    Parameters
    ----------
    path:
        Path to the PDF file.
    keywords:
        List of keywords to search for.

    Returns
    -------
    list[int]
        Sorted list of 1-based page numbers that contain at least one keyword.
    """
    pages = extract_text_by_page(path)
    kws_lower = [k.lower() for k in keywords]
    matches: list[int] = []
    for i, text in enumerate(pages):
        text_lower = text.lower()
        if any(kw in text_lower for kw in kws_lower):
            matches.append(i + 1)  # 1-based
    return matches

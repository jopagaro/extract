"""
PDF parser.

Extracts text, tables, and metadata from PDF files using pdfplumber.
This is the most critical parser in the system — the vast majority of
mining project data arrives as NI 43-101 reports, PEA/PFS documents,
and technical appendices in PDF format.

Design principles
-----------------
- Page-level granularity: text is extracted page-by-page so that provenance
  (page number) is preserved throughout the downstream pipeline.
- Table detection: pdfplumber's table extraction is run on every page and
  results are attached alongside the plain text for that page.
- Tolerant of bad PDFs: scanned / image-only pages produce empty text — we
  record this as a data gap rather than raising an error.
- No OCR in this module: OCR belongs in a separate optional step. This
  parser handles text-layer PDFs only.

Return shape
------------
``ParsedDocument`` carries:
  - metadata   — title, author, page count, etc. from the PDF header
  - pages      — list of ``ParsedPage`` (text + tables per page)
  - full_text  — concatenation of all page text (for quick LLM context)
  - warnings   — list of non-fatal issues (scanned pages, encoding errors)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.core.logging import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ParsedTable:
    """A single table extracted from a document page."""
    page_number: int              # 1-based
    table_index: int              # index of this table on the page (0-based)
    headers: list[str]            # first row treated as headers
    rows: list[list[str]]         # remaining rows; cells are raw strings
    raw: list[list[str | None]]   # pdfplumber raw output (may contain None)
    bbox: tuple[float, ...] | None = None  # bounding box on the page

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def col_count(self) -> int:
        return len(self.headers)

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "table_index": self.table_index,
            "headers": self.headers,
            "rows": self.rows,
            "row_count": self.row_count,
            "col_count": self.col_count,
        }


@dataclass
class ParsedPage:
    """Text and tables for a single PDF page."""
    page_number: int              # 1-based
    text: str                     # extracted plain text (may be empty for scanned pages)
    tables: list[ParsedTable] = field(default_factory=list)
    width: float = 0.0
    height: float = 0.0
    is_scanned: bool = False      # True when text layer is empty or near-empty

    @property
    def word_count(self) -> int:
        return len(self.text.split()) if self.text else 0


@dataclass
class ParsedDocument:
    """
    The complete parsed representation of a PDF document.
    """
    file_path: str                # original file path (string for serialisability)
    file_name: str
    page_count: int
    pages: list[ParsedPage] = field(default_factory=list)

    # PDF header metadata
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    creator: str | None = None
    creation_date: str | None = None

    # Derived
    full_text: str = ""           # concatenation of all page text
    table_count: int = 0
    scanned_page_count: int = 0
    warnings: list[str] = field(default_factory=list)

    def get_text_for_pages(self, page_numbers: list[int]) -> str:
        """Return concatenated text for a specific list of 1-based page numbers."""
        parts = []
        for page in self.pages:
            if page.page_number in page_numbers:
                parts.append(page.text)
        return "\n\n".join(p for p in parts if p)

    def get_all_tables(self) -> list[ParsedTable]:
        """Return all tables from all pages in document order."""
        tables = []
        for page in self.pages:
            tables.extend(page.tables)
        return tables

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "file_name": self.file_name,
            "page_count": self.page_count,
            "table_count": self.table_count,
            "scanned_page_count": self.scanned_page_count,
            "word_count": len(self.full_text.split()) if self.full_text else 0,
            "title": self.title,
            "author": self.author,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# A page is considered scanned if it has fewer than this many characters of text
_SCANNED_PAGE_CHAR_THRESHOLD = 30


def parse_pdf(
    path: Path | str,
    *,
    extract_tables: bool = True,
    max_pages: int | None = None,
    password: str | None = None,
) -> ParsedDocument:
    """
    Parse a PDF file and return a ``ParsedDocument``.

    Parameters
    ----------
    path:
        Path to the PDF file.
    extract_tables:
        Whether to run pdfplumber table detection on each page.
        Set False to speed up parsing for large text-only reports.
    max_pages:
        If set, only parse the first *max_pages* pages. Useful for
        previewing large technical reports.
    password:
        Password for encrypted PDFs (rare but occurs with some filings).

    Returns
    -------
    ParsedDocument
    """
    import pdfplumber

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    log.info("Parsing PDF: %s", path.name)

    doc = ParsedDocument(
        file_path=str(path),
        file_name=path.name,
        page_count=0,
    )

    try:
        open_kwargs: dict[str, Any] = {}
        if password:
            open_kwargs["password"] = password

        with pdfplumber.open(path, **open_kwargs) as pdf:
            # ---- Document metadata ----------------------------------------
            meta = pdf.metadata or {}
            doc.page_count = len(pdf.pages)
            doc.title = _clean_meta(meta.get("Title"))
            doc.author = _clean_meta(meta.get("Author"))
            doc.subject = _clean_meta(meta.get("Subject"))
            doc.creator = _clean_meta(meta.get("Creator"))
            doc.creation_date = _clean_meta(meta.get("CreationDate"))

            if not doc.title and path.stem:
                doc.title = path.stem.replace("_", " ").replace("-", " ")

            # ---- Page iteration -------------------------------------------
            pages_to_parse = pdf.pages
            if max_pages:
                pages_to_parse = pages_to_parse[:max_pages]

            all_text_parts: list[str] = []

            for pdf_page in pages_to_parse:
                page_num = pdf_page.page_number  # pdfplumber is 1-based

                # Extract text
                try:
                    raw_text = pdf_page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                except Exception as exc:
                    raw_text = ""
                    doc.warnings.append(
                        f"Page {page_num}: text extraction failed ({type(exc).__name__})"
                    )

                text = _clean_text(raw_text)
                is_scanned = len(text.strip()) < _SCANNED_PAGE_CHAR_THRESHOLD

                if is_scanned:
                    doc.scanned_page_count += 1
                    doc.warnings.append(
                        f"Page {page_num}: appears to be scanned/image-only "
                        "(no text layer detected)"
                    )

                # Extract tables
                page_tables: list[ParsedTable] = []
                if extract_tables and not is_scanned:
                    try:
                        raw_tables = pdf_page.extract_tables() or []
                        for t_idx, raw_table in enumerate(raw_tables):
                            parsed_table = _parse_raw_table(
                                raw_table, page_number=page_num, table_index=t_idx
                            )
                            if parsed_table is not None:
                                page_tables.append(parsed_table)
                    except Exception as exc:
                        doc.warnings.append(
                            f"Page {page_num}: table extraction failed ({type(exc).__name__})"
                        )

                parsed_page = ParsedPage(
                    page_number=page_num,
                    text=text,
                    tables=page_tables,
                    width=float(pdf_page.width),
                    height=float(pdf_page.height),
                    is_scanned=is_scanned,
                )
                doc.pages.append(parsed_page)

                if text:
                    all_text_parts.append(f"[Page {page_num}]\n{text}")

            doc.full_text = "\n\n".join(all_text_parts)
            doc.table_count = sum(len(p.tables) for p in doc.pages)

    except Exception as exc:
        log.error("Failed to parse PDF %s: %s", path.name, exc)
        doc.warnings.append(f"Fatal parse error: {type(exc).__name__}: {exc}")
        raise

    log.info(
        "PDF parsed | pages=%d tables=%d scanned=%d words=%d warnings=%d",
        doc.page_count,
        doc.table_count,
        doc.scanned_page_count,
        len(doc.full_text.split()),
        len(doc.warnings),
    )
    return doc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Normalise whitespace in extracted text without destroying structure."""
    if not text:
        return ""
    # Collapse runs of more than 3 blank lines to 2 (preserve section breaks)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    # Remove carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip trailing whitespace on each line
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def _clean_meta(value: Any) -> str | None:
    """Clean a PDF metadata string value."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _parse_raw_table(
    raw_table: list[list[str | None]],
    page_number: int,
    table_index: int,
) -> ParsedTable | None:
    """
    Convert a pdfplumber raw table (list of lists, may contain None) into
    a ``ParsedTable``.

    The first non-empty row is used as headers. Empty tables are discarded.
    """
    if not raw_table:
        return None

    # Coerce None cells to empty strings
    cleaned: list[list[str]] = [
        [str(cell).strip() if cell is not None else "" for cell in row]
        for row in raw_table
        if any(cell is not None and str(cell).strip() for cell in row)
    ]

    if len(cleaned) < 2:
        # Need at least a header row and one data row to be useful
        return None

    headers = cleaned[0]
    rows = cleaned[1:]

    # Skip tables that look entirely empty
    if all(all(c == "" for c in row) for row in rows):
        return None

    return ParsedTable(
        page_number=page_number,
        table_index=table_index,
        headers=headers,
        rows=rows,
        raw=[[cell if cell is not None else "" for cell in row] for row in raw_table],
    )

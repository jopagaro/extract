"""
Document section splitter.

Splits a parsed document's full text into named sections so that:
1. The LLM can be given only the relevant section rather than the full document.
2. Provenance (section title, page range) is preserved with each chunk.
3. Large documents can be processed in pieces without exceeding context windows.

Mining technical reports follow a predictable section structure
(NI 43-101 and JORC have mandated section lists). We use that structure
to produce reliable splits.

Section detection strategy
--------------------------
1. Look for lines that match known section title patterns (numbered headings,
   ALL CAPS titles, or title-case lines followed by a blank line).
2. Fall back to page-boundary splitting if no section structure is detected
   (e.g. scanned-then-OCR'd documents with erratic formatting).
3. Always break at a maximum chunk size to keep LLM context manageable.

The output is a list of ``DocumentSection`` objects, each carrying:
  - title      — the detected section heading
  - text       — the section body text
  - page_start / page_end — approximate page range (from page markers in text)
  - chunk_index — global ordering index
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from engine.core.constants import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
from engine.core.logging import get_logger
from engine.parsing.documents.parse_pdf import ParsedDocument, ParsedPage

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class DocumentSection:
    """A named section of a document with its text content."""
    title: str
    text: str
    chunk_index: int
    page_start: int | None = None
    page_end: int | None = None
    source_file: str = ""
    char_count: int = 0
    word_count: int = 0

    def __post_init__(self) -> None:
        self.char_count = len(self.text)
        self.word_count = len(self.text.split()) if self.text else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "chunk_index": self.chunk_index,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "source_file": self.source_file,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "text": self.text,
        }


# ---------------------------------------------------------------------------
# Known NI 43-101 / JORC section title patterns
# Used to seed section detection and to label anonymous breaks
# ---------------------------------------------------------------------------

_KNOWN_SECTION_TITLES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bexecutive\s+summary\b", re.I), "Executive Summary"),
    (re.compile(r"\bproperty\s+description\b", re.I), "Property Description"),
    (re.compile(r"\bgeological\s+setting\b|\bregional\s+geology\b", re.I), "Geological Setting"),
    (re.compile(r"\bexploration\b", re.I), "Exploration"),
    (re.compile(r"\bdrilling\b", re.I), "Drilling"),
    (re.compile(r"\bsampling\b|\bsample\s+preparation\b", re.I), "Sampling"),
    (re.compile(r"\bmineral\s+resource\s+estimate\b|\bresource\s+estimate\b", re.I), "Resource Estimate"),
    (re.compile(r"\bmineral\s+reserve\b|\breserve\s+estimate\b", re.I), "Reserve Estimate"),
    (re.compile(r"\bmetallurgy\b|\bmetallurgical\b", re.I), "Metallurgy"),
    (re.compile(r"\bmine\s+plan\b|\bmining\s+method\b", re.I), "Mine Plan"),
    (re.compile(r"\bprocessing\b|\bprocess\s+plant\b", re.I), "Processing"),
    (re.compile(r"\bcapital\s+cost\b|\bcapex\b", re.I), "Capital Costs"),
    (re.compile(r"\boperating\s+cost\b|\bopex\b", re.I), "Operating Costs"),
    (re.compile(r"\beconomic\s+analysis\b|\beconomics\b|\bfinancial\s+analysis\b", re.I), "Economic Analysis"),
    (re.compile(r"\bsensitivity\b", re.I), "Sensitivity Analysis"),
    (re.compile(r"\brisk\b", re.I), "Risks"),
    (re.compile(r"\benvironmental\b|\bpermitting\b", re.I), "Environmental & Permitting"),
    (re.compile(r"\bconclusion\b|\brecommendation\b", re.I), "Conclusions & Recommendations"),
    (re.compile(r"\breferences?\b|\bbibliography\b", re.I), "References"),
]

# Patterns that identify a line as a section heading
_HEADING_PATTERNS: list[re.Pattern[str]] = [
    # Numbered heading: "1. Introduction", "Section 4 — Geology"
    re.compile(r"^\s*(?:\d+[\.\)\-]?\s+|Section\s+\d+\s*[\-—:]\s*)\S", re.I),
    # ALL CAPS heading (4+ words, not a table row)
    re.compile(r"^\s*[A-Z][A-Z\s\-&/]{10,}\s*$"),
    # Title Case line followed by at least two uppercase words
    re.compile(r"^\s*(?:[A-Z][a-z]+\s+){2,}[A-Z][a-z]*\s*$"),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def split_document_into_sections(
    doc: ParsedDocument,
    *,
    max_chunk_chars: int = DEFAULT_CHUNK_SIZE * 4,
    min_section_chars: int = 200,
) -> list[DocumentSection]:
    """
    Split a ``ParsedDocument`` into named sections.

    Strategy:
    1. Walk through page text, detecting heading lines.
    2. Everything between two headings becomes one section.
    3. Sections larger than *max_chunk_chars* are split further at paragraph
       boundaries.
    4. Sections smaller than *min_section_chars* are merged with the next.

    Parameters
    ----------
    doc:
        A ``ParsedDocument`` from ``parse_pdf``.
    max_chunk_chars:
        Maximum character count per section chunk. Default 16 000 (~4 000 tokens).
    min_section_chars:
        Sections with fewer characters than this are merged into the next section.

    Returns
    -------
    list[DocumentSection]
        Ordered list of sections. Empty documents return an empty list.
    """
    if not doc.pages:
        return []

    # Build a flat list of (page_number, line_text) tuples
    lines_with_pages: list[tuple[int, str]] = []
    for page in doc.pages:
        if page.text:
            for line in page.text.split("\n"):
                lines_with_pages.append((page.page_number, line))

    if not lines_with_pages:
        log.info("No text found in document — returning empty section list")
        return []

    # ---- Detect section boundaries ------------------------------------------
    raw_sections: list[tuple[str, int, list[str]]] = []  # (title, page_start, lines)
    current_title = "Preamble"
    current_page = lines_with_pages[0][0]
    current_lines: list[str] = []

    for page_num, line in lines_with_pages:
        if _is_heading(line):
            # Save what we've accumulated
            raw_sections.append((current_title, current_page, current_lines))
            current_title = _normalise_heading(line)
            current_page = page_num
            current_lines = []
        else:
            current_lines.append(line)

    # Don't forget the last section
    raw_sections.append((current_title, current_page, current_lines))

    # ---- Build DocumentSection objects --------------------------------------
    sections: list[DocumentSection] = []
    chunk_idx = 0

    for raw_title, page_start, section_lines in raw_sections:
        text = "\n".join(section_lines).strip()

        if len(text) < min_section_chars:
            # Merge into next section by passing to next iteration
            if sections:
                # Append to the last section instead
                prev = sections[-1]
                merged_text = prev.text + "\n\n" + text if text else prev.text
                sections[-1] = DocumentSection(
                    title=prev.title,
                    text=merged_text,
                    chunk_index=prev.chunk_index,
                    page_start=prev.page_start,
                    page_end=page_start,
                    source_file=doc.file_name,
                )
            continue

        # Split oversized sections at paragraph boundaries
        sub_chunks = _split_at_paragraphs(text, max_chunk_chars)

        for i, chunk_text in enumerate(sub_chunks):
            title = raw_title if i == 0 else f"{raw_title} (cont.)"
            sections.append(DocumentSection(
                title=title,
                text=chunk_text,
                chunk_index=chunk_idx,
                page_start=page_start,
                source_file=doc.file_name,
            ))
            chunk_idx += 1

    log.info(
        "Document split into %d sections | source=%s",
        len(sections), doc.file_name,
    )
    return sections


def split_text_into_chunks(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    source_file: str = "",
) -> list[DocumentSection]:
    """
    Simple character-based chunker for plain text.

    Used when section detection is not needed (e.g. note files, site visit
    transcripts, or short documents). Produces overlapping chunks to avoid
    losing context at chunk boundaries.

    Parameters
    ----------
    text:
        The text to chunk.
    chunk_size:
        Target chunk size in characters. Default from constants.
    overlap:
        Character overlap between consecutive chunks. Default from constants.
    source_file:
        Source file name to embed in the returned sections.
    """
    if not text.strip():
        return []

    chunks: list[DocumentSection] = []
    start = 0
    idx = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(DocumentSection(
                title=f"Chunk {idx + 1}",
                text=chunk_text,
                chunk_index=idx,
                source_file=source_file,
            ))
        idx += 1
        start += chunk_size - overlap

    return chunks


def find_section(
    sections: list[DocumentSection],
    keyword: str,
) -> list[DocumentSection]:
    """
    Return sections whose title or first 200 characters of text contain *keyword*.
    Case-insensitive.
    """
    kw = keyword.lower()
    return [
        s for s in sections
        if kw in s.title.lower() or kw in s.text[:200].lower()
    ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_heading(line: str) -> bool:
    """Return True if a line looks like a section heading."""
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return False
    if len(stripped) < 4:
        return False
    for pattern in _HEADING_PATTERNS:
        if pattern.match(line):
            return True
    return False


def _normalise_heading(line: str) -> str:
    """
    Strip leading numbering and whitespace from a heading line to
    produce a clean section title.
    """
    stripped = line.strip()
    # Remove leading "1.", "1.2.", "Section 4 —" etc.
    stripped = re.sub(r"^\d+[\.\)\-]?\s*", "", stripped)
    stripped = re.sub(r"^Section\s+\d+\s*[\-—:]\s*", "", stripped, flags=re.I)
    stripped = stripped.strip()

    # Map to known section title if we recognise it
    for pattern, label in _KNOWN_SECTION_TITLES:
        if pattern.search(stripped):
            return label

    return stripped or line.strip()


def _split_at_paragraphs(text: str, max_chars: int) -> list[str]:
    """
    Split *text* into chunks of at most *max_chars* characters, preferring
    paragraph breaks (double newlines) as split points.
    """
    if len(text) <= max_chars:
        return [text]

    paragraphs = re.split(r"\n{2,}", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len > max_chars and current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        # If a single paragraph exceeds max_chars, split it at sentence boundaries
        if para_len > max_chars:
            for sub in _split_at_sentences(para, max_chars):
                chunks.append(sub)
        else:
            current.append(para)
            current_len += para_len

    if current:
        chunks.append("\n\n".join(current))

    return [c for c in chunks if c.strip()]


def _split_at_sentences(text: str, max_chars: int) -> list[str]:
    """Last-resort splitter: break at sentence boundaries."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for s in sentences:
        if len(current) + len(s) > max_chars and current:
            chunks.append(current.strip())
            current = s
        else:
            current = current + " " + s if current else s
    if current:
        chunks.append(current.strip())
    return chunks

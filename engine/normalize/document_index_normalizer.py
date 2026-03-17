"""
Document index normalizer.

Scans parsed document outputs and builds a document manifest Parquet file.
"""

from __future__ import annotations

import json
from pathlib import Path

from engine.core.logging import get_logger
from engine.core.paths import project_normalized
from engine.io.parquet_io import dicts_to_parquet

log = get_logger(__name__)

# Common section heading patterns to detect in extracted text
_SECTION_PATTERNS = [
    "executive summary",
    "introduction",
    "geological setting",
    "mineral resource",
    "mineral reserve",
    "mining method",
    "metallurgy",
    "capital cost",
    "operating cost",
    "economic analysis",
    "sensitivity",
    "risk",
    "recommendation",
    "conclusion",
    "appendix",
]


def _detect_sections(text: str) -> list[str]:
    """Detect approximate sections from extracted text."""
    found: list[str] = []
    text_lower = text.lower()
    for pattern in _SECTION_PATTERNS:
        if pattern in text_lower:
            found.append(pattern.replace(" ", "_"))
    return found


def _count_pages_from_metadata(metadata: dict) -> int | None:
    """Try to extract page count from document metadata."""
    for key in ("page_count", "pages", "num_pages", "total_pages"):
        val = metadata.get(key)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                pass
    return None


def normalise_document_index(project_id: str, run_id: str) -> list[str]:
    """
    Scans normalized/staging/parsed_documents/ for extracted document text.
    Builds a document manifest with: filename, path, page_count,
    extracted_text_length, sections_found.
    Writes to normalized/document_index/document_manifest.parquet.
    Returns list of warnings.
    """
    warnings: list[str] = []
    log.info("Normalising document index for project=%s", project_id)

    norm_root = project_normalized(project_id)
    parsed_docs_dir = norm_root / "staging" / "parsed_documents"

    if not parsed_docs_dir.exists():
        warnings.append(
            "normalized/staging/parsed_documents/ does not exist. "
            "No documents have been parsed yet — document index not built."
        )
        return warnings

    doc_rows: list[dict] = []

    # Scan for text files, JSON metadata, and directories
    text_files = list(parsed_docs_dir.rglob("*.txt")) + list(parsed_docs_dir.rglob("*.json"))
    if not text_files:
        warnings.append(
            "No parsed document files found in normalized/staging/parsed_documents/. "
            "Run document ingestion first."
        )
        return warnings

    # Group by stem to pair text + metadata files
    processed_stems: set[str] = set()

    for file_path in sorted(text_files):
        stem = file_path.stem
        if stem in processed_stems:
            continue
        processed_stems.add(stem)

        page_count: int | None = None
        text_length: int = 0
        sections_found: list[str] = []
        original_filename = file_path.name

        if file_path.suffix == ".json":
            # JSON file may contain metadata + text
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                original_filename = data.get("filename") or data.get("source_file") or file_path.name
                page_count = _count_pages_from_metadata(data)

                text = data.get("text") or data.get("content") or data.get("extracted_text") or ""
                text_length = len(str(text))
                sections_found = _detect_sections(str(text))

            except Exception as e:
                warnings.append(f"Could not parse JSON document file {file_path.name}: {e}")
                continue

        elif file_path.suffix == ".txt":
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
                text_length = len(text)
                sections_found = _detect_sections(text)
                original_filename = file_path.name

                # Look for companion metadata JSON
                meta_path = file_path.with_suffix(".meta.json")
                if meta_path.exists():
                    try:
                        with meta_path.open("r", encoding="utf-8") as f:
                            meta = json.load(f)
                        page_count = _count_pages_from_metadata(meta)
                        original_filename = meta.get("filename") or original_filename
                    except Exception:
                        pass

            except Exception as e:
                warnings.append(f"Could not read text file {file_path.name}: {e}")
                continue

        # Build relative path from norm_root
        try:
            rel_path = str(file_path.relative_to(norm_root))
        except ValueError:
            rel_path = str(file_path)

        doc_rows.append({
            "filename": original_filename,
            "path": rel_path,
            "page_count": page_count,
            "extracted_text_length": text_length,
            "sections_found": ", ".join(sections_found) if sections_found else "",
            "section_count": len(sections_found),
        })

    if not doc_rows:
        warnings.append("No document entries could be built from parsed_documents/.")
        return warnings

    # Write output
    doc_index_dir = norm_root / "document_index"
    doc_index_dir.mkdir(parents=True, exist_ok=True)
    dicts_to_parquet(doc_rows, doc_index_dir / "document_manifest.parquet")
    log.info("Written %d document entries to document_manifest.parquet", len(doc_rows))

    # Warn if no pages detected
    missing_pages = sum(1 for r in doc_rows if r["page_count"] is None)
    if missing_pages > 0:
        warnings.append(
            f"{missing_pages} document(s) have no page count recorded in metadata."
        )

    log.info("Document index normalisation complete | %d warnings", len(warnings))
    return warnings

"""
Document ingest pipeline.

Orchestrates the full lifecycle of ingesting a document (PDF, XLSX, DOCX)
into a project:

  1. Check the file is not already ingested (by SHA-256 hash)
  2. Route the file to the correct parser (PDF → parse_pdf, XLSX → parse_xlsx)
  3. Run table extraction and classification
  4. Split text into sections for LLM processing
  5. Write parsed artefacts to the project staging area
  6. Register the file in the source registry via the dispatcher

All parsed output is written under:
    <project>/normalized/staging/

  extracted_tables/       — JSON table records from parse_pdf / parse_xlsx
  entity_extraction/      — section text ready for LLM extraction

The ingest step does NOT call the LLM. It only makes the document machine-
readable. LLM extraction is a separate step (``mip analyze``).

Supported formats
-----------------
- .pdf   — via pdfplumber (parse_pdf)
- .xlsx  — via openpyxl (parse_xlsx)
- .xls   — via openpyxl read-only mode
- .docx  — plain text extraction via python-docx (if available), else skip
- .txt   — direct read
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.core.enums import ProjectStatus
from engine.core.hashing import hash_file
from engine.core.ids import run_id as make_run_id
from engine.core.logging import get_logger
from engine.core.manifests import write_json
from engine.core.paths import project_normalized, project_raw, run_root
from engine.ingest.dispatcher import ingest_file
from engine.io.file_registry import is_already_ingested, load_registry, save_registry
from engine.parsing.documents.extract_tables import (
    classify_tables,
    get_high_value_tables,
    tables_to_markdown,
)
from engine.parsing.documents.split_sections import split_document_into_sections, split_text_into_chunks
from engine.project.project_manifest import update_project_metadata
from engine.runs.run_manager import _read_manifest

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

@dataclass
class DocumentIngestResult:
    """Result of ingesting a single document."""
    project_id: str
    file_path: str
    file_name: str
    source_id: str | None = None
    category: str = "unknown"
    status: str = "pending"          # "ok", "skipped", "failed"
    parser_used: str = ""
    page_count: int = 0
    table_count: int = 0
    high_value_table_count: int = 0
    section_count: int = 0
    word_count: int = 0
    scanned_page_count: int = 0
    staging_files_written: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    ingested_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "file_name": self.file_name,
            "source_id": self.source_id,
            "category": self.category,
            "status": self.status,
            "parser_used": self.parser_used,
            "page_count": self.page_count,
            "table_count": self.table_count,
            "high_value_table_count": self.high_value_table_count,
            "section_count": self.section_count,
            "word_count": self.word_count,
            "scanned_page_count": self.scanned_page_count,
            "staging_files_written": self.staging_files_written,
            "warnings": self.warnings,
            "error": self.error,
            "ingested_at": self.ingested_at,
        }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def ingest_document(
    project_id: str,
    file_path: Path | str,
    run_id: str | None = None,
    *,
    force: bool = False,
    extract_tables: bool = True,
    split_sections: bool = True,
    max_pages: int | None = None,
) -> DocumentIngestResult:
    """
    Ingest a single document into a project.

    Parameters
    ----------
    project_id:
        Target project identifier.
    file_path:
        Absolute path to the document to ingest. The file may live anywhere
        on the filesystem — it does not need to be inside the project's
        raw/ directory already (it will be registered by its content hash).
    run_id:
        Run ID to associate with this ingest. Generated if not provided.
    force:
        Re-ingest even if the file hash is already in the registry.
    extract_tables:
        Whether to run table detection and classification.
    split_sections:
        Whether to split the document into sections for LLM input.
    max_pages:
        Only parse the first N pages (useful for previewing large PDFs).

    Returns
    -------
    DocumentIngestResult
    """
    file_path = Path(file_path).resolve()
    run_id = run_id or make_run_id(project_id)

    result = DocumentIngestResult(
        project_id=project_id,
        file_path=str(file_path),
        file_name=file_path.name,
    )

    # ---- Guard: file exists -------------------------------------------------
    if not file_path.exists():
        result.status = "failed"
        result.error = f"File not found: {file_path}"
        log.error("Document ingest failed — file not found: %s", file_path)
        return result

    # ---- Guard: already ingested --------------------------------------------
    if not force and is_already_ingested(project_id, file_path):
        result.status = "skipped"
        result.error = "Already ingested (hash match). Use force=True to re-ingest."
        log.info("Skipping already-ingested document: %s", file_path.name)
        return result

    suffix = file_path.suffix.lower()
    log.info("Ingesting document: %s (%s)", file_path.name, suffix)

    # ---- Register the file in the source registry ---------------------------
    reg_result = ingest_file(project_id, file_path, run_id)
    if reg_result["status"] != "ingested":
        result.status = "failed"
        result.error = reg_result.get("error", "Registration failed")
        return result

    entry = reg_result["entry"]
    result.source_id = entry.source_id
    result.category = entry.category

    # Persist the updated registry immediately so it's available to downstream
    existing = load_registry(project_id)
    # Remove any prior entry with same source_id (idempotent re-ingest with force)
    others = [e for e in existing if e.source_id != entry.source_id]
    save_registry(project_id, others + [entry])

    # ---- Route to parser ----------------------------------------------------
    try:
        if suffix == ".pdf":
            result = _ingest_pdf(
                project_id, file_path, run_id, result,
                extract_tables=extract_tables,
                split_sections=split_sections,
                max_pages=max_pages,
            )
        elif suffix in (".xlsx", ".xls"):
            result = _ingest_xlsx(
                project_id, file_path, run_id, result,
                split_sections=split_sections,
            )
        elif suffix in (".txt", ".md"):
            result = _ingest_text(
                project_id, file_path, run_id, result,
                split_sections=split_sections,
            )
        elif suffix == ".docx":
            result = _ingest_docx(
                project_id, file_path, run_id, result,
                split_sections=split_sections,
            )
        else:
            # Unsupported format — registered but not parsed
            result.status = "ok"
            result.parser_used = "none"
            result.warnings.append(
                f"File format '{suffix}' is registered but no parser is available yet. "
                "The file is in the source registry and will be available for manual review."
            )
            return result

    except Exception as exc:
        result.status = "failed"
        result.error = f"{type(exc).__name__}: {exc}"
        log.error("Document ingest failed for %s: %s", file_path.name, exc, exc_info=True)
        return result

    # ---- Update project metadata --------------------------------------------
    update_project_metadata(
        project_id,
        last_ingested_at=datetime.now(timezone.utc).isoformat(),
        status=ProjectStatus.INGESTING.value,
    )

    result.status = "ok"
    log.info(
        "Document ingested | file=%s pages=%d tables=%d sections=%d words=%d",
        file_path.name,
        result.page_count,
        result.table_count,
        result.section_count,
        result.word_count,
    )
    return result


# ---------------------------------------------------------------------------
# Per-format ingest handlers
# ---------------------------------------------------------------------------

def _ingest_pdf(
    project_id: str,
    file_path: Path,
    run_id: str,
    result: DocumentIngestResult,
    *,
    extract_tables: bool,
    split_sections: bool,
    max_pages: int | None,
) -> DocumentIngestResult:
    from engine.parsing.documents.parse_pdf import parse_pdf

    doc = parse_pdf(file_path, extract_tables=extract_tables, max_pages=max_pages)
    result.parser_used = "pdfplumber"
    result.page_count = doc.page_count
    result.word_count = len(doc.full_text.split()) if doc.full_text else 0
    result.scanned_page_count = doc.scanned_page_count
    result.warnings.extend(doc.warnings)

    staging_dir = _staging_dir(project_id)

    # ---- Tables ----
    if extract_tables and doc.get_all_tables():
        all_tables = doc.get_all_tables()
        result.table_count = len(all_tables)

        high_value = get_high_value_tables(all_tables, min_score=4)
        result.high_value_table_count = len(high_value)

        if high_value:
            tables_path = staging_dir / "extracted_tables" / f"{file_path.stem}_tables.json"
            tables_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "source_file": file_path.name,
                "source_id": result.source_id,
                "run_id": run_id,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "table_count": len(high_value),
                "tables": [t.to_dict() for t in high_value],
            }
            write_json(tables_path, payload)
            result.staging_files_written.append(str(tables_path))

            # Also write a Markdown version (easier to feed to LLM)
            md_path = staging_dir / "extracted_tables" / f"{file_path.stem}_tables.md"
            md_path.write_text(
                f"# Tables from {file_path.name}\n\n" + tables_to_markdown(high_value),
                encoding="utf-8",
            )
            result.staging_files_written.append(str(md_path))

    # ---- Sections ----
    if split_sections and doc.full_text:
        sections = split_document_into_sections(doc)
        result.section_count = len(sections)

        if sections:
            sections_path = (
                staging_dir / "entity_extraction" / "project_facts"
                / f"{file_path.stem}_sections.json"
            )
            sections_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "source_file": file_path.name,
                "source_id": result.source_id,
                "run_id": run_id,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "section_count": len(sections),
                "sections": [s.to_dict() for s in sections],
            }
            write_json(sections_path, payload)
            result.staging_files_written.append(str(sections_path))

    return result


def _ingest_xlsx(
    project_id: str,
    file_path: Path,
    run_id: str,
    result: DocumentIngestResult,
    *,
    split_sections: bool,
) -> DocumentIngestResult:
    from engine.parsing.documents.parse_xlsx import parse_xlsx

    wb = parse_xlsx(file_path)
    result.parser_used = "openpyxl"
    result.warnings.extend(wb.warnings)

    staging_dir = _staging_dir(project_id)
    sheets_dir = staging_dir / "extracted_tables" / "spreadsheets"
    sheets_dir.mkdir(parents=True, exist_ok=True)

    non_empty = wb.get_non_empty_sheets()
    result.table_count = len(non_empty)

    # Write each non-empty sheet as JSON
    for sheet in non_empty:
        sheet_path = sheets_dir / f"{file_path.stem}_{sheet.sheet_name}.json"
        payload = {
            "source_file": file_path.name,
            "source_id": result.source_id,
            "sheet_name": sheet.sheet_name,
            "run_id": run_id,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            **sheet.to_summary_dict(),
            "data": sheet.to_dicts(),
        }
        write_json(sheet_path, payload)
        result.staging_files_written.append(str(sheet_path))
        result.word_count += sheet.row_count

    return result


def _ingest_text(
    project_id: str,
    file_path: Path,
    run_id: str,
    result: DocumentIngestResult,
    *,
    split_sections: bool,
) -> DocumentIngestResult:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    result.parser_used = "text"
    result.word_count = len(text.split())

    if split_sections:
        sections = split_text_into_chunks(text, source_file=file_path.name)
        result.section_count = len(sections)
        _write_sections(project_id, file_path, run_id, result, sections)

    return result


def _ingest_docx(
    project_id: str,
    file_path: Path,
    run_id: str,
    result: DocumentIngestResult,
    *,
    split_sections: bool,
) -> DocumentIngestResult:
    """Extract plain text from DOCX using python-docx if available."""
    try:
        import docx  # python-docx
        doc = docx.Document(str(file_path))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        result.parser_used = "python-docx"
    except ImportError:
        result.warnings.append(
            "python-docx is not installed. DOCX text could not be extracted. "
            "Run: pip install python-docx"
        )
        result.parser_used = "none"
        return result
    except Exception as exc:
        result.warnings.append(f"DOCX parse error: {exc}")
        result.parser_used = "none"
        return result

    result.word_count = len(text.split())

    if split_sections and text:
        sections = split_text_into_chunks(text, source_file=file_path.name)
        result.section_count = len(sections)
        _write_sections(project_id, file_path, run_id, result, sections)

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _staging_dir(project_id: str) -> Path:
    return project_normalized(project_id) / "staging"


def _write_sections(
    project_id: str,
    file_path: Path,
    run_id: str,
    result: DocumentIngestResult,
    sections: list,
) -> None:
    sections_path = (
        _staging_dir(project_id)
        / "entity_extraction"
        / "project_facts"
        / f"{file_path.stem}_sections.json"
    )
    sections_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_file": file_path.name,
        "source_id": result.source_id,
        "run_id": run_id,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "section_count": len(sections),
        "sections": [s.to_dict() for s in sections],
    }
    write_json(sections_path, payload)
    result.staging_files_written.append(str(sections_path))

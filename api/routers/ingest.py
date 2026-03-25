"""
Ingest router — file upload and library management.

Endpoints:
  POST /projects/{project_id}/files    upload one or more files
  GET  /projects/{project_id}/files    list all files in the project library
  DELETE /projects/{project_id}/files/{filename}  remove a single file
"""

from __future__ import annotations

import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from api.models.ingest_request import FileList, FileRecord, IngestResponse
from engine.core.paths import project_root
from engine.ingest.url_fetcher import fetch_url_as_text

router = APIRouter(prefix="/projects/{project_id}/files", tags=["ingest"])

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv",
    ".txt", ".md", ".png", ".jpg", ".jpeg", ".tiff",
    ".dxf", ".dwg",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _registry_path(project_id: str) -> Path:
    return project_root(project_id) / "normalized" / "metadata" / "file_registry.json"


def _load_registry(project_id: str) -> dict[str, dict]:
    path = _registry_path(project_id)
    if not path.exists():
        return {}
    with path.open() as f:
        return json.load(f)


def _save_registry(project_id: str, registry: dict[str, dict]) -> None:
    path = _registry_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(registry, f, indent=2)


def _project_exists(project_id: str) -> None:
    if not project_root(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=IngestResponse, status_code=202)
async def upload_files(
    project_id: str,
    files: list[UploadFile] = File(...),
) -> IngestResponse:
    """
    Upload one or more files into the project's raw document library.
    Accepted formats: PDF, DOCX, XLSX, CSV, TXT, PNG/JPG/TIFF, DXF/DWG.
    Files are saved immediately; analysis is triggered separately via /analyze.
    """
    _project_exists(project_id)
    dest_dir = project_root(project_id) / "raw" / "documents"
    dest_dir.mkdir(parents=True, exist_ok=True)

    registry = _load_registry(project_id)
    queued: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    for upload in files:
        filename = Path(upload.filename).name
        suffix = Path(filename).suffix.lower()

        if suffix not in ALLOWED_EXTENSIONS:
            skipped.append(filename)
            continue

        dest_file = dest_dir / filename
        try:
            content = await upload.read()
            dest_file.write_bytes(content)
            mime = upload.content_type or mimetypes.guess_type(filename)[0]
            registry[filename] = {
                "filename": filename,
                "path": str(dest_file),
                "size_bytes": len(content),
                "mime_type": mime,
                "ingested": False,
                "ingested_at": None,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }
            queued.append(filename)
        except Exception as exc:
            errors.append(f"{filename}: {exc}")

    _save_registry(project_id, registry)
    return IngestResponse(
        project_id=project_id,
        queued=queued,
        skipped=skipped,
        errors=errors,
    )


@router.get("", response_model=FileList)
def list_files(project_id: str) -> FileList:
    """Return the full file library for this project."""
    _project_exists(project_id)
    registry = _load_registry(project_id)
    records = [FileRecord(**v) for v in registry.values()]
    return FileList(project_id=project_id, files=records, total=len(records))


@router.get("/{filename}/content")
def serve_file_content(project_id: str, filename: str) -> Response:
    """Serve a raw project file (images, renders) by filename for report display."""
    _project_exists(project_id)
    # Block path traversal
    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Check raw/documents first, then raw/renders (CAD renders)
    raw_dir = project_root(project_id) / "raw" / "documents"
    renders_dir = project_root(project_id) / "raw" / "renders"

    file_path = raw_dir / filename
    if not file_path.exists():
        file_path = renders_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return Response(content=file_path.read_bytes(), media_type=mime)


@router.delete("/{filename}", status_code=204)
def delete_file(project_id: str, filename: str) -> None:
    """Remove a file from the project library."""
    _project_exists(project_id)
    dest_dir = project_root(project_id) / "raw" / "documents"
    dest_file = dest_dir / filename
    if not dest_file.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
    dest_file.unlink()
    registry = _load_registry(project_id)
    registry.pop(filename, None)
    _save_registry(project_id, registry)


# ---------------------------------------------------------------------------
# URL ingestion — separate router so the path is /projects/{id}/ingest/url
# ---------------------------------------------------------------------------

url_router = APIRouter(prefix="/projects/{project_id}/ingest", tags=["ingest"])


class UrlIngestRequest(BaseModel):
    url: str


class UrlIngestResponse(BaseModel):
    project_id: str
    filename: str
    url: str
    size_bytes: int
    status: str
    error: str | None = None


@url_router.post("/url", response_model=UrlIngestResponse, status_code=202)
def ingest_url(project_id: str, body: UrlIngestRequest) -> UrlIngestResponse:
    """
    Fetch a public URL (press release, news article, company page) and save
    it as a plain-text source document in the project library.

    The page is cleaned of navigation, ads, and scripts — only the main
    readable content is kept. Triggers no analysis; run /analyze separately.
    """
    _project_exists(project_id)
    dest_dir = project_root(project_id) / "raw" / "documents"
    dest_dir.mkdir(parents=True, exist_ok=True)

    url = str(body.url).strip()

    try:
        text, filename = fetch_url_as_text(url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {exc}")

    # If a file with this name already exists, append a counter
    dest_file = dest_dir / filename
    if dest_file.exists():
        stem = Path(filename).stem
        counter = 2
        while dest_file.exists():
            dest_file = dest_dir / f"{stem}_{counter}.txt"
            counter += 1
        filename = dest_file.name

    dest_file.write_text(text, encoding="utf-8")
    size = len(text.encode("utf-8"))

    registry = _load_registry(project_id)
    registry[filename] = {
        "filename": filename,
        "path": str(dest_file),
        "size_bytes": size,
        "mime_type": "text/plain",
        "source_url": url,
        "ingested": False,
        "ingested_at": None,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_registry(project_id, registry)

    return UrlIngestResponse(
        project_id=project_id,
        filename=filename,
        url=url,
        size_bytes=size,
        status="queued",
    )


# ---------------------------------------------------------------------------
# EDGAR / SEDAR import — separate router (prefix: /edgar or /projects/{id})
# ---------------------------------------------------------------------------

edgar_router = APIRouter(tags=["filing-import"])


class EdgarCompany(BaseModel):
    cik: str
    name: str
    ticker: str
    exchange: str


class EdgarFiling(BaseModel):
    accession_number: str
    form_type: str
    filing_date: str
    report_date: str
    primary_document: str
    primary_doc_description: str
    filing_url: str
    index_url: str
    cik: str


class EdgarDocument(BaseModel):
    filename: str
    description: str
    document_type: str
    size_bytes: int
    url: str


class FilingImportRequest(BaseModel):
    url: str
    filename: str | None = None   # override auto-detected name
    source: str = "edgar"          # "edgar" | "sedar"


class FilingImportResponse(BaseModel):
    project_id: str
    filename: str
    url: str
    size_bytes: int
    source: str
    status: str
    error: str | None = None


@edgar_router.get("/edgar/search")
def edgar_search(q: str, limit: int = 10) -> dict:
    """
    Search for companies on SEC EDGAR by name or ticker.
    Returns a list of matching companies with CIK numbers.
    """
    from engine.ingest.edgar_client import search_companies
    try:
        results = search_companies(q.strip(), max_results=min(limit, 25))
        return {"query": q, "results": results, "total": len(results)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"EDGAR search failed: {exc}")


@edgar_router.get("/edgar/filings")
def edgar_filings(
    cik: str,
    forms: str = "40-F,10-K,20-F,6-K,8-K",
    limit: int = 20,
    after: str | None = None,
) -> dict:
    """
    List filings for a given CIK.
    forms: comma-separated form types (default: 40-F,10-K,20-F,6-K,8-K)
    after: only return filings after this date (YYYY-MM-DD)
    """
    from engine.ingest.edgar_client import list_filings, get_company_facts
    form_list = [f.strip() for f in forms.split(",") if f.strip()]
    try:
        filings = list_filings(cik, form_types=form_list, max_results=min(limit, 50), after_date=after)
        facts = {}
        try:
            facts = get_company_facts(cik)
        except Exception:
            pass
        return {
            "cik": cik,
            "company": facts.get("name", ""),
            "ticker": facts.get("tickers", [""])[0] if facts.get("tickers") else "",
            "filings": filings,
            "total": len(filings),
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@edgar_router.get("/edgar/filings/{cik}/{accession}/documents")
def edgar_filing_documents(cik: str, accession: str) -> dict:
    """List all documents inside a specific EDGAR filing."""
    from engine.ingest.edgar_client import get_filing_index
    try:
        docs = get_filing_index(cik, accession)
        return {
            "cik": cik,
            "accession_number": accession,
            "documents": docs,
            "total": len(docs),
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@edgar_router.post("/projects/{project_id}/files/import-filing", response_model=FilingImportResponse, status_code=202)
def import_filing_document(project_id: str, body: FilingImportRequest) -> FilingImportResponse:
    """
    Download a document from EDGAR or SEDAR+ and save it into the project's
    raw/documents folder.

    Accepts:
    - Any EDGAR document URL (www.sec.gov/Archives/...)
    - Any SEDAR+ document URL (sedarplus.ca/...)
    """
    _project_exists(project_id)
    dest_dir = project_root(project_id) / "raw" / "documents"
    dest_dir.mkdir(parents=True, exist_ok=True)

    url = body.url.strip()
    source = body.source

    # Determine source from URL if not explicitly given
    from engine.ingest.sedar_client import is_sedar_url
    if is_sedar_url(url):
        source = "sedar"
    elif "sec.gov" in url.lower():
        source = "edgar"

    try:
        if source == "sedar":
            from engine.ingest.sedar_client import fetch_sedar_document
            raw_bytes, auto_name = fetch_sedar_document(url)
        else:
            from engine.ingest.edgar_client import download_edgar_document
            raw_bytes = download_edgar_document(url)
            # Infer filename from URL
            path_part = url.split("?")[0].rsplit("/", 1)[-1]
            auto_name = path_part or "edgar_document.pdf"

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Download failed: {exc}")

    # Use caller-supplied name or auto-detected
    filename = body.filename or auto_name
    filename = Path(filename).name   # strip any path components

    # Validate extension
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS and suffix not in {".html", ".htm"}:
        # Accept HTML from EDGAR even though it's not in the standard list
        if suffix not in {".html", ".htm"}:
            # Re-derive from content
            if raw_bytes[:4] == b"%PDF":
                filename = Path(filename).stem + ".pdf"
            elif raw_bytes[:2] in (b"PK", ):
                filename = Path(filename).stem + ".xlsx"

    # Dedup filename
    dest_file = dest_dir / filename
    if dest_file.exists():
        stem = Path(filename).stem
        ext  = Path(filename).suffix
        counter = 2
        while dest_file.exists():
            dest_file = dest_dir / f"{stem}_{counter}{ext}"
            counter += 1
        filename = dest_file.name

    dest_file.write_bytes(raw_bytes)
    size = len(raw_bytes)

    registry = _load_registry(project_id)
    registry[filename] = {
        "filename":    filename,
        "path":        str(dest_file),
        "size_bytes":  size,
        "mime_type":   _mime_for(filename),
        "source_url":  url,
        "source":      source,
        "ingested":    False,
        "ingested_at": None,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_registry(project_id, registry)

    return FilingImportResponse(
        project_id=project_id,
        filename=filename,
        url=url,
        size_bytes=size,
        source=source,
        status="queued",
    )


@edgar_router.get("/sedar/search-link")
def sedar_search_link(company: str, form_type: str | None = None) -> dict:
    """
    Return a SEDAR+ search deep-link URL for the given company name.
    SEDAR+ has no public API — this provides a URL to open manually.
    """
    from engine.ingest.sedar_client import get_sedar_search_url
    url = get_sedar_search_url(company, form_type)
    return {
        "company": company,
        "form_type": form_type,
        "search_url": url,
        "note": (
            "SEDAR+ does not provide a public API. "
            "Open this URL in your browser to find filings, "
            "then paste the document download URL into the import field."
        ),
    }


def _mime_for(filename: str) -> str:
    import mimetypes
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"

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

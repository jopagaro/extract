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

from api.models.ingest_request import FileList, FileRecord, IngestResponse
from engine.core.paths import project_root

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

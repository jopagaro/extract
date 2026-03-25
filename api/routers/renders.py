"""
Renders router — serves OMF-derived PNG figures for inline report display.

Endpoints:
  GET /projects/{project_id}/renders/{filename}
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from engine.core.paths import project_root

router = APIRouter(prefix="/projects/{project_id}/renders", tags=["renders"])

_ALLOWED_EXTS = {".png", ".jpg", ".jpeg"}


@router.get("/{filename}")
def get_render(project_id: str, filename: str) -> FileResponse:
    """Serve a rendered figure PNG from normalized/renders/."""
    # Safety: no path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = Path(filename)
    if path.suffix.lower() not in _ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail="Only PNG/JPG renders are served here")

    render_path = project_root(project_id) / "normalized" / "renders" / filename
    if not render_path.exists():
        raise HTTPException(status_code=404, detail=f"Render '{filename}' not found")

    media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(str(render_path), media_type=media_type)

"""
Notes router — analyst annotations on projects.

Endpoints:
  GET    /projects/{project_id}/notes              list all notes
  POST   /projects/{project_id}/notes              create a note
  PATCH  /projects/{project_id}/notes/{note_id}   update a note
  DELETE /projects/{project_id}/notes/{note_id}   delete a note
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.core.paths import project_root

router = APIRouter(prefix="/projects/{project_id}/notes", tags=["notes"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _notes_path(project_id: str) -> Path:
    return project_root(project_id) / "normalized" / "metadata" / "notes.json"


def _load_notes(project_id: str) -> list[dict]:
    path = _notes_path(project_id)
    if not path.exists():
        return []
    with path.open() as f:
        return json.load(f)


def _save_notes(project_id: str, notes: list[dict]) -> None:
    path = _notes_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(notes, f, indent=2)


def _project_exists(project_id: str) -> None:
    if not project_root(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class NoteCreate(BaseModel):
    content: str
    tag: str | None = None  # e.g. "red flag", "follow up", "assumption"


class NoteUpdate(BaseModel):
    content: str | None = None
    tag: str | None = None


class Note(BaseModel):
    note_id: str
    content: str
    tag: str | None = None
    created_at: str
    updated_at: str


class NoteList(BaseModel):
    project_id: str
    notes: list[Note]
    total: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=NoteList)
def list_notes(project_id: str) -> NoteList:
    """Return all analyst notes for this project, newest first."""
    _project_exists(project_id)
    notes = _load_notes(project_id)
    # Sort newest first
    notes_sorted = sorted(notes, key=lambda n: n["created_at"], reverse=True)
    return NoteList(
        project_id=project_id,
        notes=[Note(**n) for n in notes_sorted],
        total=len(notes_sorted),
    )


@router.post("", response_model=Note, status_code=201)
def create_note(project_id: str, body: NoteCreate) -> Note:
    """Add a new analyst note to this project."""
    _project_exists(project_id)
    if not body.content.strip():
        raise HTTPException(status_code=422, detail="Note content cannot be empty")

    now = datetime.now(timezone.utc).isoformat()
    note = {
        "note_id": str(uuid.uuid4()),
        "content": body.content.strip(),
        "tag": body.tag,
        "created_at": now,
        "updated_at": now,
    }

    notes = _load_notes(project_id)
    notes.append(note)
    _save_notes(project_id, notes)
    return Note(**note)


@router.patch("/{note_id}", response_model=Note)
def update_note(project_id: str, note_id: str, body: NoteUpdate) -> Note:
    """Edit the content or tag of an existing note."""
    _project_exists(project_id)
    notes = _load_notes(project_id)
    for note in notes:
        if note["note_id"] == note_id:
            if body.content is not None:
                note["content"] = body.content.strip()
            if body.tag is not None:
                note["tag"] = body.tag
            note["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_notes(project_id, notes)
            return Note(**note)
    raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found")


@router.delete("/{note_id}", status_code=204)
def delete_note(project_id: str, note_id: str) -> None:
    """Delete a note permanently."""
    _project_exists(project_id)
    notes = _load_notes(project_id)
    filtered = [n for n in notes if n["note_id"] != note_id]
    if len(filtered) == len(notes):
        raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found")
    _save_notes(project_id, filtered)

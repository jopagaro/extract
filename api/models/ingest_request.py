"""Pydantic models for ingest and file resources."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IngestOptions(BaseModel):
    no_tables: bool = False
    no_sections: bool = False
    max_pages: int | None = Field(None, ge=1, le=2000)


class FileRecord(BaseModel):
    filename: str
    path: str
    size_bytes: int
    mime_type: str | None = None
    ingested: bool = False
    ingested_at: str | None = None
    page_count: int | None = None
    error: str | None = None


class FileList(BaseModel):
    project_id: str
    files: list[FileRecord]
    total: int


class IngestResponse(BaseModel):
    project_id: str
    queued: list[str]
    skipped: list[str]
    errors: list[str]

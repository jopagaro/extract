"""Pydantic models for project resources."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, description="Human-readable project name")
    description: str | None = Field(None, max_length=500)
    commodity: str | None = Field(None, description="Primary commodity, e.g. 'gold', 'copper'")
    study_type: Literal["PEA", "PFS", "FS", "scoping", "other"] = "PEA"


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    ticker: str | None = Field(None, max_length=12, description="Exchange ticker symbol, e.g. ABX, NEM")


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    commodity: str | None = None
    study_type: str
    ticker: str | None = None
    created_at: str
    status: Literal["empty", "ingested", "analyzed", "error"] = "empty"
    file_count: int = 0
    run_count: int = 0


class ProjectList(BaseModel):
    projects: list[ProjectResponse]
    total: int

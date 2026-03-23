"""
Activation router — validates a license key against the Extract license server
and persists the result to user settings.

Endpoint:
  POST /activate   { "license_key": "EXTR-...", "machine_id": "..." }
"""
from __future__ import annotations

import hashlib
import os
import platform
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.routers.settings import AppSettings, _load, _save

router = APIRouter(tags=["activate"])

# URL of your deployed license server — set via env var in production.
# Defaults to localhost for local development/testing.
LICENSE_SERVER_URL = os.environ.get(
    "LICENSE_SERVER_URL",
    "https://license.yourdomain.com",   # ← replace with your Railway URL
)


class ActivateRequest(BaseModel):
    license_key: str


class ActivateResponse(BaseModel):
    success: bool
    message: str


def _machine_id() -> str:
    """Return a stable per-machine fingerprint stored in settings.

    We use a random UUID that's generated once and persisted, rather than
    reading hardware IDs (which require elevated permissions on some OSes).
    """
    data = _load()
    mid = data.get("_machine_id")
    if not mid:
        mid = str(uuid.uuid4())
        data["_machine_id"] = mid
        _save(data)
    return mid


@router.post("/activate", response_model=ActivateResponse)
def activate(body: ActivateRequest) -> ActivateResponse:
    key = body.license_key.strip().upper()
    if not key:
        raise HTTPException(status_code=400, detail="License key is required.")

    mid = _machine_id()

    try:
        resp = httpx.post(
            f"{LICENSE_SERVER_URL}/activate",
            json={"license_key": key, "machine_id": mid},
            timeout=10.0,
        )
        result = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail="Could not reach the license server. Check your internet connection.",
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"License server error: {exc}")

    if result.get("valid"):
        # Persist the verified license to settings
        data = _load()
        data["license_key"]      = key
        data["license_verified"] = True
        _save(data)
        return ActivateResponse(success=True, message="License activated successfully.")

    return ActivateResponse(
        success=False,
        message=result.get("message", "Invalid license key."),
    )

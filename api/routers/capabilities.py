"""
Capabilities router — tells the frontend which feature packs are installed.
"""

from fastapi import APIRouter
from engine.core.capabilities import get_capabilities

router = APIRouter(tags=["meta"])


@router.get("/capabilities")
def capabilities() -> dict:
    """Return which optional feature packs are available on this installation."""
    return get_capabilities()

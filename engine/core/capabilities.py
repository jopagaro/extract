"""
Runtime capability detection.

Checks which optional feature packs are installed so the API and UI
can adapt without crashing. Import is always safe — no heavy deps here.
"""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_capabilities() -> dict:
    """
    Detect installed feature packs.

    Cached after the first call — pack presence doesn't change at runtime.
    """
    cad_pack = _probe("OCP") and _probe("cadvert")
    omf_pack = _probe("pyvista") and _probe("vtkmodules")

    base_formats = [
        "pdf", "docx", "doc", "xlsx", "xls", "csv", "txt", "md",
        "png", "jpg", "jpeg", "tiff",
        "dxf", "dwg",   # ezdxf — lightweight, always in base
    ]
    cad_formats = ["step", "stp", "iges", "igs", "brep"]
    geo_formats = ["omf", "vtk", "vtu", "obj", "stl"]

    supported = list(base_formats)
    if cad_pack:
        supported += cad_formats
    if omf_pack:
        supported += geo_formats

    return {
        "base": True,
        "cad_pack": cad_pack,
        "omf_pack": omf_pack,
        "supported_formats": supported,
        "locked_formats": {
            "cad": cad_formats if not cad_pack else [],
            "geo": geo_formats if not omf_pack else [],
        },
        "upgrade_info": {
            "cad": {
                "name": "CAD Analysis Pack",
                "description": "Analyse 3D solid models (STEP, IGES) with exact geometry — slope angles, pit depth, bench widths, volumes.",
                "formats": cad_formats,
            },
            "geo": {
                "name": "Geology 3D Pack",
                "description": "Visualise block models, grade shells, and 3D geological data (OMF, VTK, OBJ, STL).",
                "formats": geo_formats,
            },
        },
    }


def _probe(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False

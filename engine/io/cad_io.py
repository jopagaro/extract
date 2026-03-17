"""
CAD file I/O utilities.

Supports DXF, DWG, OBJ, STL, GLTF, GLB, OMF, and related 3-D formats
used in mine planning and geological modelling.

Optional dependencies:
- ezdxf  — required for DXF operations.
           Install: pip install ezdxf
- trimesh — optional for GLTF/GLB geometry inspection.
           Install: pip install trimesh

Both imports are wrapped in try/except so this module can be imported
in environments without these packages installed; functions raise a clear
ImportError with instructions when called.

DWG format:
    The .dwg format is a proprietary Autodesk binary format. Converting
    DWG to DXF requires the ODA File Converter (free, external tool):
        https://www.opendesign.com/guestfiles/oda_file_converter
    Once installed, convert with:
        ODAFileConverter <input_dir> <output_dir> ACAD2018 DXF 1 1
    The read_dwg_* functions below raise NotImplementedError with these
    instructions rather than silently failing.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Optional dependency detection
# ---------------------------------------------------------------------------

try:
    import ezdxf  # noqa: F401
    _EZDXF_AVAILABLE = True
except ImportError:
    _EZDXF_AVAILABLE = False

try:
    import trimesh  # noqa: F401
    _TRIMESH_AVAILABLE = True
except ImportError:
    _TRIMESH_AVAILABLE = False

_EZDXF_INSTALL_MSG = (
    "ezdxf is required for DXF operations but is not installed.\n"
    "Install it with:  pip install ezdxf"
)

_TRIMESH_INSTALL_MSG = (
    "trimesh is optional for GLTF/GLB geometry inspection.\n"
    "Install it with:  pip install trimesh"
)


def _require_ezdxf() -> None:
    if not _EZDXF_AVAILABLE:
        raise ImportError(_EZDXF_INSTALL_MSG)


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

_EXTENSION_MAP: dict[str, str] = {
    ".dxf": "dxf",
    ".dwg": "dwg",
    ".obj": "obj",
    ".stl": "stl",
    ".gltf": "gltf",
    ".glb": "glb",
    ".omf": "omf",
}


def detect_cad_format(path: Path | str) -> str:
    """
    Detect the CAD format of a file from its extension.

    Parameters
    ----------
    path:
        Path to the CAD file (or just a filename with extension).

    Returns
    -------
    str
        One of: ``"dxf"``, ``"dwg"``, ``"obj"``, ``"stl"``,
        ``"gltf"``, ``"glb"``, ``"omf"``, ``"unknown"``.
    """
    suffix = Path(path).suffix.lower()
    return _EXTENSION_MAP.get(suffix, "unknown")


# ---------------------------------------------------------------------------
# DXF — layers
# ---------------------------------------------------------------------------

def read_dxf_layers(path: Path | str) -> list[dict[str, Any]]:
    """
    Extract layer information from a DXF file.

    Returns a list of dicts, one per layer, containing:
    - ``name``       — layer name
    - ``color``      — AutoCAD colour index (int)
    - ``is_on``      — whether the layer is visible
    - ``is_frozen``  — whether the layer is frozen
    - ``entity_count`` — number of model-space entities on this layer

    Requires ezdxf. Install with:  pip install ezdxf

    Parameters
    ----------
    path:
        Path to the DXF file.

    Returns
    -------
    list[dict]
    """
    _require_ezdxf()
    import ezdxf

    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()

    # Count entities per layer
    layer_entity_counts: dict[str, int] = {}
    for entity in msp:
        layer_name = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"
        layer_entity_counts[layer_name] = layer_entity_counts.get(layer_name, 0) + 1

    layers: list[dict[str, Any]] = []
    for layer in doc.layers:
        name = layer.dxf.name
        layers.append({
            "name": name,
            "color": getattr(layer.dxf, "color", 7),
            "is_on": layer.is_on(),
            "is_frozen": layer.is_frozen(),
            "entity_count": layer_entity_counts.get(name, 0),
        })

    return layers


# ---------------------------------------------------------------------------
# DXF — entities
# ---------------------------------------------------------------------------

def read_dxf_entities(
    path: Path | str,
    layer_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Extract entity metadata from a DXF file.

    Returns a list of dicts, one per entity, containing:
    - ``type``    — DXF entity type (e.g. ``"LINE"``, ``"POLYLINE"``)
    - ``layer``   — layer name
    - ``handle``  — entity handle (unique ID within the file)
    - ``bbox``    — bounding box dict ``{"min": [x,y,z], "max": [x,y,z]}``
                    or ``None`` if not computable

    Requires ezdxf. Install with:  pip install ezdxf

    Parameters
    ----------
    path:
        Path to the DXF file.
    layer_filter:
        If provided, only entities on these layers are returned.

    Returns
    -------
    list[dict]
    """
    _require_ezdxf()
    import ezdxf
    from ezdxf.math import BoundingBox

    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()

    filter_set = set(layer_filter) if layer_filter else None

    result: list[dict[str, Any]] = []
    for entity in msp:
        layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"
        if filter_set and layer not in filter_set:
            continue

        bbox_data = None
        try:
            bb = entity.bbox()
            if bb and bb.has_data:
                bbox_data = {
                    "min": list(bb.extmin),
                    "max": list(bb.extmax),
                }
        except Exception:
            pass

        result.append({
            "type": entity.dxftype(),
            "layer": layer,
            "handle": entity.dxf.handle if hasattr(entity.dxf, "handle") else None,
            "bbox": bbox_data,
        })

    return result


# ---------------------------------------------------------------------------
# DXF — bounding box
# ---------------------------------------------------------------------------

def get_dxf_bounding_box(path: Path | str) -> dict[str, Any]:
    """
    Compute the overall model-space bounding box of a DXF file.

    Iterates all model-space entities and accumulates min/max extents.

    Requires ezdxf. Install with:  pip install ezdxf

    Parameters
    ----------
    path:
        Path to the DXF file.

    Returns
    -------
    dict with keys ``min_x``, ``min_y``, ``min_z``, ``max_x``, ``max_y``,
    ``max_z``, ``width``, ``height``, ``depth``.
    An ``"empty"`` key is True if no bounding box could be computed.
    """
    _require_ezdxf()
    import ezdxf

    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()

    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")
    found = False

    for entity in msp:
        try:
            bb = entity.bbox()
            if bb and bb.has_data:
                ex_min = bb.extmin
                ex_max = bb.extmax
                min_x = min(min_x, ex_min.x)
                min_y = min(min_y, ex_min.y)
                min_z = min(min_z, ex_min.z)
                max_x = max(max_x, ex_max.x)
                max_y = max(max_y, ex_max.y)
                max_z = max(max_z, ex_max.z)
                found = True
        except Exception:
            continue

    if not found:
        return {"empty": True}

    return {
        "empty": False,
        "min_x": min_x,
        "min_y": min_y,
        "min_z": min_z,
        "max_x": max_x,
        "max_y": max_y,
        "max_z": max_z,
        "width": max_x - min_x,
        "height": max_y - min_y,
        "depth": max_z - min_z,
    }


# ---------------------------------------------------------------------------
# DXF — full summary
# ---------------------------------------------------------------------------

def convert_dxf_to_summary(path: Path | str) -> dict[str, Any]:
    """
    Build a comprehensive summary dict for a DXF file.

    Returns a dict with:
    - ``layers``         — list of layer dicts (from :func:`read_dxf_layers`)
    - ``entity_counts``  — dict mapping entity type → count
    - ``bounding_box``   — bounding box dict (from :func:`get_dxf_bounding_box`)
    - ``units``          — DXF drawing units string (e.g. ``"Meters"``)
    - ``dxf_version``    — DXF version string (e.g. ``"AC1032"`` = AutoCAD 2018)
    - ``total_entities`` — total number of model-space entities

    Requires ezdxf. Install with:  pip install ezdxf

    Parameters
    ----------
    path:
        Path to the DXF file.

    Returns
    -------
    dict
    """
    _require_ezdxf()
    import ezdxf

    path = Path(path)
    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()

    # Entity type counts
    entity_counts: dict[str, int] = {}
    for entity in msp:
        etype = entity.dxftype()
        entity_counts[etype] = entity_counts.get(etype, 0) + 1

    # Drawing units
    unit_code = doc.header.get("$INSUNITS", 0)
    units_map = {
        0: "Unitless", 1: "Inches", 2: "Feet", 3: "Miles",
        4: "Millimeters", 5: "Centimeters", 6: "Meters", 7: "Kilometers",
        8: "Microinches", 9: "Mils", 10: "Yards", 11: "Angstroms",
        12: "Nanometers", 13: "Microns", 14: "Decimeters", 15: "Decameters",
        16: "Hectometers", 17: "Gigameters", 18: "Astronomical Units",
        19: "Light Years", 20: "Parsecs",
    }
    units = units_map.get(unit_code, f"Unknown ({unit_code})")

    return {
        "file": path.name,
        "dxf_version": doc.dxfversion,
        "units": units,
        "layers": read_dxf_layers(path),
        "entity_counts": entity_counts,
        "total_entities": sum(entity_counts.values()),
        "bounding_box": get_dxf_bounding_box(path),
    }


# ---------------------------------------------------------------------------
# Generic CAD file metadata (no full parse)
# ---------------------------------------------------------------------------

def cad_file_metadata(path: Path | str) -> dict[str, Any]:
    """
    Return basic metadata about a CAD file without fully parsing it.

    This function does NOT load the full CAD model. It only inspects
    the file system and the file extension.

    Parameters
    ----------
    path:
        Path to the CAD file.

    Returns
    -------
    dict with keys ``file_name``, ``format``, ``size_bytes``,
    ``size_mb``, ``exists``.
    """
    path = Path(path)
    fmt = detect_cad_format(path)

    if not path.exists():
        return {
            "file_name": path.name,
            "format": fmt,
            "size_bytes": None,
            "size_mb": None,
            "exists": False,
        }

    size = path.stat().st_size
    return {
        "file_name": path.name,
        "format": fmt,
        "size_bytes": size,
        "size_mb": round(size / (1024 * 1024), 3),
        "exists": True,
    }


# ---------------------------------------------------------------------------
# DWG — stub (requires ODA File Converter)
# ---------------------------------------------------------------------------

def read_dwg_layers(path: Path | str) -> list[dict[str, Any]]:
    """
    Extract layer information from a DWG file.

    .. note::
        DWG is a proprietary Autodesk binary format that cannot be read
        directly by Python libraries. You must first convert the DWG to
        DXF using the **ODA File Converter** (free external tool):

        1. Download from: https://www.opendesign.com/guestfiles/oda_file_converter
        2. Convert DWG to DXF::

               ODAFileConverter <input_dir> <output_dir> ACAD2018 DXF 1 1

        3. Then use :func:`read_dxf_layers` on the resulting .dxf file.

    Raises
    ------
    NotImplementedError
        Always — DWG cannot be parsed without the ODA File Converter.
    """
    raise NotImplementedError(
        "DWG format requires the ODA File Converter to convert to DXF first.\n"
        "Download from: https://www.opendesign.com/guestfiles/oda_file_converter\n"
        "Convert with:  ODAFileConverter <input_dir> <output_dir> ACAD2018 DXF 1 1\n"
        "Then use read_dxf_layers() on the resulting .dxf file."
    )


def read_dwg_entities(
    path: Path | str,
    layer_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Extract entity metadata from a DWG file.

    Raises NotImplementedError — see :func:`read_dwg_layers` for instructions.
    """
    raise NotImplementedError(
        "DWG format requires the ODA File Converter. "
        "See read_dwg_layers() docstring for instructions."
    )


# ---------------------------------------------------------------------------
# GLTF / GLB — metadata via trimesh (optional)
# ---------------------------------------------------------------------------

def read_gltf_metadata(path: Path | str) -> dict[str, Any]:
    """
    Return metadata for a GLTF or GLB file.

    Uses trimesh if available for geometry statistics.
    Falls back to basic file metadata if trimesh is not installed.

    Parameters
    ----------
    path:
        Path to the .gltf or .glb file.

    Returns
    -------
    dict with basic file info and, if trimesh is available,
    mesh statistics (vertex count, face count, bounding box).
    """
    path = Path(path)
    base = cad_file_metadata(path)

    if not _TRIMESH_AVAILABLE:
        base["trimesh_available"] = False
        base["note"] = (
            "Install trimesh for geometry statistics: pip install trimesh"
        )
        return base

    import trimesh as tm
    try:
        scene = tm.load(str(path))
        if hasattr(scene, "geometry"):
            meshes = list(scene.geometry.values())
        elif isinstance(scene, tm.Trimesh):
            meshes = [scene]
        else:
            meshes = []

        total_vertices = sum(len(m.vertices) for m in meshes)
        total_faces = sum(len(m.faces) for m in meshes)

        if meshes:
            all_bounds = [m.bounds for m in meshes]
            min_pt = [min(b[0][i] for b in all_bounds) for i in range(3)]
            max_pt = [max(b[1][i] for b in all_bounds) for i in range(3)]
            bounds = {"min": min_pt, "max": max_pt}
        else:
            bounds = {}

        base.update({
            "trimesh_available": True,
            "mesh_count": len(meshes),
            "total_vertices": total_vertices,
            "total_faces": total_faces,
            "bounding_box": bounds,
        })
    except Exception as exc:
        base["trimesh_error"] = str(exc)

    return base

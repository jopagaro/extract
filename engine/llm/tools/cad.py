"""
CAD geometry tool schemas and executors.

Wraps CADVERT's pipeline as callable tools for the LLM. When the model
encounters a CAD file reference in a project, it can call these tools to
query exact geometric data — slope angles, pit depth, bench widths,
volume — rather than relying on a visual description.

Requires: pip install -e /path/to/CADVERT
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool schemas (OpenAI format)
# ---------------------------------------------------------------------------

ANALYZE_CAD_GEOMETRY_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "analyze_cad_geometry",
        "description": (
            "Run exact geometric analysis on a 3D solid model file (STEP, IGES, BREP). "
            "Returns a structured document with bounding box, volume, surface area, "
            "detected features (drill holes, benches, ramps), slope angles (from face normals), "
            "and spatial relationships (pit depth, bench widths, clearances). "
            "Use this when a CAD file is present in the project and you need precise geometry "
            "rather than a visual description."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the STEP/IGES/BREP file to analyse",
                },
            },
            "required": ["file_path"],
        },
    },
}

QUERY_CAD_FEATURE_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "query_cad_feature",
        "description": (
            "Query a specific geometric feature from a previously analysed CAD file. "
            "Returns exact parameters: for a hole → diameter, depth, axis, location; "
            "for a slope face → dip angle, area, normal vector; "
            "for a bench → height, width, orientation. "
            "Use feature IDs from the analyze_cad_geometry output."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the CAD file (same as used in analyze_cad_geometry)",
                },
                "feature_id": {
                    "type": "string",
                    "description": "Feature ID from the geometry document, e.g. 'hole_1', 'F12', 'fillet_3'",
                },
            },
            "required": ["file_path", "feature_id"],
        },
    },
}

MEASURE_CAD_DISTANCE_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "measure_cad_distance",
        "description": (
            "Measure the exact minimum distance between two geometric entities in a CAD model. "
            "Useful for: pit depth (bottom face to surface), bench berm width, "
            "haul road clearance, infrastructure setback distances. "
            "Uses OCC BRepExtrema for exact computation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the CAD file",
                },
                "entity_a": {
                    "type": "string",
                    "description": "First entity: face ID like 'F12', feature like 'hole_1', or coordinates 'x,y,z'",
                },
                "entity_b": {
                    "type": "string",
                    "description": "Second entity: same format as entity_a",
                },
            },
            "required": ["file_path", "entity_a", "entity_b"],
        },
    },
}

ALL_CAD_TOOLS: list[dict] = [
    ANALYZE_CAD_GEOMETRY_TOOL,
    QUERY_CAD_FEATURE_TOOL,
    MEASURE_CAD_DISTANCE_TOOL,
]


# ---------------------------------------------------------------------------
# Session cache — holds loaded CADVERT state per file path so the LLM
# can call multiple tools against the same file without re-loading
# ---------------------------------------------------------------------------

_SESSION_CACHE: dict[str, dict[str, Any]] = {}


def _load_cadvert_session(file_path: str) -> dict[str, Any] | None:
    """
    Load and cache a CADVERT analysis session for a file.
    Returns a dict with keys: shape, graph, features, spatial, metadata.
    Returns None if CADVERT is not installed or file cannot be loaded.
    """
    if file_path in _SESSION_CACHE:
        return _SESSION_CACHE[file_path]

    try:
        from cadvert.ingest import load_step
        from cadvert.topology import build_topology
        from cadvert.features import detect_features
        from cadvert.spatial import compute_spatial_relationships
        from cadvert.document import assign_feature_ids
    except ImportError:
        log.warning("CADVERT not installed — CAD geometry tools unavailable")
        return None

    path = Path(file_path)
    if not path.exists():
        log.warning("CAD file not found: %s", file_path)
        return None

    try:
        shape, body_count, metadata = load_step(str(path))

        session: dict[str, Any] = {
            "shape": shape,
            "metadata": metadata,
            "graph": None,
            "features": [],
            "feature_ids": [],
            "spatial": [],
        }

        if not metadata.is_mesh:
            graph = build_topology(shape, body_count)
            features = detect_features(graph)
            feature_ids = assign_feature_ids(features)
            spatial = compute_spatial_relationships(graph, features, shape=shape)
            session.update({
                "graph": graph,
                "features": features,
                "feature_ids": feature_ids,
                "spatial": spatial,
            })

        _SESSION_CACHE[file_path] = session
        return session

    except Exception as exc:
        log.error("CADVERT session load failed for %s: %s", file_path, exc)
        return None


# ---------------------------------------------------------------------------
# Executors
# ---------------------------------------------------------------------------

def execute_analyze_cad_geometry(args: dict[str, Any]) -> dict[str, Any]:
    """Run full CADVERT pipeline and return the tier0 HSD document."""
    file_path = args.get("file_path", "")

    session = _load_cadvert_session(file_path)
    if session is None:
        return {
            "success": False,
            "error": "CADVERT not installed or file not found. Install with: pip install -e /path/to/CADVERT",
        }

    try:
        from cadvert.document import render_tier0

        metadata = session["metadata"]
        graph = session["graph"]
        features = session["features"]
        feature_ids = session["feature_ids"]
        spatial = session["spatial"]

        if metadata.is_mesh:
            tier0 = render_tier0(
                None, file_path,
                units=metadata.units,
                mesh_info={"triangle_count": metadata.triangle_count},
            )
        else:
            tier0 = render_tier0(
                graph, file_path,
                feature_ids=feature_ids,
                features=features,
                spatial=spatial,
                units=metadata.units,
                gdt_annotations=metadata.gdt_annotations or [],
            )

        return {
            "success": True,
            "file": Path(file_path).name,
            "format": metadata.source_format,
            "units": metadata.units,
            "is_mesh": metadata.is_mesh,
            "feature_count": len(features),
            "spatial_relationship_count": len(spatial),
            "geometry_document": tier0,
        }

    except Exception as exc:
        return {"success": False, "error": str(exc)}


def execute_query_cad_feature(args: dict[str, Any]) -> dict[str, Any]:
    """Return detailed geometry for a specific feature or face."""
    file_path = args.get("file_path", "")
    feature_id = args.get("feature_id", "")

    session = _load_cadvert_session(file_path)
    if session is None:
        return {"success": False, "error": "CADVERT not installed or file not found"}

    graph = session.get("graph")
    features = session.get("features", [])
    feature_ids = session.get("feature_ids", [])

    # Check if it's a feature ID (hole_1, fillet_3, etc.)
    if "_" in feature_id and not feature_id.startswith("F"):
        for fid, feature in zip(feature_ids, features):
            if fid == feature_id:
                return {
                    "success": True,
                    "feature_id": feature_id,
                    "feature_type": feature.feature_type,
                    "parameters": feature.parameters,
                    "confidence": feature.confidence,
                    "standard_match": feature.standard_match,
                    "notes": feature.notes,
                    "face_ids": feature.face_ids,
                }
        return {"success": False, "error": f"Feature '{feature_id}' not found"}

    # Check if it's a face ID (F12, 12)
    if graph is not None:
        fid_int = None
        try:
            fid_int = int(feature_id.lstrip("Ff"))
        except ValueError:
            pass

        if fid_int is not None:
            for face in graph.faces:
                if face.id == fid_int:
                    return {
                        "success": True,
                        "face_id": fid_int,
                        "geometry": face.geometry,
                        "area": face.area,
                        "boundary_edge_ids": face.edge_ids,
                    }
            return {"success": False, "error": f"Face F{fid_int} not found"}

    return {"success": False, "error": f"Could not resolve '{feature_id}' to a feature or face"}


def execute_measure_cad_distance(args: dict[str, Any]) -> dict[str, Any]:
    """Measure exact distance between two entities using OCC BRepExtrema."""
    file_path = args.get("file_path", "")
    entity_a = args.get("entity_a", "")
    entity_b = args.get("entity_b", "")

    session = _load_cadvert_session(file_path)
    if session is None:
        return {"success": False, "error": "CADVERT not installed or file not found"}

    # Delegate to CADVERT's server-side tool logic
    try:
        from cadvert.spatial import compute_spatial_relationships
        graph = session.get("graph")
        shape = session.get("shape")

        if graph is None:
            return {"success": False, "error": "Mesh files do not support distance measurement"}

        # Find the two faces by ID
        def _get_face(ref: str):
            try:
                fid = int(ref.lstrip("Ff"))
                for face in graph.faces:
                    if face.id == fid:
                        return face
            except ValueError:
                pass
            return None

        face_a = _get_face(entity_a)
        face_b = _get_face(entity_b)

        if face_a is None or face_b is None:
            return {
                "success": False,
                "error": f"Could not resolve both entities to faces: '{entity_a}', '{entity_b}'",
                "hint": "Use face IDs like 'F12' or 'F5'. Feature IDs (hole_1) are not supported for distance measurement.",
            }

        # Use OCC BRepExtrema for exact distance
        try:
            from OCP.BRepExtrema import BRepExtrema_DistShapeShape
            from OCP.TopExp import TopExp_Explorer
            from OCP.TopAbs import TopAbs_FACE
            from OCP.BRep import BRep_Builder
            from OCP.TopoDS import TopoDS_Compound
            import itertools

            explorer_a = TopExp_Explorer(shape, TopAbs_FACE)
            idx = 0
            topo_face_a = topo_face_b = None
            while explorer_a.More():
                idx += 1
                if idx == face_a.id:
                    topo_face_a = explorer_a.Current()
                if idx == face_b.id:
                    topo_face_b = explorer_a.Current()
                explorer_a.Next()

            if topo_face_a is None or topo_face_b is None:
                raise RuntimeError("Could not locate faces in OCC shape")

            dist_calc = BRepExtrema_DistShapeShape(topo_face_a, topo_face_b)
            dist_calc.Perform()

            if not dist_calc.IsDone():
                raise RuntimeError("BRepExtrema distance calculation failed")

            distance = dist_calc.Value()
            pt_a = dist_calc.PointOnShape1(1)
            pt_b = dist_calc.PointOnShape2(1)

            return {
                "success": True,
                "distance": round(distance, 4),
                "units": session["metadata"].units,
                "from": {"face_id": face_a.id, "point": [round(pt_a.X(), 4), round(pt_a.Y(), 4), round(pt_a.Z(), 4)]},
                "to": {"face_id": face_b.id, "point": [round(pt_b.X(), 4), round(pt_b.Y(), 4), round(pt_b.Z(), 4)]},
            }

        except ImportError:
            # OCC not available, return bounding box approximation
            bb = graph.bounding_box
            return {
                "success": True,
                "distance": None,
                "note": "OCC not available — exact distance unavailable. Bounding box for reference:",
                "bounding_box": bb,
            }

    except Exception as exc:
        return {"success": False, "error": str(exc)}

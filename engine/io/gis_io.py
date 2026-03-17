"""
GIS file I/O utilities.

Handles reading and inspecting geospatial data formats used in mining
project areas, tenement boundaries, and claim polygons.

Supported formats:
- GeoJSON (.geojson, .json with spatial content)
- Shapefile (.shp) — requires fiona
- GeoPackage (.gpkg) — requires fiona
- GeoTIFF (.tif, .tiff) — basic metadata only
- KML (.kml)

Optional dependencies:
- fiona   — required for Shapefile and GeoPackage reads.
             Install: pip install fiona
- shapely — used for bounding box calculation on vector data.
             Install: pip install shapely

Both imports are wrapped in try/except so this module can be imported
without these packages; functions raise clear ImportErrors when called.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Optional dependency detection
# ---------------------------------------------------------------------------

try:
    import fiona  # noqa: F401
    _FIONA_AVAILABLE = True
except ImportError:
    _FIONA_AVAILABLE = False

try:
    from shapely.geometry import shape  # noqa: F401
    _SHAPELY_AVAILABLE = True
except ImportError:
    _SHAPELY_AVAILABLE = False

_FIONA_INSTALL_MSG = (
    "fiona is required to read Shapefiles and GeoPackages but is not installed.\n"
    "Install it with:  pip install fiona\n"
    "On macOS you may need:  brew install gdal  first."
)

_SHAPELY_INSTALL_MSG = (
    "shapely is optional for geometry operations.\n"
    "Install it with:  pip install shapely"
)


def _require_fiona() -> None:
    if not _FIONA_AVAILABLE:
        raise ImportError(_FIONA_INSTALL_MSG)


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

_EXTENSION_FORMAT_MAP: dict[str, str] = {
    ".geojson": "geojson",
    ".shp": "shapefile",
    ".gpkg": "gpkg",
    ".tif": "geotiff",
    ".tiff": "geotiff",
    ".kml": "kml",
    ".kmz": "kml",
}


def detect_gis_format(path: Path | str) -> str:
    """
    Detect the GIS format of a file from its extension.

    Parameters
    ----------
    path:
        Path to the GIS file (or just a filename with extension).

    Returns
    -------
    str
        One of: ``"geojson"``, ``"shapefile"``, ``"gpkg"``,
        ``"geotiff"``, ``"kml"``, ``"unknown"``.
    """
    suffix = Path(path).suffix.lower()
    # .json could be GeoJSON — check for spatial content would require opening
    if suffix == ".json":
        return "geojson"
    return _EXTENSION_FORMAT_MAP.get(suffix, "unknown")


# ---------------------------------------------------------------------------
# GeoJSON
# ---------------------------------------------------------------------------

def read_geojson(path: Path | str) -> dict[str, Any]:
    """
    Read a GeoJSON file and return the parsed Python dict.

    Parameters
    ----------
    path:
        Path to the .geojson file.

    Returns
    -------
    dict
        Full GeoJSON structure (FeatureCollection, Feature, or Geometry).
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def extract_claims_from_geojson(path: Path | str) -> list[dict[str, Any]]:
    """
    Extract mineral claim polygons from a GeoJSON file.

    Returns one dict per feature, containing the feature properties
    plus a ``geometry_type`` key and a simplified ``coordinates`` preview.

    Looks for features with Polygon or MultiPolygon geometry types, as
    these are typical for mineral tenement / claim boundary files.

    Parameters
    ----------
    path:
        Path to the GeoJSON file.

    Returns
    -------
    list[dict]
        One dict per claim feature.
    """
    data = read_geojson(path)

    features = []
    if data.get("type") == "FeatureCollection":
        raw_features = data.get("features", [])
    elif data.get("type") == "Feature":
        raw_features = [data]
    else:
        # Bare geometry — wrap it
        raw_features = [{"type": "Feature", "geometry": data, "properties": {}}]

    for feat in raw_features:
        geom = feat.get("geometry") or {}
        geom_type = geom.get("type", "")
        if geom_type not in ("Polygon", "MultiPolygon"):
            continue
        props = dict(feat.get("properties") or {})
        props["geometry_type"] = geom_type
        # Add a coordinate count for quick inspection
        coords = geom.get("coordinates", [])
        if geom_type == "Polygon" and coords:
            props["coordinate_count"] = len(coords[0]) if coords else 0
        elif geom_type == "MultiPolygon":
            props["coordinate_count"] = sum(
                len(ring[0]) if ring else 0 for ring in coords
            )
        features.append(props)

    return features


# ---------------------------------------------------------------------------
# Shapefile / GeoPackage (fiona)
# ---------------------------------------------------------------------------

def read_shapefile_metadata(path: Path | str) -> dict[str, Any]:
    """
    Return metadata for a Shapefile or GeoPackage without loading all features.

    Metadata includes field names and types, CRS, feature count,
    geometry type, and bounding box.

    Requires fiona. Install with:  pip install fiona

    Parameters
    ----------
    path:
        Path to the .shp file (or .gpkg for GeoPackage).

    Returns
    -------
    dict
    """
    _require_fiona()
    import fiona

    path = Path(path)
    with fiona.open(str(path)) as src:
        schema = src.schema
        crs = src.crs
        feature_count = len(src)
        bounds = src.bounds  # (min_x, min_y, max_x, max_y)
        driver = src.driver

    fields: dict[str, str] = {
        name: ftype
        for name, ftype in schema.get("properties", {}).items()
    }

    return {
        "file": path.name,
        "driver": driver,
        "geometry_type": schema.get("geometry", "Unknown"),
        "field_names": list(fields.keys()),
        "fields": fields,
        "feature_count": feature_count,
        "crs": str(crs) if crs else None,
        "bounding_box": {
            "min_x": bounds[0],
            "min_y": bounds[1],
            "max_x": bounds[2],
            "max_y": bounds[3],
        } if bounds else None,
    }


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------

def get_bounding_box(path: Path | str) -> dict[str, Any]:
    """
    Return the bounding box of a GIS file.

    Dispatches to the appropriate reader based on the file format.
    For GeoJSON, iterates all features to accumulate extents.
    For Shapefiles / GeoPackages, uses fiona's efficient index.

    Parameters
    ----------
    path:
        Path to the GIS file.

    Returns
    -------
    dict with keys ``min_x``, ``min_y``, ``max_x``, ``max_y``.
    An ``"empty"`` key is True if no bounding box could be computed.
    """
    path = Path(path)
    fmt = detect_gis_format(path)

    if fmt == "geojson":
        return _bbox_from_geojson(path)
    elif fmt in ("shapefile", "gpkg"):
        meta = read_shapefile_metadata(path)
        bb = meta.get("bounding_box")
        if bb:
            return {**bb, "empty": False}
        return {"empty": True}
    else:
        return {"empty": True, "note": f"Bounding box not supported for format: {fmt}"}


def _bbox_from_geojson(path: Path) -> dict[str, Any]:
    """Compute bounding box by iterating all GeoJSON feature coordinates."""
    data = read_geojson(path)

    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    found = False

    if data.get("type") == "FeatureCollection":
        features = data.get("features", [])
    elif data.get("type") == "Feature":
        features = [data]
    else:
        features = [{"geometry": data}]

    def _scan_coords(coords: Any) -> None:
        nonlocal min_x, min_y, max_x, max_y, found
        if not coords:
            return
        if isinstance(coords[0], (int, float)):
            # It's a single coordinate pair [x, y] or [x, y, z]
            x, y = coords[0], coords[1]
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            found = True
        else:
            for item in coords:
                _scan_coords(item)

    for feat in features:
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates")
        if coords:
            _scan_coords(coords)

    if not found:
        return {"empty": True}

    return {
        "empty": False,
        "min_x": min_x,
        "min_y": min_y,
        "max_x": max_x,
        "max_y": max_y,
    }

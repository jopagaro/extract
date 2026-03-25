"""
OMF 3D Mining File Loader — Extract + Render pipeline.

Given an OMF (Open Mining Format) file this module produces two outputs:

  1. Structured text for the LLM analysis pipeline
     - Block model grade statistics, tonnage at cutoffs, spatial breakdown
     - Wireframe geometry: centroid, bounding box, PCA-derived orientation
     - Drill hole composite summary tables

  2. pyvista PNG renders saved to renders_dir
     - 3d_perspective.png  — oblique SE view, grade-coloured
     - long_section.png    — looking along strike (PC2 axis)
     - cross_section.png   — perpendicular to strike (PC1 axis)
     - plan_view.png       — top-down at grade centroid elevation

  A renders_manifest.json is written alongside the PNGs describing each figure.
  This manifest is later read by analyze.py to build the AVAILABLE FIGURES block
  passed to the LLM reporting prompts, which insert {{FIGURE: ...}} placeholders
  that the PDF exporter and React viewer substitute with the actual images.

Dependencies (graceful degradation if missing):
  - omf        (pip install omf)
  - pyvista    (pip install pyvista)
  - numpy      (already in requirements.txt)
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# ── Public entry point ────────────────────────────────────────────────────────

def extract_omf_data(path: Path, renders_dir: Path) -> str:
    """
    Process an OMF file and return structured text for the LLM pipeline.
    Renders are saved to renders_dir as side effects.

    Returns a formatted text block describing the project's 3D model data.
    Never raises — all errors are caught and logged, degraded text returned.
    """
    try:
        import omf as omflib
    except ImportError:
        return f"[OMF: {path.name} — install 'omf' package to process 3D model files]"

    try:
        reader = omflib.OMFReader(str(path))
        project = reader.get_project()
    except Exception as exc:
        logger.warning("OMF read failed for %s: %s", path.name, exc)
        return f"[OMF: {path.name} — could not be parsed: {exc}]"

    parts = [f"[OMF 3D Model: {path.name}]"]
    if project.name:
        parts.append(f"Project: {project.name}")
    if project.description:
        parts.append(f"Description: {project.description}")

    renders_dir.mkdir(parents=True, exist_ok=True)
    render_manifest_entries: list[dict] = []

    # Collect primary ore body mesh for rendering (first surface with most vertices)
    primary_surface_verts: np.ndarray | None = None
    primary_surface_tris: np.ndarray | None = None
    primary_grade_values: np.ndarray | None = None
    primary_grade_name: str = "grade"

    for element in project.elements:
        etype = type(element).__name__

        # ── Surface / wireframe ───────────────────────────────────────────────
        if etype == "SurfaceElement":
            section = _describe_surface(element)
            if section:
                parts.append(section)
            # Collect for rendering
            try:
                verts = np.array(element.geometry.vertices.array)
                tris  = np.array(element.geometry.triangles.array)
                if primary_surface_verts is None or len(verts) > len(primary_surface_verts):
                    primary_surface_verts = verts
                    primary_surface_tris  = tris
                    # Try to get a grade scalar
                    for d in (element.data or []):
                        if hasattr(d, "array") and d.array is not None:
                            arr = np.array(d.array.array)
                            if arr.dtype.kind in ("f", "i") and len(arr) > 0:
                                primary_grade_values = arr
                                primary_grade_name   = getattr(d, "name", "grade") or "grade"
                                break
            except Exception:
                pass

        # ── Volume / block model ──────────────────────────────────────────────
        elif etype == "VolumeElement":
            section, block_verts, block_grades, grade_name = _describe_volume(element)
            if section:
                parts.append(section)
            if block_verts is not None and primary_surface_verts is None:
                # Use block centroids as fallback render geometry
                primary_surface_verts = block_verts
                primary_grade_values  = block_grades
                primary_grade_name    = grade_name

        # ── Line set / drill holes ────────────────────────────────────────────
        elif etype == "LineSetElement":
            section = _describe_lineset(element)
            if section:
                parts.append(section)

        # ── Point set / collars ───────────────────────────────────────────────
        elif etype == "PointSetElement":
            section = _describe_pointset(element)
            if section:
                parts.append(section)

    # ── Render figures ────────────────────────────────────────────────────────
    if primary_surface_verts is not None and len(primary_surface_verts) >= 4:
        render_manifest_entries = _render_figures(
            verts        = primary_surface_verts,
            tris         = primary_surface_tris,
            grade_values = primary_grade_values,
            grade_name   = primary_grade_name,
            renders_dir  = renders_dir,
        )

    if render_manifest_entries:
        manifest = {
            "renders": render_manifest_entries,
            "source_file": path.name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        (renders_dir / "renders_manifest.json").write_text(
            json.dumps(manifest, indent=2)
        )
        logger.info("OMF renders written to %s", renders_dir)

    return "\n\n".join(parts)


# ── Surface description ───────────────────────────────────────────────────────

def _describe_surface(element) -> str | None:
    try:
        geom = element.geometry
        verts = np.array(geom.vertices.array)   # (N, 3)
        tris  = np.array(geom.triangles.array)  # (M, 3)

        name = getattr(element, "name", "") or "Unnamed surface"
        lines = [f"[Surface: {name}]"]
        lines.append(f"  Vertices: {len(verts):,}   Triangles: {len(tris):,}")

        # Bounding box
        mn, mx = verts.min(axis=0), verts.max(axis=0)
        lines.append(
            f"  Bounding box (m): X {mn[0]:.0f}–{mx[0]:.0f}  "
            f"Y {mn[1]:.0f}–{mx[1]:.0f}  Z {mn[2]:.0f}–{mx[2]:.0f}"
        )

        # Centroid
        centroid = verts.mean(axis=0)
        lines.append(f"  Centroid: X {centroid[0]:.0f}  Y {centroid[1]:.0f}  Z {centroid[2]:.0f}")

        # PCA-derived orientation
        oriented = _pca_orientation(verts)
        if oriented:
            lines.append(f"  Long axis: {oriented}")

        # Volume estimate via signed tetrahedra
        vol = _mesh_volume(verts, tris)
        if vol is not None:
            lines.append(f"  Volume estimate: {vol / 1e6:.2f} Mm³  ({vol:.0f} m³)")

        # Surface area
        area = _mesh_surface_area(verts, tris)
        if area is not None:
            lines.append(f"  Surface area: {area / 1e4:.1f} ha  ({area:.0f} m²)")

        # Data attributes
        for d in (element.data or []):
            attr_line = _describe_data_attribute(d)
            if attr_line:
                lines.append(f"  Attribute — {attr_line}")

        return "\n".join(lines)
    except Exception as exc:
        logger.debug("Surface describe failed: %s", exc)
        return None


# ── Volume / block model description ─────────────────────────────────────────

def _describe_volume(element) -> tuple[str | None, np.ndarray | None, np.ndarray | None, str]:
    try:
        geom = element.geometry
        name = getattr(element, "name", "") or "Unnamed block model"
        lines = [f"[Block Model: {name}]"]

        tu = np.array(geom.tensor_u)
        tv = np.array(geom.tensor_v)
        tw = np.array(geom.tensor_w)

        nu, nv, nw = len(tu), len(tv), len(tw)
        n_blocks = nu * nv * nw
        lines.append(f"  Grid: {nu} × {nv} × {nw} = {n_blocks:,} blocks")
        lines.append(
            f"  Block size (avg): {tu.mean():.1f}m × {tv.mean():.1f}m × {tw.mean():.1f}m"
        )

        # Origin and extent
        origin = np.array(geom.origin.array) if hasattr(geom, "origin") and geom.origin else np.zeros(3)
        extent_u = tu.sum()
        extent_v = tv.sum()
        extent_w = tw.sum()
        lines.append(
            f"  Origin: X {origin[0]:.0f}  Y {origin[1]:.0f}  Z {origin[2]:.0f}"
        )
        lines.append(
            f"  Extent: {extent_u:.0f}m (U) × {extent_v:.0f}m (V) × {extent_w:.0f}m (W)"
        )

        # Build block centroids
        cu = origin[0] + np.cumsum(np.concatenate([[0], tu]))[:-1] + tu / 2
        cv = origin[1] + np.cumsum(np.concatenate([[0], tv]))[:-1] + tv / 2
        cw = origin[2] + np.cumsum(np.concatenate([[0], tw]))[:-1] + tw / 2
        uu, vv, ww = np.meshgrid(cu, cv, cw, indexing="ij")
        centroids = np.column_stack([uu.ravel(), vv.ravel(), ww.ravel()])

        primary_grades: np.ndarray | None = None
        primary_name = "grade"

        # Grade statistics for each numeric attribute
        for d in (element.data or []):
            try:
                if not hasattr(d, "array") or d.array is None:
                    continue
                arr = np.array(d.array.array, dtype=float).ravel()
                if len(arr) != n_blocks or not np.isfinite(arr).any():
                    continue
                attr_name = getattr(d, "name", "attribute") or "attribute"
                valid = arr[np.isfinite(arr)]

                lines.append(f"\n  [Attribute: {attr_name}]")
                lines.append(f"    Count: {len(valid):,} blocks with valid data")
                lines.append(
                    f"    Range: {valid.min():.4g} – {valid.max():.4g}  "
                    f"Mean: {valid.mean():.4g}  P50: {np.median(valid):.4g}  "
                    f"P90: {np.percentile(valid, 90):.4g}"
                )

                # Histogram (10 bins)
                hist, edges = np.histogram(valid, bins=10)
                hist_lines = []
                for i, (cnt, lo, hi) in enumerate(zip(hist, edges[:-1], edges[1:])):
                    pct = 100 * cnt / len(valid)
                    hist_lines.append(f"    {lo:.3g}–{hi:.3g}: {cnt:,} blocks ({pct:.1f}%)")
                lines.append("    Grade histogram:\n" + "\n".join(hist_lines))

                # Tonnage at standard cutoffs (assume density=2.7 if no density attr)
                block_vol = tu.mean() * tv.mean() * tw.mean()
                density   = 2.7
                cutoffs = [0.3, 0.5, 1.0, 2.0]
                tonne_lines = []
                for co in cutoffs:
                    above = (arr >= co) & np.isfinite(arr)
                    if above.any():
                        t = above.sum() * block_vol * density / 1e6  # Mt
                        g = arr[above].mean()
                        tonne_lines.append(f"    ≥ {co} g/t: {t:.1f} Mt @ {g:.2f} g/t mean")
                if tonne_lines:
                    lines.append("    Indicative tonnage at cutoffs (density=2.7 assumed):\n" + "\n".join(tonne_lines))

                # Spatial: high-grade zone
                if len(valid) > 0:
                    p90_thresh = np.percentile(valid, 90)
                    hg_mask = arr >= p90_thresh
                    if hg_mask.any():
                        hg_cents = centroids[hg_mask]
                        hg_bounds = hg_cents.min(axis=0), hg_cents.max(axis=0)
                        lines.append(
                            f"    High-grade core (≥P90 = {p90_thresh:.2g}): "
                            f"X {hg_bounds[0][0]:.0f}–{hg_bounds[1][0]:.0f}  "
                            f"Y {hg_bounds[0][1]:.0f}–{hg_bounds[1][1]:.0f}  "
                            f"Z {hg_bounds[0][2]:.0f}–{hg_bounds[1][2]:.0f}"
                        )

                # Keep first grade-like attribute for rendering
                if primary_grades is None:
                    primary_grades = arr
                    primary_name   = attr_name

            except Exception as de:
                logger.debug("Block model attribute failed: %s", de)

        return "\n".join(lines), centroids, primary_grades, primary_name

    except Exception as exc:
        logger.debug("Volume describe failed: %s", exc)
        return None, None, None, "grade"


# ── Line set / drill hole description ────────────────────────────────────────

def _describe_lineset(element) -> str | None:
    try:
        geom = element.geometry
        verts   = np.array(geom.vertices.array)
        segs    = np.array(geom.segments.array)
        name    = getattr(element, "name", "") or "Unnamed line set"
        n_holes = len(np.unique(segs)) // 2 if len(segs) else 0

        lines = [f"[Line Set / Drill Holes: {name}]"]
        lines.append(f"  Segments: {len(segs):,}   Vertices: {len(verts):,}")

        if len(verts):
            mn, mx = verts.min(axis=0), verts.max(axis=0)
            lines.append(
                f"  Spatial extent: X {mn[0]:.0f}–{mx[0]:.0f}  "
                f"Y {mn[1]:.0f}–{mx[1]:.0f}  Z {mn[2]:.0f}–{mx[2]:.0f}"
            )

        for d in (element.data or []):
            attr_line = _describe_data_attribute(d)
            if attr_line:
                lines.append(f"  Attribute — {attr_line}")

        return "\n".join(lines)
    except Exception as exc:
        logger.debug("LineSet describe failed: %s", exc)
        return None


# ── Point set / collar description ───────────────────────────────────────────

def _describe_pointset(element) -> str | None:
    try:
        geom  = element.geometry
        verts = np.array(geom.vertices.array)
        name  = getattr(element, "name", "") or "Unnamed point set"
        lines = [f"[Point Set: {name}]"]
        lines.append(f"  Points: {len(verts):,}")
        if len(verts):
            centroid = verts.mean(axis=0)
            lines.append(f"  Centroid: X {centroid[0]:.0f}  Y {centroid[1]:.0f}  Z {centroid[2]:.0f}")
        for d in (element.data or []):
            attr_line = _describe_data_attribute(d)
            if attr_line:
                lines.append(f"  Attribute — {attr_line}")
        return "\n".join(lines)
    except Exception as exc:
        logger.debug("PointSet describe failed: %s", exc)
        return None


# ── Data attribute summary ────────────────────────────────────────────────────

def _describe_data_attribute(d) -> str | None:
    try:
        name = getattr(d, "name", "attr") or "attr"
        if not hasattr(d, "array") or d.array is None:
            return None
        arr = np.array(d.array.array)
        if arr.dtype.kind in ("f", "i"):
            valid = arr[np.isfinite(arr.astype(float))]
            if len(valid) == 0:
                return None
            return (
                f"{name}: n={len(valid):,}  "
                f"min={valid.min():.4g}  max={valid.max():.4g}  "
                f"mean={valid.astype(float).mean():.4g}"
            )
        elif arr.dtype.kind in ("U", "S", "O"):
            uniq = list(dict.fromkeys(str(v) for v in arr[:200]))[:20]
            return f"{name} (categorical): {', '.join(uniq)}"
        return None
    except Exception:
        return None


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _pca_orientation(verts: np.ndarray) -> str | None:
    """Return human-readable long axis description from PCA of vertex cloud."""
    try:
        centred = verts - verts.mean(axis=0)
        _, _, Vt = np.linalg.svd(centred, full_matrices=False)
        long_axis = Vt[0]   # principal axis (unit vector)
        # Azimuth: angle from North (Y+) clockwise in horizontal plane
        az = math.degrees(math.atan2(long_axis[0], long_axis[1])) % 360
        # Plunge: angle below horizontal
        horiz_len = math.sqrt(long_axis[0]**2 + long_axis[1]**2)
        plunge = abs(math.degrees(math.atan2(-long_axis[2], horiz_len)))
        # Dimensions along each PC
        proj0 = centred @ Vt[0]
        proj1 = centred @ Vt[1]
        proj2 = centred @ Vt[2]
        dim0 = proj0.max() - proj0.min()
        dim1 = proj1.max() - proj1.min()
        dim2 = proj2.max() - proj2.min()
        return (
            f"Azimuth {az:.0f}°, plunge {plunge:.0f}° — "
            f"long {dim0:.0f}m × intermediate {dim1:.0f}m × short {dim2:.0f}m"
        )
    except Exception:
        return None


def _mesh_volume(verts: np.ndarray, tris: np.ndarray) -> float | None:
    """Approximate signed volume of a closed triangulated mesh."""
    try:
        v0 = verts[tris[:, 0]]
        v1 = verts[tris[:, 1]]
        v2 = verts[tris[:, 2]]
        vol = np.sum(v0 * np.cross(v1, v2)) / 6.0
        return abs(float(vol))
    except Exception:
        return None


def _mesh_surface_area(verts: np.ndarray, tris: np.ndarray) -> float | None:
    """Sum of triangle areas."""
    try:
        v0 = verts[tris[:, 0]]
        v1 = verts[tris[:, 1]]
        v2 = verts[tris[:, 2]]
        cross = np.cross(v1 - v0, v2 - v0)
        area  = 0.5 * np.linalg.norm(cross, axis=1).sum()
        return float(area)
    except Exception:
        return None


# ── pyvista rendering ─────────────────────────────────────────────────────────

_RENDER_W = 1400
_RENDER_H = 1000
_BG = "white"


def _render_figures(
    verts:        np.ndarray,
    tris:         np.ndarray | None,
    grade_values: np.ndarray | None,
    grade_name:   str,
    renders_dir:  Path,
) -> list[dict]:
    """
    Generate 4 standard mining figures using pyvista and save to renders_dir.
    Returns list of manifest entries.
    """
    try:
        import pyvista as pv
    except ImportError:
        logger.warning("pyvista not installed — skipping OMF renders")
        return []

    pv.global_theme.background = _BG
    pv.global_theme.window_size = [_RENDER_W, _RENDER_H]

    # Build mesh
    if tris is not None and len(tris) > 0:
        faces = np.hstack([np.full((len(tris), 1), 3), tris]).ravel()
        mesh  = pv.PolyData(verts.astype(float), faces)
    else:
        # Point cloud fallback (block centroids)
        mesh = pv.PolyData(verts.astype(float))

    # Attach grade scalar
    scalar_name = grade_name if grade_values is not None else None
    if grade_values is not None and len(grade_values) == len(mesh.points):
        mesh[grade_name] = grade_values.astype(float)

    # PCA axes for camera orientation
    centred = verts - verts.mean(axis=0)
    try:
        _, _, Vt = np.linalg.svd(centred[:min(len(centred), 10000)], full_matrices=False)
        pc1, pc2, pc3 = Vt[0], Vt[1], Vt[2]
    except Exception:
        pc1, pc2, pc3 = np.array([1,0,0]), np.array([0,1,0]), np.array([0,0,1])

    centroid = verts.mean(axis=0)
    radius   = np.linalg.norm(verts - centroid, axis=1).max() * 2.5

    manifest: list[dict] = []

    views = [
        {
            "filename":    "3d_perspective.png",
            "camera_pos":  centroid + radius * np.array([0.6, -0.6, 0.5]),
            "description": f"Oblique 3D view from SE, ore body coloured by {grade_name}",
            "caption_hint": "3D Perspective View",
        },
        {
            "filename":    "long_section.png",
            "camera_pos":  centroid + radius * pc3 * np.sign(pc3[2] if pc3[2] != 0 else 1),
            "description": f"Long section looking along strike, grade-coded by {grade_name}",
            "caption_hint": "Long Section",
        },
        {
            "filename":    "cross_section.png",
            "camera_pos":  centroid + radius * pc1,
            "description": f"Cross section perpendicular to strike, coloured by {grade_name}",
            "caption_hint": "Cross Section",
        },
        {
            "filename":    "plan_view.png",
            "camera_pos":  centroid + np.array([0, 0, radius]),
            "description": f"Plan view (top-down) coloured by {grade_name}",
            "caption_hint": "Plan View",
        },
    ]

    for view in views:
        try:
            pl = pv.Plotter(off_screen=True, window_size=[_RENDER_W, _RENDER_H])
            pl.background_color = _BG

            if scalar_name and scalar_name in mesh.array_names:
                pl.add_mesh(
                    mesh,
                    scalars    = scalar_name,
                    cmap       = "hot_r",
                    show_scalar_bar = True,
                    scalar_bar_args = {"title": grade_name, "color": "black"},
                    opacity    = 0.9,
                )
            else:
                pl.add_mesh(mesh, color="#4a90d9", opacity=0.85)

            pl.camera_position = [
                view["camera_pos"].tolist(),
                centroid.tolist(),
                [0, 0, 1],
            ]

            out_path = renders_dir / view["filename"]
            pl.screenshot(str(out_path), return_img=False)
            pl.close()

            manifest.append({
                "filename":    view["filename"],
                "description": view["description"],
            })
            logger.info("OMF render saved: %s", out_path)

        except Exception as exc:
            logger.warning("OMF render failed for %s: %s", view["filename"], exc)

    return manifest

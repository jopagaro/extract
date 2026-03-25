"""
Drill Hole Ingest & Desurveying
================================
Parses collar, survey, and assay/interval tables from CSV or Excel files,
normalises column names, and computes 3-D XYZ traces via the minimum-curvature
method.

Public API
----------
detect_table_type(df) -> str
    Returns "collars" | "surveys" | "assays" | "unknown"

parse_collars(df) -> list[dict]
parse_surveys(df) -> list[dict]
parse_assays(df) -> list[dict]

desurvey_holes(collars, surveys) -> dict[str, list[dict]]
    Returns {hole_id: [{depth, x, y, z}, ...]} — the 3-D trace for every hole.

load_drillhole_file(path) -> dict
    Entry point: load a CSV or XLSX and return
    {"type", "rows", "columns", "hole_count", "row_count", "analytes", "error"}
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Column-name alias sets
# ---------------------------------------------------------------------------

_HOLE_ID_COLS = {"holeid","hole_id","bhid","dhid","drillhole","hole","id","hole_name","dhname","dh_id"}
_X_COLS       = {"x","easting","east","utme","longitude","lon","xcoord","x_coord","x_m"}
_Y_COLS       = {"y","northing","north","utmn","latitude","lat","ycoord","y_coord","y_m"}
_Z_COLS       = {"z","elevation","elev","rl","rl_m","collar_rl","z_collar","altitude","amsl","z_m"}
_DEPTH_COLS   = {"depth","maxdepth","eoh","total_depth","td","eoh_m","depth_m","holelen","holelenm","length","max_depth"}
_AZ_COLS      = {"azimuth","az","azi","bearing","azimuth_deg","dh_azimuth","az_deg"}
_DIP_COLS     = {"dip","dip_deg","inc","inclination","dh_dip","dip_angle","plunge"}
_FROM_COLS    = {"from","from_m","depth_from","frm","from_depth","interval_from","start","start_m","f"}
_TO_COLS      = {"to","to_m","depth_to","to_depth","interval_to","end","end_m","t"}
_SURVEY_AT    = {"at","at_m","survey_depth","depth_m","measure","meas"}

_METAL_HINTS  = {"au","ag","cu","zn","pb","mo","ni","co","fe","as","sb","bi","te",
                 "gold","silver","copper","zinc","lead","molybdenum","nickel","cobalt"}


def _norm(col: str) -> str:
    return col.strip().lower().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "").replace("%", "pct")


def _find(df: pd.DataFrame, aliases: set[str]) -> str | None:
    for col in df.columns:
        if _norm(col) in aliases:
            return col
    return None


def _float(val: Any) -> float | None:
    try:
        v = float(val)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Table-type detection
# ---------------------------------------------------------------------------

def detect_table_type(df: pd.DataFrame) -> str:
    nc = {_norm(c) for c in df.columns}
    has_hole  = bool(nc & _HOLE_ID_COLS)
    has_from  = bool(nc & _FROM_COLS)
    has_to    = bool(nc & _TO_COLS)
    has_xy    = bool(nc & _X_COLS) and bool(nc & _Y_COLS)
    has_dip   = bool(nc & _DIP_COLS)
    has_az    = bool(nc & _AZ_COLS)
    has_depth = bool(nc & (_DEPTH_COLS | _SURVEY_AT))

    if has_from and has_to and has_hole:
        return "assays"
    if has_dip and has_az and has_hole and not has_xy:
        return "surveys"
    if has_dip and has_depth and has_hole and not has_from:
        return "surveys"
    if has_xy and has_hole:
        return "collars"
    if has_depth and has_hole and not has_from:
        return "collars"
    return "unknown"


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_collars(df: pd.DataFrame) -> list[dict]:
    hole = _find(df, _HOLE_ID_COLS)
    x    = _find(df, _X_COLS)
    y    = _find(df, _Y_COLS)
    z    = _find(df, _Z_COLS)
    dep  = _find(df, _DEPTH_COLS)
    az   = _find(df, _AZ_COLS)
    dip  = _find(df, _DIP_COLS)

    out: list[dict] = []
    for _, row in df.iterrows():
        hid = str(row[hole]).strip() if hole else ""
        if not hid or hid.lower() in ("nan", "none", ""):
            continue
        out.append({
            "hole_id":  hid,
            "x":        _float(row[x])   if x   else None,
            "y":        _float(row[y])   if y   else None,
            "z":        _float(row[z])   if z   else None,
            "depth":    _float(row[dep]) if dep else None,
            "azimuth":  _float(row[az])  if az  else None,
            "dip":      _float(row[dip]) if dip else None,
        })
    return out


def parse_surveys(df: pd.DataFrame) -> list[dict]:
    hole  = _find(df, _HOLE_ID_COLS)
    depth = _find(df, _SURVEY_AT | _DEPTH_COLS)
    az    = _find(df, _AZ_COLS)
    dip   = _find(df, _DIP_COLS)

    out: list[dict] = []
    for _, row in df.iterrows():
        hid = str(row[hole]).strip() if hole else ""
        if not hid or hid.lower() in ("nan", "none", ""):
            continue
        out.append({
            "hole_id":  hid,
            "depth":    _float(row[depth]) if depth else None,
            "azimuth":  _float(row[az])    if az    else None,
            "dip":      _float(row[dip])   if dip   else None,
        })
    out.sort(key=lambda s: (s["hole_id"], s["depth"] or 0))
    return out


def parse_assays(df: pd.DataFrame) -> list[dict]:
    hole = _find(df, _HOLE_ID_COLS)
    frm  = _find(df, _FROM_COLS)
    to   = _find(df, _TO_COLS)

    reserved = {c for c in [hole, frm, to] if c}
    analyte_cols = [
        c for c in df.columns
        if c not in reserved and pd.api.types.is_numeric_dtype(df[c])
    ]

    out: list[dict] = []
    for _, row in df.iterrows():
        hid = str(row[hole]).strip() if hole else ""
        if not hid or hid.lower() in ("nan", "none", ""):
            continue
        f = _float(row[frm]) if frm else None
        t = _float(row[to])  if to  else None
        entry: dict = {
            "hole_id": hid,
            "from_m":  f,
            "to_m":    t,
            "length":  round(t - f, 3) if f is not None and t is not None else None,
        }
        for ac in analyte_cols:
            v = _float(row[ac])
            if v is not None:
                entry[_norm(ac)] = v
        out.append(entry)
    out.sort(key=lambda a: (a["hole_id"], a["from_m"] or 0))
    return out


def get_analyte_columns(assays: list[dict]) -> list[str]:
    reserved = {"hole_id", "from_m", "to_m", "length"}
    cols: set[str] = set()
    for row in assays:
        cols.update(k for k in row if k not in reserved and isinstance(row[k], (int, float)))
    priority = sorted(c for c in cols if any(c.startswith(m) or c == m for m in _METAL_HINTS))
    rest     = sorted(c for c in cols if c not in set(priority))
    return priority + rest


# ---------------------------------------------------------------------------
# Desurveying — minimum-curvature method
# ---------------------------------------------------------------------------

def _d2r(d: float) -> float:
    return d * math.pi / 180.0


def _mc_step(d1: float, az1: float, dp1: float,
             d2: float, az2: float, dp2: float) -> tuple[float, float, float]:
    """
    Minimum-curvature step from survey station 1 to 2.

    Convention: dip is degrees below horizontal, positive = downward.
    Returns (dx_east, dy_north, dz_elevation) where dz is negative downward.
    """
    dl = d2 - d1
    az1r, az2r = _d2r(az1), _d2r(az2)
    # inc = inclination from vertical (0=vertical, 90=horizontal)
    inc1 = _d2r(90.0 - abs(dp1))   # treat dip magnitude as below horizontal
    inc2 = _d2r(90.0 - abs(dp2))

    cos_beta = (
        math.cos(inc2 - inc1)
        - math.sin(inc1) * math.sin(inc2) * (1 - math.cos(az2r - az1r))
    )
    beta = math.acos(min(1.0, max(-1.0, cos_beta)))
    rf   = (2 / beta * math.tan(beta / 2)) if abs(beta) > 1e-10 else 1.0

    dx = dl / 2 * rf * (math.sin(inc1) * math.sin(az1r) + math.sin(inc2) * math.sin(az2r))
    dy = dl / 2 * rf * (math.sin(inc1) * math.cos(az1r) + math.sin(inc2) * math.cos(az2r))
    dz = dl / 2 * rf * (math.cos(inc1) + math.cos(inc2)) * -1.0   # negative = downward

    return dx, dy, dz


def desurvey_holes(
    collars: list[dict],
    surveys: list[dict],
) -> dict[str, list[dict]]:
    """
    Compute 3-D traces for all holes.
    Returns {hole_id: [{depth, x, y, z}, ...]}
    """
    by_hole: dict[str, list[dict]] = {}
    for s in surveys:
        by_hole.setdefault(s["hole_id"], []).append(s)

    traces: dict[str, list[dict]] = {}
    for collar in collars:
        hid  = collar["hole_id"]
        cx   = collar.get("x")   or 0.0
        cy   = collar.get("y")   or 0.0
        cz   = collar.get("z")   or 0.0
        tdep = collar.get("depth") or 0.0
        c_az = collar.get("azimuth") or 0.0
        c_dp = collar.get("dip") if collar.get("dip") is not None else -90.0

        srvs = sorted(by_hole.get(hid, []), key=lambda s: s.get("depth") or 0)

        if not srvs:
            srvs = [
                {"depth": 0,    "azimuth": c_az, "dip": c_dp},
                {"depth": tdep, "azimuth": c_az, "dip": c_dp},
            ]
        else:
            if (srvs[0].get("depth") or 0) > 0:
                srvs = [{"depth": 0, "azimuth": srvs[0].get("azimuth") or c_az,
                          "dip": srvs[0].get("dip") if srvs[0].get("dip") is not None else c_dp}] + srvs
            if tdep and (srvs[-1].get("depth") or 0) < tdep:
                last = srvs[-1]
                srvs.append({"depth": tdep, "azimuth": last.get("azimuth") or 0,
                              "dip": last.get("dip") if last.get("dip") is not None else -90})

        trace: list[dict] = [{"depth": 0.0, "x": cx, "y": cy, "z": cz}]
        x, y, z = cx, cy, cz

        for i in range(1, len(srvs)):
            s1, s2 = srvs[i - 1], srvs[i]
            d1, d2 = (s1.get("depth") or 0), (s2.get("depth") or 0)
            a1 = s1.get("azimuth") or 0;  a2 = s2.get("azimuth") or a1
            p1 = s1.get("dip") if s1.get("dip") is not None else -90
            p2 = s2.get("dip") if s2.get("dip") is not None else p1
            try:
                dx, dy, dz = _mc_step(d1, a1, p1, d2, a2, p2)
            except Exception:
                dl = d2 - d1
                dx = dl * math.cos(_d2r(abs(p1))) * math.sin(_d2r(a1))
                dy = dl * math.cos(_d2r(abs(p1))) * math.cos(_d2r(a1))
                dz = -dl * math.sin(_d2r(abs(p1)))
            x += dx; y += dy; z += dz
            trace.append({"depth": round(d2, 2), "x": round(x, 2), "y": round(y, 2), "z": round(z, 2)})

        traces[hid] = trace
    return traces


# ---------------------------------------------------------------------------
# Assay statistics
# ---------------------------------------------------------------------------

def compute_assay_stats(assays: list[dict], analyte: str) -> dict:
    vals = [r[analyte] for r in assays if r.get(analyte) is not None]
    if not vals:
        return {"count": 0}
    arr = np.array(vals, dtype=float)
    return {
        "count":  int(len(arr)),
        "min":    round(float(np.nanmin(arr)), 4),
        "max":    round(float(np.nanmax(arr)), 4),
        "mean":   round(float(np.nanmean(arr)), 4),
        "median": round(float(np.nanmedian(arr)), 4),
        "p90":    round(float(np.nanpercentile(arr, 90)), 4),
        "p95":    round(float(np.nanpercentile(arr, 95)), 4),
    }


# ---------------------------------------------------------------------------
# File loader
# ---------------------------------------------------------------------------

def load_drillhole_file(path: Path) -> dict:
    """
    Load a CSV or Excel file and auto-detect its drill-hole table type.
    Returns {"type", "rows", "columns", "hole_count", "row_count", "analytes", "error"}
    """
    try:
        suffix = path.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            df = pd.read_excel(path, sheet_name=0, dtype=str)
        elif suffix == ".csv":
            df = pd.read_csv(path, dtype=str)
        else:
            return {"type": "unknown", "rows": [], "columns": [], "hole_count": 0,
                    "row_count": 0, "analytes": [], "error": f"Unsupported: {suffix}"}

        df = df.dropna(how="all", axis=1).dropna(how="all", axis=0).reset_index(drop=True)
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col], errors="ignore")
            except Exception:
                pass

        ttype = detect_table_type(df)

        if ttype == "collars":
            rows = parse_collars(df)
        elif ttype == "surveys":
            rows = parse_surveys(df)
        elif ttype == "assays":
            rows = parse_assays(df)
        else:
            rows = df.head(200).to_dict(orient="records")

        hole_ids = {r.get("hole_id", "") for r in rows if r.get("hole_id")}
        analytes = get_analyte_columns(rows) if ttype == "assays" else []

        return {
            "type":       ttype,
            "rows":       rows,
            "columns":    list(df.columns),
            "hole_count": len(hole_ids),
            "row_count":  len(rows),
            "analytes":   analytes,
            "error":      None,
        }
    except Exception as exc:
        return {"type": "unknown", "rows": [], "columns": [], "hole_count": 0,
                "row_count": 0, "analytes": [], "error": str(exc)}

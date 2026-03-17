"""
Diff builder.

Compares two runs of the same project and produces a structured diff
of headline economics and geological picture changes.

Useful for:
  - Showing what changed between a re-run after new data was added
  - Flagging when key economic outputs move materially
  - Audit trail for report revisions
"""

from __future__ import annotations

from typing import Any

from engine.core.logging import get_logger
from engine.runs.run_manager import _read_manifest, list_runs
from engine.core.paths import run_root

log = get_logger(__name__)

# A change is "material" if it moves by more than this threshold
_MATERIAL_THRESHOLD_PERCENT = 5.0


def build_run_diff(
    project_id: str,
    run_id_before: str,
    run_id_after: str,
    before_summary: dict[str, Any] | None = None,
    after_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Compare two run ValuationSummary dicts and return a structured diff.

    before_summary / after_summary: to_dict() output from ValuationSummary.
    If not provided, attempts to load summary.json from the run folder.

    Returns a diff dict with:
      - changed_fields: list of {field, before, after, change_percent, material}
      - material_changes: same list filtered to material changes only
      - summary: human-readable change summary string
    """
    if before_summary is None:
        before_summary = _load_summary(project_id, run_id_before)
    if after_summary is None:
        after_summary = _load_summary(project_id, run_id_after)

    if not before_summary or not after_summary:
        log.warning(
            "Cannot build diff — summary missing for one or both runs (%s, %s)",
            run_id_before, run_id_after,
        )
        return {"error": "summary_missing", "changed_fields": [], "material_changes": []}

    numeric_fields = [
        "npv_musd",
        "irr_percent",
        "payback_years",
        "peak_capex_musd",
        "total_initial_capex_musd",
        "total_sustaining_capex_musd",
        "average_annual_revenue_musd",
        "average_annual_opex_musd",
        "average_aisc",
        "mine_life_years",
    ]

    changed_fields = []
    for field in numeric_fields:
        v_before = before_summary.get(field)
        v_after = after_summary.get(field)
        if v_before is None and v_after is None:
            continue
        if v_before == v_after:
            continue

        change_pct: float | None = None
        if v_before and v_before != 0:
            change_pct = ((v_after or 0) - v_before) / abs(v_before) * 100

        material = (
            change_pct is not None and abs(change_pct) >= _MATERIAL_THRESHOLD_PERCENT
        )

        changed_fields.append({
            "field": field,
            "before": v_before,
            "after": v_after,
            "change_percent": round(change_pct, 1) if change_pct is not None else None,
            "material": material,
        })

    material_changes = [c for c in changed_fields if c["material"]]

    # Build a short summary string
    if not changed_fields:
        summary = "No headline economic changes between runs."
    elif not material_changes:
        summary = (
            f"{len(changed_fields)} field(s) changed, none materially "
            f"(>{_MATERIAL_THRESHOLD_PERCENT:.0f}% threshold)."
        )
    else:
        parts = []
        for c in material_changes:
            sign = "+" if (c["change_percent"] or 0) > 0 else ""
            parts.append(f"{c['field']}: {sign}{c['change_percent']}%")
        summary = f"{len(material_changes)} material change(s): {'; '.join(parts)}."

    return {
        "project_id": project_id,
        "run_id_before": run_id_before,
        "run_id_after": run_id_after,
        "scenario": after_summary.get("scenario"),
        "changed_fields": changed_fields,
        "material_changes": material_changes,
        "summary": summary,
    }


def _load_summary(project_id: str, run_id: str) -> dict[str, Any]:
    """Try to load summary.json from the run folder."""
    import json
    summary_path = run_root(project_id, run_id) / "summary.json"
    if not summary_path.exists():
        return {}
    with summary_path.open("r", encoding="utf-8") as f:
        return json.load(f)

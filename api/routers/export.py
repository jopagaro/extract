"""
Export router — download report outputs as formatted files.

Endpoints:
  GET /projects/{project_id}/reports/{run_id}/export?format=json
  GET /projects/{project_id}/reports/{run_id}/export?format=md
  GET /projects/{project_id}/reports/{run_id}/export?format=txt
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from engine.core.paths import project_root, run_root

router = APIRouter(tags=["export"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project_exists(project_id: str) -> None:
    if not project_root(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")


def _get_all_sections(project_id: str, run_id: str) -> dict[str, object]:
    rdir = run_root(project_id, run_id)
    if not rdir.exists():
        return {}
    sections = {}
    for jf in sorted(rdir.glob("*.json")):
        if jf.name == "run_status.json":
            continue
        section_name = jf.stem.replace(f"{run_id}_", "")
        with jf.open() as f:
            sections[section_name] = json.load(f)
    return sections


def _sections_to_markdown(project_id: str, run_id: str, sections: dict) -> str:
    """Convert structured JSON sections into a clean Markdown document."""
    lines = [
        f"# Mining Project Analysis Report",
        f"",
        f"**Project:** {project_id}  ",
        f"**Run ID:** {run_id}  ",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"",
        f"---",
        f"",
    ]

    section_titles = {
        "project_facts": "Project Facts",
        "geology_summary": "Geology",
        "economics_summary": "Economics",
        "risk_summary": "Risks",
        "permitting_summary": "Permitting",
        "financing_risk": "Financing Risk",
        "contradictions": "Internal Contradictions",
        "missing_data": "Data Gaps",
        "assumptions": "Assumption Challenges",
        "geology_score": "Geology Score",
        "economics_score": "Economics Score",
        "financing_score": "Financing Score",
        "permitting_score": "Permitting Score",
        "overall_score": "Overall Project Score",
    }

    for section_key, content in sections.items():
        title = section_titles.get(section_key, section_key.replace("_", " ").title())
        lines.append(f"## {title}")
        lines.append("")
        lines.append(_format_section(content))
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _format_section(content: object, indent: int = 0) -> str:
    """Recursively format a JSON structure as readable Markdown."""
    pad = "  " * indent
    if isinstance(content, dict):
        parts = []
        for k, v in content.items():
            label = k.replace("_", " ").title()
            if isinstance(v, (dict, list)):
                parts.append(f"{pad}**{label}:**")
                parts.append(_format_section(v, indent + 1))
            else:
                parts.append(f"{pad}**{label}:** {v}")
        return "\n".join(parts)
    elif isinstance(content, list):
        if not content:
            return f"{pad}_(none)_"
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(_format_section(item, indent))
                parts.append("")
            else:
                parts.append(f"{pad}- {item}")
        return "\n".join(parts)
    else:
        return f"{pad}{content}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/reports/{run_id}/export")
def export_report(
    project_id: str,
    run_id: str,
    format: Literal["json", "md", "txt"] = Query("md", description="Export format: json, md, or txt"),
) -> Response:
    """
    Download a completed report in the requested format.

    - **json**: Raw structured data (all sections combined)
    - **md**: Clean Markdown document, suitable for pasting into Notion, Word, or a PDF converter
    - **txt**: Plain text version of the Markdown
    """
    _project_exists(project_id)
    sections = _get_all_sections(project_id, run_id)
    if not sections:
        raise HTTPException(status_code=404, detail="No report output found for this run.")

    filename_base = f"{project_id}_{run_id}_report"

    if format == "json":
        payload = json.dumps(
            {"project_id": project_id, "run_id": run_id, "sections": sections},
            indent=2,
        )
        return Response(
            content=payload,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.json"'},
        )

    md_content = _sections_to_markdown(project_id, run_id, sections)

    if format == "txt":
        # Strip markdown syntax for plain text
        import re
        txt = re.sub(r"#{1,6} ", "", md_content)
        txt = re.sub(r"\*\*(.+?)\*\*", r"\1", txt)
        txt = re.sub(r"_(.+?)_", r"\1", txt)
        return Response(
            content=txt,
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.txt"'},
        )

    return Response(
        content=md_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename_base}.md"'},
    )

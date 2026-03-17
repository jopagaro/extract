"""
Export router — download report outputs as formatted files.

Endpoints:
  GET /projects/{project_id}/reports/{run_id}/export?format=json
  GET /projects/{project_id}/reports/{run_id}/export?format=md
  GET /projects/{project_id}/reports/{run_id}/export?format=txt
  GET /projects/{project_id}/reports/{run_id}/export?format=pdf
"""

from __future__ import annotations

import io
import json
import re
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


SECTION_TITLES = {
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


def _format_section(content: object, indent: int = 0) -> str:
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


def _sections_to_markdown(project_id: str, run_id: str, sections: dict) -> str:
    lines = [
        "# Mining Project Analysis Report",
        "",
        f"**Project:** {project_id}  ",
        f"**Run ID:** {run_id}  ",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "---",
        "",
    ]
    for section_key, content in sections.items():
        title = SECTION_TITLES.get(section_key, section_key.replace("_", " ").title())
        lines.append(f"## {title}")
        lines.append("")
        lines.append(_format_section(content))
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def _flatten_for_pdf(content: object, lines: list[str], indent: int = 0) -> None:
    """Recursively flatten content into plain text lines for PDF.

    Long prose strings are emitted without a label so they render as
    flowing paragraphs.  Short scalars use "Label: value" format.
    """
    pad = "  " * indent
    if isinstance(content, dict):
        for k, v in content.items():
            label = k.replace("_", " ").title()
            if isinstance(v, str) and len(v) > 80:
                # Prose paragraph — no label, just the text
                lines.append(v)
                lines.append("")
            elif isinstance(v, list):
                if v:
                    lines.append(f"{pad}{label}:")
                    _flatten_for_pdf(v, lines, indent + 1)
                    lines.append("")
            elif isinstance(v, dict):
                _flatten_for_pdf(v, lines, indent)
            elif v is not None and str(v).strip():
                lines.append(f"{pad}{label}: {v}")
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                _flatten_for_pdf(item, lines, indent)
                lines.append("")
            else:
                lines.append(f"{pad}• {item}")
    else:
        if str(content).strip():
            lines.append(f"{pad}{content}")


def _safe(text: str) -> str:
    """Replace Unicode characters that Helvetica (Latin-1) can't encode."""
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2012": "-",  # dashes
        "\u2018": "'", "\u2019": "'",                   # smart single quotes
        "\u201c": '"', "\u201d": '"',                   # smart double quotes
        "\u2022": "*", "\u2026": "...",                  # bullet, ellipsis
        "\u00b0": "deg", "\u00b2": "2", "\u00b3": "3",  # degree, superscripts
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _generate_pdf(project_id: str, run_id: str, sections: dict) -> bytes:
    from fpdf import FPDF

    class ReportPDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(110, 110, 115)
            self.cell(0, 8, "Mining Intelligence Platform - Confidential", align="L")
            self.set_text_color(110, 110, 115)
            self.cell(0, 0, f"Page {self.page_no()}", align="R")
            self.ln(4)
            self.set_draw_color(220, 220, 220)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(4)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(174, 174, 178)
            self.cell(0, 10, "For internal research purposes only. Not investment advice.", align="C")

    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    # Title
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(29, 29, 31)
    pdf.ln(4)
    pdf.cell(0, 12, "Mining Project Analysis Report", ln=True)

    # Meta
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(110, 110, 115)
    pdf.cell(0, 6, _safe(f"Project: {project_id.replace('_', ' ').title()}"), ln=True)
    pdf.cell(0, 6, _safe(f"Run ID: {run_id}"), ln=True)
    pdf.cell(0, 6, _safe(f"Generated: {datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')}"), ln=True)
    pdf.ln(4)

    # Disclaimer box — use cell width explicitly
    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 110)
    pdf.multi_cell(
        page_w, 5,
        "This report is generated by an AI system for internal research purposes only. "
        "It does not constitute investment advice or a formal technical study. "
        "All figures should be verified against primary source documents.",
    )
    pdf.ln(6)

    # Sections
    for section_key, content in sections.items():
        title = SECTION_TITLES.get(section_key, section_key.replace("_", " ").title())

        # Section heading
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(29, 29, 31)
        pdf.set_fill_color(245, 245, 247)
        pdf.cell(page_w, 9, _safe(title), ln=True, fill=True)
        pdf.ln(1)

        # Section content
        flat_lines: list[str] = []
        _flatten_for_pdf(content, flat_lines)

        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(45, 45, 48)
        for line in flat_lines:
            line = _safe(str(line))
            if not line.strip():
                pdf.ln(2)
                continue
            # Truncate extremely long words that would break the layout
            words = line.split()
            line = " ".join(w[:80] if len(w) > 80 else w for w in words)
            colon_pos = line.find(":")
            if colon_pos != -1 and colon_pos < 28 and not line.strip().startswith("•"):
                # Short "Label: value" line — bold the label
                label_part = line[:colon_pos + 1]
                value_part = line[colon_pos + 1:]
                pdf.set_font("Helvetica", "B", 9.5)
                pdf.write(5, label_part)
                pdf.set_font("Helvetica", "", 9.5)
                pdf.write(5, value_part)
                pdf.ln(5)
            else:
                pdf.multi_cell(page_w, 5, line)

        pdf.ln(5)
        pdf.set_draw_color(220, 220, 220)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(5)

    return bytes(pdf.output())


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/reports/{run_id}/export")
def export_report(
    project_id: str,
    run_id: str,
    format: Literal["json", "md", "txt", "pdf"] = Query("pdf", description="Export format"),
) -> Response:
    _project_exists(project_id)
    sections = _get_all_sections(project_id, run_id)
    if not sections:
        raise HTTPException(status_code=404, detail="No report output found for this run.")

    filename_base = f"{project_id}_{run_id}_report"

    if format == "json":
        payload = json.dumps({"project_id": project_id, "run_id": run_id, "sections": sections}, indent=2)
        return Response(
            content=payload,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.json"'},
        )

    if format == "pdf":
        pdf_bytes = _generate_pdf(project_id, run_id, sections)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'},
        )

    md_content = _sections_to_markdown(project_id, run_id, sections)

    if format == "txt":
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

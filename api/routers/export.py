"""
Export router — download report outputs as formatted files.

Endpoints:
  GET /projects/{project_id}/reports/{run_id}/export?format=json
  GET /projects/{project_id}/reports/{run_id}/export?format=md
  GET /projects/{project_id}/reports/{run_id}/export?format=txt
  GET /projects/{project_id}/reports/{run_id}/export?format=pdf
"""

from __future__ import annotations

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
    # Current pipeline sections
    "07_assembly":           "Analyst Narrative",
    "02_market_intelligence": "Market Intelligence",
    "01_project_facts":      "Project Facts",
    "03_geology":            "Geology & Resources",
    "04_economics":          "Economics & Financial Analysis",
    "05_risks":              "Risks & Uncertainties",
    "06_dcf_model":          "DCF Financial Model",
    "00_data_sources":       "Appendix A — Source Documents",
    # Legacy keys (kept for backward compat)
    "project_facts":        "Project Facts",
    "geology_summary":      "Geology",
    "economics_summary":    "Economics",
    "risk_summary":         "Risks",
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
        "# Extract — Technical Analysis Report",
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
    """Sanitise text so Helvetica (Latin-1) can always encode it.

    Applies known unicode → ASCII replacements first, then falls back to
    latin-1 encode/decode with replacement for anything still outside range.
    """
    replacements = {
        # Dashes
        "\u2014": "-", "\u2013": "-", "\u2012": "-", "\u2015": "-",
        # Quotes
        "\u2018": "'", "\u2019": "'", "\u201a": "'",
        "\u201c": '"', "\u201d": '"', "\u201e": '"',
        # Bullets / ellipsis
        "\u2022": "-", "\u2023": "-", "\u25cf": "-",
        "\u2026": "...",
        # Math / units
        "\u00b0": "deg", "\u00b2": "2", "\u00b3": "3",
        "\u00d7": "x",  "\u00f7": "/", "\u2248": "~",
        "\u2264": "<=", "\u2265": ">=",
        "\u00b1": "+/-",
        # Currency
        "\u20ac": "EUR", "\u00a3": "GBP", "\u00a5": "JPY",
        # Misc
        "\u00ae": "(R)", "\u00a9": "(C)", "\u2122": "(TM)",
        "\u00a0": " ",   # non-breaking space
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    # Final safety net: drop anything still outside Latin-1
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _write_pdf_prose(pdf, text: str, page_w: float, font_size: float = 10.5) -> None:
    """Emit flowing prose paragraphs — split on double newlines."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for para in paragraphs:
        para = _safe(para)
        words = para.split()
        para = " ".join(w[:120] if len(w) > 120 else w for w in words)
        pdf.set_font("Helvetica", "", font_size)
        pdf.set_text_color(45, 45, 48)
        pdf.multi_cell(page_w, 5.5, para)
        pdf.ln(3)


def _write_pdf_section_header(pdf, title: str, subtitle: str | None, section_num: str | None, page_w: float) -> None:
    """Draw a clean section header with a top rule, number label, and serif-style title."""
    pdf.set_draw_color(11, 35, 71)   # navy
    pdf.set_line_width(0.6)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + page_w, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(5)

    if section_num:
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(155, 163, 175)
        pdf.cell(0, 5, _safe(f"SECTION {section_num}"), ln=True)
        pdf.ln(1)

    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(11, 35, 71)
    pdf.multi_cell(page_w, 7, _safe(title))

    if subtitle:
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(107, 114, 128)
        pdf.multi_cell(page_w, 5, _safe(subtitle))

    pdf.ln(5)


def _write_pdf_content(pdf, content: object, page_w: float) -> None:
    """Render a section's content: prose flows freely, scalars use label: value, lists bullet."""
    flat_lines: list[str] = []
    _flatten_for_pdf(content, flat_lines)

    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(45, 45, 48)

    for line in flat_lines:
        line = _safe(str(line))
        if not line.strip():
            pdf.ln(2)
            continue
        words = line.split()
        line = " ".join(w[:120] if len(w) > 120 else w for w in words)

        if line.startswith("•"):
            # Bullet item — indent
            pdf.set_x(pdf.l_margin + 4)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(page_w - 4, 5, line)
            pdf.set_x(pdf.l_margin)
        else:
            colon_pos = line.find(":")
            if colon_pos != -1 and colon_pos < 30 and "\n" not in line[:colon_pos]:
                # Short "Label: value" — bold the label
                label_part = line[:colon_pos + 1]
                value_part = line[colon_pos + 1:]
                pdf.set_font("Helvetica", "B", 10)
                pdf.write(5.5, label_part)
                pdf.set_font("Helvetica", "", 10.5)
                pdf.write(5.5, value_part)
                pdf.ln(5.5)
            else:
                pdf.set_font("Helvetica", "", 10.5)
                pdf.multi_cell(page_w, 5.5, line)

    pdf.ln(4)


# Section display order for PDF
_PDF_SECTION_ORDER = [
    "07_assembly",
    "02_market_intelligence",
    "03_geology",
    "04_economics",
    "05_risks",
    "06_dcf_model",
    "00_data_sources",
    "01_project_facts",
]

_PDF_SECTION_META: dict[str, dict] = {
    "07_assembly":            {"title": "Analyst Narrative",                  "subtitle": None,                                              "num": None,  "layer": "narrative"},
    "02_market_intelligence": {"title": "Market Intelligence",                "subtitle": "Live prices, web-sourced context, macro factors",  "num": None,  "layer": "market"},
    "03_geology":             {"title": "Geology & Resources",                "subtitle": "Deposit geology and resource assessment",           "num": "1",   "layer": "detail"},
    "04_economics":           {"title": "Economics & Financial Analysis",     "subtitle": "Capital costs, operating costs, projections",       "num": "2",   "layer": "detail"},
    "05_risks":               {"title": "Risks & Uncertainties",              "subtitle": "Material risks and mitigations",                   "num": "3",   "layer": "detail"},
    "06_dcf_model":           {"title": "DCF Financial Model",                "subtitle": "Computed discounted cash flow analysis",            "num": "4",   "layer": "detail"},
    "00_data_sources":        {"title": "Appendix A - Source Documents",      "subtitle": "All documents used in this analysis",              "num": None,  "layer": "appendix"},
    "01_project_facts":       {"title": "Project Facts",                      "subtitle": None,                                              "num": None,  "layer": "appendix"},
}


def _generate_pdf(project_id: str, run_id: str, sections: dict) -> bytes:
    from fpdf import FPDF

    raw_dir = project_root(project_id) / "raw" / "documents"
    renders_dir = project_root(project_id) / "raw" / "renders"
    IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tiff"}

    class ReportPDF(FPDF):
        def header(self):
            if self.page_no() == 1:
                return  # cover page — no running header
            self.set_font("Helvetica", "", 8)
            self.set_text_color(156, 163, 175)
            self.cell(0, 6, "Extract - Confidential", align="L")
            self.cell(0, 0, f"Page {self.page_no() - 1}", align="R")
            self.ln(3)
            self.set_draw_color(229, 231, 235)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(4)

        def footer(self):
            self.set_y(-14)
            self.set_font("Helvetica", "I", 7.5)
            self.set_text_color(174, 174, 178)
            self.cell(0, 8, "For internal research purposes only. Not investment advice.", align="C")

    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(16, 16, 16)
    page_w = 210 - 32  # A4 minus margins

    # ── Cover page ───────────────────────────────────────────────────────────
    pdf.add_page()

    # Gold accent bar
    pdf.set_fill_color(176, 141, 60)
    pdf.rect(0, 0, 210, 5, "F")
    pdf.ln(16)

    # Eyebrow
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(176, 141, 60)
    pdf.cell(0, 5, _safe("EXTRACT \u2014 TECHNICAL ANALYSIS REPORT"), ln=True)
    pdf.ln(6)

    # Project name
    project_display = _safe(project_id.replace("_", " ").replace("-", " ").title())
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(11, 35, 71)
    pdf.multi_cell(page_w, 11, project_display)
    pdf.ln(4)

    # Study level / stage from assembly if available
    assembly = sections.get("07_assembly", {})
    if isinstance(assembly, dict):
        stage = assembly.get("project_stage") or assembly.get("study_level") or ""
        if stage and stage.lower() not in ("unknown", "not specified", ""):
            pdf.set_font("Helvetica", "", 12)
            pdf.set_text_color(107, 114, 128)
            pdf.cell(0, 6, _safe(str(stage)), ln=True)

    pdf.ln(10)

    # Horizontal rule
    pdf.set_draw_color(229, 231, 235)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + page_w, pdf.get_y())
    pdf.ln(8)

    # Meta grid (2-up)
    meta_items = [
        ("Report Date", datetime.now(timezone.utc).strftime("%B %d, %Y")),
        ("Run ID",       run_id),
        ("Classification", "Internal — Confidential"),
        ("Prepared By",  "Extract AI"),
    ]
    col_w = page_w / 2
    for i in range(0, len(meta_items), 2):
        y_start = pdf.get_y()
        for j in range(2):
            if i + j >= len(meta_items):
                break
            label, value = meta_items[i + j]
            pdf.set_xy(pdf.l_margin + j * col_w, y_start)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(156, 163, 175)
            pdf.cell(col_w, 4, _safe(label.upper()), ln=False)
            pdf.set_xy(pdf.l_margin + j * col_w, y_start + 4)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(29, 29, 31)
            pdf.multi_cell(col_w - 4, 5, _safe(value))
        pdf.set_y(max(pdf.get_y(), y_start + 14))
        pdf.ln(4)

    pdf.ln(6)
    pdf.set_draw_color(229, 231, 235)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + page_w, pdf.get_y())
    pdf.ln(8)

    # Disclaimer
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(107, 114, 128)
    pdf.multi_cell(
        page_w, 5,
        "This report is generated by an AI system for internal research purposes only. "
        "It does not constitute investment advice or a formal technical study. "
        "All figures and conclusions should be verified against primary source documents.",
    )

    # ── Content pages ─────────────────────────────────────────────────────────
    ordered_keys = _PDF_SECTION_ORDER + [k for k in sections if k not in _PDF_SECTION_ORDER]

    for section_key in ordered_keys:
        if section_key not in sections:
            continue
        content = sections[section_key]
        meta = _PDF_SECTION_META.get(section_key)
        title = meta["title"] if meta else SECTION_TITLES.get(section_key, section_key.replace("_", " ").title())
        subtitle = meta.get("subtitle") if meta else None
        num = meta.get("num") if meta else None

        pdf.add_page()
        _write_pdf_section_header(pdf, title, subtitle, num, page_w)

        # Market intelligence section
        if section_key == "02_market_intelligence" and isinstance(content, dict):
            if content.get("error"):
                pdf.set_font("Helvetica", "I", 10)
                pdf.set_text_color(107, 114, 128)
                pdf.multi_cell(page_w, 5, _safe(str(content["error"])))
            else:
                # As-of date notice
                gathered_at = content.get("gathered_at", "")
                if gathered_at:
                    pdf.set_font("Helvetica", "I", 9)
                    pdf.set_text_color(107, 114, 128)
                    pdf.cell(0, 5, _safe(f"Data gathered: {gathered_at}"), ln=True)
                    pdf.ln(3)

                # Live price callouts (from yfinance)
                live_prices = content.get("live_prices", {}).get("prices", {})
                macro_inds  = content.get("macro_indicators", {}).get("indicators", {})
                all_prices  = list(live_prices.items()) + [
                    (k, {"price": v["value"], "unit": v["unit"]})
                    for k, v in macro_inds.items()
                    if v.get("value") is not None
                ]

                if all_prices:
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.set_text_color(156, 163, 175)
                    pdf.cell(0, 5, "LIVE MARKET DATA", ln=True)
                    pdf.ln(2)
                    col_count = min(4, len(all_prices))
                    col = page_w / col_count
                    y0 = pdf.get_y()
                    for i, (name, data) in enumerate(all_prices[:8]):
                        x = pdf.l_margin + (i % col_count) * col
                        y = y0 + (i // col_count) * 20
                        price_val = data.get("price") or data.get("value") or ""
                        price_str = f"{price_val:,.2f}" if isinstance(price_val, (int, float)) else str(price_val)
                        unit_str  = _safe(str(data.get("unit", "")))
                        pdf.set_xy(x, y)
                        pdf.set_font("Helvetica", "B", 12)
                        pdf.set_text_color(176, 141, 60)   # gold accent
                        pdf.cell(col - 2, 6, _safe(f"{price_str} {unit_str}"), ln=False)
                        pdf.set_xy(x, y + 7)
                        pdf.set_font("Helvetica", "", 7.5)
                        pdf.set_text_color(107, 114, 128)
                        pdf.cell(col - 2, 4, _safe(name.replace("_", " ").title()), ln=False)
                    rows = (len(all_prices[:8]) + col_count - 1) // col_count
                    pdf.set_y(y0 + rows * 20 + 4)
                    pdf.set_draw_color(229, 231, 235)
                    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + page_w, pdf.get_y())
                    pdf.ln(6)

                # Project intelligence
                proj_intel = content.get("project_intelligence", {})
                if proj_intel.get("findings"):
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.set_text_color(156, 163, 175)
                    subject = _safe(proj_intel.get("search_subject", "Project"))
                    pdf.cell(0, 5, f"PROJECT INTELLIGENCE: {subject}", ln=True)
                    pdf.ln(2)
                    _write_pdf_prose(pdf, proj_intel["findings"], page_w, font_size=10)
                    pdf.ln(4)

                # Commodity market
                comm = content.get("commodity_market", {})
                if comm.get("analysis"):
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.set_text_color(156, 163, 175)
                    pdf.cell(0, 5, _safe(f"COMMODITY MARKET: {comm.get('commodity', '').upper()}"), ln=True)
                    pdf.ln(2)
                    _write_pdf_prose(pdf, comm["analysis"], page_w, font_size=10)
                    pdf.ln(4)

                # Macro context
                macro = content.get("macro_context", {})
                if macro.get("analysis"):
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.set_text_color(156, 163, 175)
                    pdf.cell(0, 5, "MACROECONOMIC CONTEXT", ln=True)
                    pdf.ln(2)
                    _write_pdf_prose(pdf, macro["analysis"], page_w, font_size=10)

                # Notice
                notice = content.get("notice")
                if notice:
                    pdf.ln(6)
                    pdf.set_font("Helvetica", "I", 8)
                    pdf.set_text_color(156, 163, 175)
                    pdf.multi_cell(page_w, 4.5, _safe(notice))

        # Narrative section — extract prose fields directly
        elif section_key == "07_assembly" and isinstance(content, dict):
            # Key callouts table
            callouts = content.get("key_callouts")
            if isinstance(callouts, list) and callouts:
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(156, 163, 175)
                pdf.cell(0, 5, "KEY METRICS", ln=True)
                pdf.ln(2)
                col = page_w / min(4, len(callouts))
                y0 = pdf.get_y()
                for i, c in enumerate(callouts[:8]):
                    x = pdf.l_margin + (i % 4) * col
                    y = y0 + (i // 4) * 22
                    pdf.set_xy(x, y)
                    pdf.set_font("Helvetica", "B", 13)
                    pdf.set_text_color(11, 35, 71)
                    pdf.cell(col - 2, 7, _safe(str(c.get("value", ""))), ln=False)
                    pdf.set_xy(x, y + 7)
                    pdf.set_font("Helvetica", "", 7.5)
                    pdf.set_text_color(107, 114, 128)
                    pdf.cell(col - 2, 4, _safe(str(c.get("label", ""))), ln=False)
                rows = (len(callouts) + 3) // 4
                pdf.set_y(y0 + rows * 22 + 4)
                pdf.set_draw_color(229, 231, 235)
                pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + page_w, pdf.get_y())
                pdf.ln(6)

            # Narrative prose
            narrative = content.get("narrative")
            if isinstance(narrative, str):
                _write_pdf_prose(pdf, narrative, page_w)

            conclusion = content.get("analyst_conclusion")
            if isinstance(conclusion, str):
                pdf.ln(2)
                pdf.set_draw_color(11, 35, 71)
                pdf.set_line_width(0.6)
                pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + page_w, pdf.get_y())
                pdf.set_line_width(0.2)
                pdf.ln(5)
                pdf.set_font("Helvetica", "I", 10.5)
                pdf.set_text_color(45, 45, 48)
                pdf.multi_cell(page_w, 5.5, _safe(conclusion))

            flags = content.get("consistency_flags")
            if isinstance(flags, list) and flags:
                pdf.ln(6)
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(146, 104, 10)
                pdf.cell(0, 5, "CONSISTENCY NOTES", ln=True)
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(107, 74, 0)
                for flag in flags:
                    pdf.multi_cell(page_w, 5, _safe(f"- {flag}"))

        elif section_key == "00_data_sources" and isinstance(content, dict):
            notice = content.get("notice")
            if isinstance(notice, str):
                pdf.set_font("Helvetica", "I", 9.5)
                pdf.set_text_color(107, 114, 128)
                pdf.multi_cell(page_w, 5, _safe(notice))
                pdf.ln(4)

            files = content.get("source_files", [])
            if files:
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(156, 163, 175)
                pdf.cell(0, 5, f"SOURCE DOCUMENTS ({len(files)})", ln=True)
                pdf.ln(2)
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(45, 45, 48)
                for f in files:
                    pdf.cell(0, 5.5, _safe(f"  {chr(10003)}  {f}"), ln=True)

            # Embedded images
            image_files = content.get("image_files", [])
            render_files = content.get("render_files", [])
            all_images = list(dict.fromkeys(image_files + render_files))  # dedup, preserve order
            shown = 0
            for img_name in all_images:
                img_path = raw_dir / img_name
                if not img_path.exists():
                    img_path = renders_dir / img_name
                if not img_path.exists() or img_path.suffix.lower() not in IMAGE_EXTS:
                    continue
                if shown == 0:
                    pdf.ln(6)
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.set_text_color(156, 163, 175)
                    pdf.cell(0, 5, "VISUAL REFERENCES", ln=True)
                    pdf.ln(3)
                try:
                    # Cap image width to page width; preserve aspect ratio
                    pdf.image(str(img_path), w=min(page_w, 140))
                    pdf.set_font("Helvetica", "I", 8)
                    pdf.set_text_color(156, 163, 175)
                    pdf.cell(0, 4, _safe(img_name), ln=True)
                    pdf.ln(4)
                    shown += 1
                except Exception:
                    pass

        elif section_key == "06_dcf_model" and isinstance(content, dict):
            if not content.get("model_ran"):
                reason = content.get("reason", "DCF model did not run.")
                pdf.set_font("Helvetica", "I", 10)
                pdf.set_text_color(107, 114, 128)
                pdf.multi_cell(page_w, 5, _safe(str(reason)))
            else:
                notes = content.get("assumptions_notes")
                if isinstance(notes, str):
                    pdf.set_font("Helvetica", "I", 9.5)
                    pdf.set_text_color(107, 114, 128)
                    pdf.multi_cell(page_w, 5, _safe(f"Model assumptions: {notes}"))
                    pdf.ln(4)
                summary = content.get("summary")
                if isinstance(summary, dict):
                    pdf.set_font("Helvetica", "B", 8.5)
                    pdf.set_text_color(11, 35, 71)
                    pdf.cell(0, 5, "VALUATION SUMMARY", ln=True)
                    pdf.ln(2)
                    skip = {"project_id", "scenario", "after_tax", "notes", "aisc_unit"}
                    for k, v in summary.items():
                        if k in skip or v is None:
                            continue
                        label = k.replace("_", " ").title()
                        val = f"{v:,}" if isinstance(v, (int, float)) else str(v)
                        pdf.set_font("Helvetica", "B", 9.5)
                        pdf.set_text_color(45, 45, 48)
                        pdf.write(5.5, _safe(f"{label}: "))
                        pdf.set_font("Helvetica", "", 9.5)
                        pdf.write(5.5, _safe(val))
                        pdf.ln(5.5)
        else:
            _write_pdf_content(pdf, content, page_w)

        pdf.ln(6)

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

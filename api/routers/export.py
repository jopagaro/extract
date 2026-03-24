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
    "07_assembly":           "Analyst Narrative",
    "02_market_intelligence": "Market Intelligence",
    "01_project_facts":      "Project Facts",
    "03_geology":            "Geology & Resources",
    "04_economics":          "Economics & Financial Analysis",
    "05_risks":              "Risks & Uncertainties",
    "06_dcf_model":          "DCF Financial Model",
    "00_data_sources":       "Appendix A — Source Documents",
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
    pad = "  " * indent
    if isinstance(content, dict):
        for k, v in content.items():
            label = k.replace("_", " ").title()
            if isinstance(v, str) and len(v) > 80:
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
                lines.append(f"{pad}* {item}")
    else:
        if str(content).strip():
            lines.append(f"{pad}{content}")


def _safe(text: str) -> str:
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2012": "-", "\u2015": "-",
        "\u2018": "'", "\u2019": "'", "\u201a": "'",
        "\u201c": '"', "\u201d": '"', "\u201e": '"',
        "\u2022": "-", "\u2023": "-", "\u25cf": "-",
        "\u2026": "...",
        "\u00b0": "deg", "\u00b2": "2", "\u00b3": "3",
        "\u00d7": "x",  "\u00f7": "/", "\u2248": "~",
        "\u2264": "<=", "\u2265": ">=",
        "\u00b1": "+/-",
        "\u20ac": "EUR", "\u00a3": "GBP", "\u00a5": "JPY",
        "\u00ae": "(R)", "\u00a9": "(C)", "\u2122": "(TM)",
        "\u00a0": " ",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode("latin-1", errors="replace").decode("latin-1")


# ---------------------------------------------------------------------------
# PDF design system
# ---------------------------------------------------------------------------

# Palette
_INK       = (15, 20, 30)       # near-black for body text
_NAVY      = (11, 35, 71)       # headings / accents
_GOLD      = (176, 141, 60)     # primary accent
_SILVER    = (140, 148, 160)    # secondary / captions
_RULE      = (220, 224, 230)    # light dividers
_BG_LIGHT  = (248, 248, 250)    # alternating row / card bg
_BG_DARK   = (22, 32, 52)       # cover dark band
_WHITE     = (255, 255, 255)
_AMBER     = (180, 120, 20)     # warning/flag text
_AMBER_BG  = (255, 248, 230)    # warning card bg

# Layout
_LM = 18   # left margin
_RM = 18   # right margin
_PW = 210 - _LM - _RM   # usable page width (A4)


def _set_body(pdf, size: float = 10.0, style: str = "") -> None:
    pdf.set_font("Helvetica", style, size)
    pdf.set_text_color(*_INK)


def _set_label(pdf, size: float = 7.5) -> None:
    pdf.set_font("Helvetica", "B", size)
    pdf.set_text_color(*_SILVER)


def _set_heading(pdf, size: float = 13.0) -> None:
    pdf.set_font("Helvetica", "B", size)
    pdf.set_text_color(*_NAVY)


def _rule(pdf, color=_RULE, lw: float = 0.25) -> None:
    pdf.set_draw_color(*color)
    pdf.set_line_width(lw)
    pdf.line(_LM, pdf.get_y(), _LM + _PW, pdf.get_y())


def _prose(pdf, text: str, line_h: float = 5.8, size: float = 10.0) -> None:
    """Render flowing prose, split on double newlines."""
    _set_body(pdf, size)
    for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
        para = _safe(" ".join(para.split()))
        pdf.multi_cell(_PW, line_h, para)
        pdf.ln(3.5)


def _section_header(pdf, title: str, subtitle: str | None = None, num: str | None = None) -> None:
    """Elegant section header with gold left accent bar."""
    # Gold left bar
    pdf.set_fill_color(*_GOLD)
    pdf.rect(_LM, pdf.get_y(), 2.5, 14 if not subtitle else 18, "F")

    x_text = _LM + 7
    y0 = pdf.get_y()

    if num:
        pdf.set_xy(x_text, y0 + 0.5)
        _set_label(pdf, 7)
        pdf.cell(0, 4, _safe(f"SECTION {num}"), ln=True)
        y0 = pdf.get_y()

    pdf.set_xy(x_text, y0)
    _set_heading(pdf, 14)
    pdf.cell(0, 7, _safe(title), ln=True)

    if subtitle:
        pdf.set_x(x_text)
        _set_body(pdf, 8.5)
        pdf.set_text_color(*_SILVER)
        pdf.cell(0, 5, _safe(subtitle), ln=True)

    pdf.ln(7)


def _metric_cards(pdf, items: list[tuple[str, str, str | None]], cols: int = 4) -> None:
    """Render a row of KPI cards with value + label + optional context."""
    if not items:
        return
    col_w = _PW / cols
    card_h = 18
    y0 = pdf.get_y()

    for i, (value, label, context) in enumerate(items[:cols * 2]):
        col = i % cols
        row = i // cols
        x = _LM + col * col_w
        y = y0 + row * (card_h + 3)

        # Card background
        pdf.set_fill_color(*_BG_LIGHT)
        pdf.rect(x, y, col_w - 2, card_h, "F")

        # Gold top accent line
        pdf.set_fill_color(*_GOLD)
        pdf.rect(x, y, col_w - 2, 1.5, "F")

        # Value
        pdf.set_xy(x + 4, y + 3.5)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*_NAVY)
        pdf.cell(col_w - 8, 6, _safe(str(value)), ln=False)

        # Label
        pdf.set_xy(x + 4, y + 10)
        _set_label(pdf, 7.5)
        pdf.cell(col_w - 8, 4, _safe(str(label)), ln=False)

    rows = (len(items[:cols * 2]) + cols - 1) // cols
    pdf.set_y(y0 + rows * (card_h + 3) + 5)
    _rule(pdf)
    pdf.ln(6)


def _price_tiles(pdf, prices: list[tuple[str, str, str]]) -> None:
    """Compact price tiles: value + unit on top, name below."""
    if not prices:
        return
    cols = min(4, len(prices))
    tile_w = _PW / cols
    tile_h = 16
    y0 = pdf.get_y()

    for i, (name, value, unit) in enumerate(prices[:8]):
        col = i % cols
        row = i // cols
        x = _LM + col * tile_w
        y = y0 + row * (tile_h + 2)

        pdf.set_fill_color(*_BG_LIGHT)
        pdf.rect(x, y, tile_w - 1.5, tile_h, "F")

        pdf.set_xy(x + 3, y + 2.5)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*_GOLD)
        display = f"{value} {unit}".strip()
        pdf.cell(tile_w - 6, 5.5, _safe(display), ln=False)

        pdf.set_xy(x + 3, y + 9)
        _set_label(pdf, 7)
        pdf.cell(tile_w - 6, 4, _safe(name.replace("_", " ").title()), ln=False)

    rows = (len(prices[:8]) + cols - 1) // cols
    pdf.set_y(y0 + rows * (tile_h + 2) + 6)


def _table(pdf, headers: list[str], rows: list[list[str]], col_widths: list[float] | None = None) -> None:
    """Render a clean table with header row and alternating body rows."""
    if not rows:
        return
    if col_widths is None:
        col_widths = [_PW / len(headers)] * len(headers)

    row_h = 6.5

    # Header
    pdf.set_fill_color(*_NAVY)
    pdf.set_text_color(*_WHITE)
    pdf.set_font("Helvetica", "B", 8.5)
    x0 = _LM
    for i, h in enumerate(headers):
        pdf.set_xy(x0, pdf.get_y())
        pdf.cell(col_widths[i], row_h, _safe(h), fill=True, border=0)
        x0 += col_widths[i]
    pdf.ln(row_h)

    # Body rows
    for r_idx, row in enumerate(rows):
        if pdf.get_y() > 260:
            pdf.add_page()
        fill = r_idx % 2 == 0
        pdf.set_fill_color(*_BG_LIGHT)
        pdf.set_text_color(*_INK)
        pdf.set_font("Helvetica", "", 8.5)
        x0 = _LM
        for i, cell in enumerate(row):
            pdf.set_xy(x0, pdf.get_y())
            pdf.cell(col_widths[i], row_h, _safe(str(cell)), fill=fill, border=0)
            x0 += col_widths[i]
        pdf.ln(row_h)

    pdf.ln(5)


def _flag_box(pdf, flags: list[str]) -> None:
    """Amber warning box for consistency flags."""
    if not flags:
        return
    pdf.set_fill_color(*_AMBER_BG)
    pdf.set_draw_color(*_GOLD)
    pdf.set_line_width(0.4)

    y0 = pdf.get_y()
    box_h = 7 + len(flags) * 5.5 + 4
    pdf.rect(_LM, y0, _PW, box_h, "FD")

    pdf.set_xy(_LM + 4, y0 + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*_AMBER)
    pdf.cell(0, 4.5, "CONSISTENCY NOTES", ln=True)

    for flag in flags:
        pdf.set_x(_LM + 4)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_AMBER)
        pdf.cell(0, 5.5, _safe(f"  -  {flag}"), ln=True)

    pdf.ln(6)


# ---------------------------------------------------------------------------
# Section display order
# ---------------------------------------------------------------------------

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
    "07_assembly":            {"title": "Analyst Narrative",               "subtitle": None,                                             "num": None},
    "02_market_intelligence": {"title": "Market Intelligence",             "subtitle": "Live prices and web-sourced context",            "num": None},
    "03_geology":             {"title": "Geology & Resources",             "subtitle": "Deposit geology and resource assessment",        "num": "1"},
    "04_economics":           {"title": "Economics & Financial Analysis",  "subtitle": "Capital costs, operating costs, projections",    "num": "2"},
    "05_risks":               {"title": "Risks & Uncertainties",           "subtitle": "Material risks and mitigations",                 "num": "3"},
    "06_dcf_model":           {"title": "DCF Financial Model",             "subtitle": "Discounted cash flow analysis",                  "num": "4"},
    "00_data_sources":        {"title": "Appendix A — Source Documents",   "subtitle": "All documents used in this analysis",            "num": None},
    "01_project_facts":       {"title": "Project Facts",                   "subtitle": None,                                             "num": None},
}


# ---------------------------------------------------------------------------
# PDF generator
# ---------------------------------------------------------------------------

def _generate_pdf(project_id: str, run_id: str, sections: dict) -> bytes:
    from fpdf import FPDF

    raw_dir     = project_root(project_id) / "raw" / "documents"
    renders_dir = project_root(project_id) / "raw" / "renders"
    IMAGE_EXTS  = {".png", ".jpg", ".jpeg", ".tiff"}

    class ReportPDF(FPDF):
        def header(self):
            if self.page_no() == 1:
                return
            # Running header
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(*_SILVER)
            self.set_y(10)
            proj_display = _safe(project_id.replace("_", " ").replace("-", " ").title())
            self.cell(0, 5, proj_display, align="L")
            self.set_y(10)
            self.cell(0, 5, "Extract  —  Confidential", align="R")
            self.set_y(16)
            _rule(self, _RULE, 0.2)
            self.ln(4)

        def footer(self):
            self.set_y(-13)
            _rule(self, _RULE, 0.2)
            self.ln(1)
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(*_SILVER)
            self.cell(0, 5, "For internal research purposes only. Not investment advice.", align="L")
            self.set_y(-13)
            self.set_font("Helvetica", "", 7.5)
            self.cell(0, 5, f"{self.page_no() - 1}", align="R")

    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(_LM, 16, _RM)

    # ── Cover page ──────────────────────────────────────────────────────────
    pdf.add_page()

    # Full-width dark header band
    pdf.set_fill_color(*_BG_DARK)
    pdf.rect(0, 0, 210, 72, "F")

    # Gold accent stripe at top
    pdf.set_fill_color(*_GOLD)
    pdf.rect(0, 0, 210, 3, "F")

    # "EXTRACT" wordmark
    pdf.set_xy(_LM, 12)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*_GOLD)
    pdf.cell(0, 5, "EXTRACT", ln=True)

    # Report type label
    pdf.set_x(_LM)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(160, 170, 185)
    pdf.cell(0, 5, "TECHNICAL ANALYSIS REPORT", ln=True)

    # Project name — large
    pdf.set_xy(_LM, 32)
    proj_display = _safe(project_id.replace("_", " ").replace("-", " ").title())
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*_WHITE)
    pdf.multi_cell(_PW, 11, proj_display)

    # Study level sub-label
    assembly = sections.get("07_assembly", {})
    stage = ""
    if isinstance(assembly, dict):
        stage = assembly.get("project_stage") or assembly.get("study_level") or ""
    if stage and stage.lower() not in ("unknown", "not specified", ""):
        pdf.set_x(_LM)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(160, 170, 185)
        pdf.cell(0, 6, _safe(str(stage)), ln=True)

    # Move below the dark band
    pdf.set_y(82)
    pdf.set_text_color(*_INK)

    # Meta grid (2 columns × 2 rows)
    meta = [
        ("REPORT DATE",    datetime.now(timezone.utc).strftime("%B %d, %Y")),
        ("CLASSIFICATION", "Internal — Confidential"),
        ("RUN ID",         run_id),
        ("PREPARED BY",    "Extract AI"),
    ]
    col_w = _PW / 2
    for i in range(0, len(meta), 2):
        y_row = pdf.get_y()
        for j in range(2):
            if i + j >= len(meta):
                break
            lbl, val = meta[i + j]
            x = _LM + j * col_w
            pdf.set_xy(x, y_row)
            _set_label(pdf, 7)
            pdf.cell(col_w, 4.5, lbl, ln=False)
            pdf.set_xy(x, y_row + 4.5)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*_INK)
            pdf.multi_cell(col_w - 4, 5.5, _safe(val))
        pdf.set_y(max(pdf.get_y(), y_row + 13))

    pdf.ln(10)
    _rule(pdf, _RULE)
    pdf.ln(8)

    # Disclaimer
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*_SILVER)
    pdf.multi_cell(
        _PW, 5,
        "This report is generated by an AI system for internal research purposes only. "
        "It does not constitute investment advice or a formal technical study. "
        "All figures and conclusions should be verified against primary source documents.",
    )

    # ── Content pages ────────────────────────────────────────────────────────
    ordered_keys = _PDF_SECTION_ORDER + [k for k in sections if k not in _PDF_SECTION_ORDER]

    for section_key in ordered_keys:
        if section_key not in sections:
            continue
        content = sections[section_key]
        meta_s  = _PDF_SECTION_META.get(section_key, {})
        title    = meta_s.get("title") or SECTION_TITLES.get(section_key, section_key.replace("_", " ").title())
        subtitle = meta_s.get("subtitle")
        num      = meta_s.get("num")

        pdf.add_page()
        _section_header(pdf, title, subtitle, num)

        # ── Assembly / Narrative ──────────────────────────────────────────
        if section_key == "07_assembly" and isinstance(content, dict):
            # Key callouts
            callouts = content.get("key_callouts")
            if isinstance(callouts, list) and callouts:
                items = [(c.get("value", ""), c.get("label", ""), c.get("context")) for c in callouts]
                _metric_cards(pdf, items, cols=min(4, len(items)))

            # Narrative prose
            narrative = content.get("narrative")
            if isinstance(narrative, str):
                _prose(pdf, narrative)

            # Analyst conclusion — indented block
            conclusion = content.get("analyst_conclusion")
            if isinstance(conclusion, str):
                pdf.ln(3)
                pdf.set_fill_color(*_BG_LIGHT)
                pdf.set_draw_color(*_NAVY)
                pdf.set_line_width(0.4)
                y0 = pdf.get_y()
                # draw left accent
                pdf.set_fill_color(*_NAVY)
                pdf.rect(_LM, y0, 2, 30, "F")
                pdf.set_xy(_LM + 6, y0 + 3)
                _set_label(pdf, 7.5)
                pdf.cell(0, 4, "ANALYST CONCLUSION", ln=True)
                pdf.set_x(_LM + 6)
                pdf.set_font("Helvetica", "I", 10)
                pdf.set_text_color(*_INK)
                pdf.multi_cell(_PW - 6, 5.5, _safe(conclusion))
                pdf.ln(5)

            # Consistency flags
            flags = content.get("consistency_flags")
            if isinstance(flags, list) and flags:
                _flag_box(pdf, [str(f) for f in flags])

        # ── Market Intelligence ───────────────────────────────────────────
        elif section_key == "02_market_intelligence" and isinstance(content, dict):
            if content.get("error"):
                _set_body(pdf, 10, "I")
                pdf.set_text_color(*_SILVER)
                pdf.multi_cell(_PW, 5.5, _safe(str(content["error"])))
            else:
                gathered_at = content.get("gathered_at", "")
                if gathered_at:
                    _set_label(pdf, 8)
                    pdf.cell(0, 5, _safe(f"Data gathered: {gathered_at}"), ln=True)
                    pdf.ln(3)

                # Live prices
                live_prices = content.get("live_prices", {}).get("prices", {})
                macro_inds  = content.get("macro_indicators", {}).get("indicators", {})
                price_tiles: list[tuple[str, str, str]] = []
                for name, data in live_prices.items():
                    v = data.get("price")
                    u = data.get("unit", "")
                    if v is not None:
                        price_tiles.append((name, f"{v:,.2f}" if isinstance(v, (int, float)) else str(v), str(u)))
                for name, data in macro_inds.items():
                    v = data.get("value")
                    u = data.get("unit", "")
                    if v is not None:
                        price_tiles.append((name, f"{v:,.2f}" if isinstance(v, (int, float)) else str(v), str(u)))

                if price_tiles:
                    _set_label(pdf, 8)
                    pdf.cell(0, 5, "LIVE MARKET DATA", ln=True)
                    pdf.ln(3)
                    _price_tiles(pdf, price_tiles)
                    pdf.ln(4)

                # Project intelligence
                proj_intel = content.get("project_intelligence", {})
                if proj_intel.get("findings"):
                    subject = _safe(proj_intel.get("search_subject", "Project"))
                    _set_label(pdf, 8)
                    pdf.cell(0, 5, f"PROJECT INTELLIGENCE: {subject}", ln=True)
                    pdf.ln(2)
                    _prose(pdf, proj_intel["findings"], size=9.5)

                # Commodity market
                comm = content.get("commodity_market", {})
                if comm.get("analysis"):
                    _set_label(pdf, 8)
                    pdf.cell(0, 5, _safe(f"COMMODITY MARKET: {comm.get('commodity', '').upper()}"), ln=True)
                    pdf.ln(2)
                    _prose(pdf, comm["analysis"], size=9.5)

                # Macro context
                macro = content.get("macro_context", {})
                if macro.get("analysis"):
                    _set_label(pdf, 8)
                    pdf.cell(0, 5, "MACROECONOMIC CONTEXT", ln=True)
                    pdf.ln(2)
                    _prose(pdf, macro["analysis"], size=9.5)

                notice = content.get("notice")
                if notice:
                    pdf.ln(4)
                    pdf.set_font("Helvetica", "I", 8)
                    pdf.set_text_color(*_SILVER)
                    pdf.multi_cell(_PW, 4.5, _safe(notice))

        # ── DCF Model ─────────────────────────────────────────────────────
        elif section_key == "06_dcf_model" and isinstance(content, dict):
            if not content.get("model_ran"):
                reason = content.get("reason", "DCF model did not run.")
                _set_body(pdf, 10, "I")
                pdf.set_text_color(*_SILVER)
                pdf.multi_cell(_PW, 5.5, _safe(str(reason)))
            else:
                notes = content.get("assumptions_notes")
                if isinstance(notes, str):
                    _set_body(pdf, 9, "I")
                    pdf.set_text_color(*_SILVER)
                    pdf.multi_cell(_PW, 5, _safe(notes))
                    pdf.ln(5)

                summary = content.get("summary")
                if isinstance(summary, dict):
                    _set_label(pdf, 8)
                    pdf.cell(0, 5, "VALUATION SUMMARY", ln=True)
                    pdf.ln(3)
                    skip = {"project_id", "scenario", "after_tax", "notes", "aisc_unit"}
                    kpi_items = []
                    for k, v in summary.items():
                        if k in skip or v is None:
                            continue
                        label = k.replace("_", " ").title()
                        val   = f"{v:,}" if isinstance(v, (int, float)) else str(v)
                        kpi_items.append((val, label, None))
                    if kpi_items:
                        _metric_cards(pdf, kpi_items, cols=min(4, len(kpi_items)))

                # Cash flow table
                cash_flows = content.get("cash_flows")
                if isinstance(cash_flows, list) and cash_flows:
                    _set_label(pdf, 8)
                    pdf.cell(0, 5, "ANNUAL CASH FLOWS", ln=True)
                    pdf.ln(3)

                    def _fmt(v):
                        if v is None: return "-"
                        if isinstance(v, (int, float)): return f"{v:,.0f}"
                        return str(v)

                    headers = ["Year", "Revenue", "OpEx", "CapEx", "Tax", "FCF", "NPV (PV)"]
                    col_widths = [18, 30, 27, 27, 22, 28, 28]
                    rows_data = []
                    for cf in cash_flows[:20]:
                        rows_data.append([
                            str(cf.get("year", "")),
                            _fmt(cf.get("gross_revenue")),
                            _fmt(cf.get("opex")),
                            _fmt(cf.get("capex")),
                            _fmt(cf.get("tax")),
                            _fmt(cf.get("free_cash_flow")),
                            _fmt(cf.get("present_value")),
                        ])
                    _table(pdf, headers, rows_data, col_widths)

        # ── Data sources ──────────────────────────────────────────────────
        elif section_key == "00_data_sources" and isinstance(content, dict):
            notice = content.get("notice")
            if isinstance(notice, str):
                _set_body(pdf, 9, "I")
                pdf.set_text_color(*_SILVER)
                pdf.multi_cell(_PW, 5, _safe(notice))
                pdf.ln(5)

            files = content.get("source_files", [])
            if files:
                _set_label(pdf, 8)
                pdf.cell(0, 5, f"SOURCE DOCUMENTS ({len(files)})", ln=True)
                pdf.ln(3)
                for i, f in enumerate(files):
                    fill = i % 2 == 0
                    if fill:
                        pdf.set_fill_color(*_BG_LIGHT)
                        pdf.rect(_LM, pdf.get_y(), _PW, 6, "F")
                    _set_body(pdf, 9.5)
                    pdf.cell(_PW, 6, _safe(f"  {f}"), ln=True)
                pdf.ln(5)

            # Embedded images
            image_files  = content.get("image_files", [])
            render_files = content.get("render_files", [])
            all_images   = list(dict.fromkeys(image_files + render_files))
            shown = 0
            for img_name in all_images:
                img_path = raw_dir / img_name
                if not img_path.exists():
                    img_path = renders_dir / img_name
                if not img_path.exists() or img_path.suffix.lower() not in IMAGE_EXTS:
                    continue
                if shown == 0:
                    pdf.ln(4)
                    _set_label(pdf, 8)
                    pdf.cell(0, 5, "VISUAL REFERENCES", ln=True)
                    pdf.ln(3)
                try:
                    pdf.image(str(img_path), w=min(_PW, 130))
                    _set_body(pdf, 8, "I")
                    pdf.set_text_color(*_SILVER)
                    pdf.cell(0, 4, _safe(img_name), ln=True)
                    pdf.ln(4)
                    shown += 1
                except Exception:
                    pass

        # ── Generic section (geology, economics, risk, project facts) ─────
        else:
            flat_lines: list[str] = []
            _flatten_for_pdf(content, flat_lines)

            for line in flat_lines:
                line = _safe(str(line))
                if not line.strip():
                    pdf.ln(2)
                    continue
                words = line.split()
                line = " ".join(w[:120] if len(w) > 120 else w for w in words)

                if line.startswith("*"):
                    # Bullet
                    pdf.set_x(_LM + 4)
                    _set_body(pdf, 10)
                    pdf.multi_cell(_PW - 4, 5.8, line)
                    pdf.set_x(_LM)
                elif line.endswith(":") and len(line) < 50:
                    # Sub-label
                    pdf.ln(2)
                    _set_label(pdf, 8)
                    pdf.cell(0, 5, line.upper(), ln=True)
                else:
                    colon_pos = line.find(":")
                    if 0 < colon_pos < 35 and "\n" not in line[:colon_pos]:
                        label_part = line[:colon_pos + 1]
                        value_part = line[colon_pos + 1:]
                        _set_body(pdf, 10, "B")
                        pdf.write(5.8, label_part)
                        _set_body(pdf, 10)
                        pdf.write(5.8, value_part)
                        pdf.ln(5.8)
                    else:
                        # Long prose
                        _set_body(pdf, 10)
                        pdf.multi_cell(_PW, 5.8, line)
                        pdf.ln(1)

        pdf.ln(4)

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

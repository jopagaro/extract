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
    "07_assembly":            "Analyst Narrative",
    "02_market_intelligence": "Market Intelligence",
    "01_project_facts":       "Project Facts",
    "03_geology":             "Geology & Resources",
    "04_economics":           "Economics & Financial Analysis",
    "05_risks":               "Risks & Uncertainties",
    "06_dcf_model":           "DCF Financial Model",
    "00_data_sources":        "Appendix A — Source Documents",
    "project_facts":          "Project Facts",
    "geology_summary":        "Geology",
    "economics_summary":      "Economics",
    "risk_summary":           "Risks",
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
# Design tokens  — Substack-style: off-white, dark ink, one accent bar
# ---------------------------------------------------------------------------

_BG         = (247, 244, 238)   # warm off-white page background
_INK        = (26, 23, 19)      # near-black body text
_INK_SOFT   = (80, 75, 68)      # secondary text / captions
_GRAY       = (150, 144, 136)   # labels, metadata, rules
_RULE_CLR   = (210, 206, 198)   # horizontal dividers
_ACCENT     = (44, 74, 62)      # dark muted green — top bar only
_WHITE      = (255, 255, 255)

# Layout
_LM  = 22   # left margin
_RM  = 22   # right margin
_PW  = 210 - _LM - _RM   # usable width on A4


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _bg(pdf) -> None:
    """Fill the current page with the off-white background."""
    pdf.set_fill_color(*_BG)
    pdf.rect(0, 0, 210, 297, "F")


def _accent_bar(pdf) -> None:
    """Thin colored stripe across the very top of the page."""
    pdf.set_fill_color(*_ACCENT)
    pdf.rect(0, 0, 210, 4, "F")


def _rule(pdf, y: float | None = None) -> None:
    lw_prev = pdf.line_width
    pdf.set_draw_color(*_RULE_CLR)
    pdf.set_line_width(0.25)
    y = y if y is not None else pdf.get_y()
    pdf.line(_LM, y, _LM + _PW, y)
    pdf.set_line_width(lw_prev)


def _label(pdf, text: str) -> None:
    """Small all-caps gray label — used above section titles."""
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(*_GRAY)
    pdf.cell(0, 5, _safe(text.upper()), ln=True)


def _h1(pdf, text: str) -> None:
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*_INK)
    pdf.multi_cell(_PW, 9, _safe(text))
    pdf.ln(1)


def _h2(pdf, text: str) -> None:
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*_INK)
    pdf.multi_cell(_PW, 7, _safe(text))
    pdf.ln(2)


def _body(pdf, text: str, size: float = 10.5) -> None:
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(*_INK)
    pdf.multi_cell(_PW, 6.2, _safe(text))


def _prose(pdf, text: str, size: float = 10.5) -> None:
    """Render multi-paragraph prose split on blank lines."""
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(*_INK)
    for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
        pdf.multi_cell(_PW, 6.2, _safe(" ".join(para.split())))
        pdf.ln(4)


def _caption(pdf, text: str) -> None:
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*_GRAY)
    pdf.multi_cell(_PW, 5, _safe(text))


def _section_break(pdf, title: str, subtitle: str | None = None, num: str | None = None) -> None:
    """Clean section opener: optional number label, bold title, optional subtitle, rule."""
    pdf.ln(2)
    if num:
        _label(pdf, f"Section {num}")
        pdf.ln(1)
    _h2(pdf, title)
    if subtitle:
        _caption(pdf, subtitle)
        pdf.ln(1)
    _rule(pdf)
    pdf.ln(6)


# ---------------------------------------------------------------------------
# Data renderers
# ---------------------------------------------------------------------------

def _kv_list(pdf, items: list[tuple[str, str]]) -> None:
    """Render a clean label: value list, no backgrounds."""
    for label, value in items:
        if not value or str(value).strip() in ("", "None", "null"):
            continue
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_INK_SOFT)
        pdf.write(6, _safe(label + ":  "))
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*_INK)
        pdf.write(6, _safe(str(value)))
        pdf.ln(6)


def _simple_table(pdf, headers: list[str], rows: list[list[str]], col_widths: list[float] | None = None) -> None:
    """Minimal table: thin gray borders, no background fills."""
    if not rows:
        return
    if col_widths is None:
        col_widths = [_PW / len(headers)] * len(headers)
    row_h = 6.5

    # Header row
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*_INK_SOFT)
    pdf.set_draw_color(*_RULE_CLR)
    pdf.set_line_width(0.25)
    x0 = _LM
    for i, h in enumerate(headers):
        pdf.set_xy(x0, pdf.get_y())
        pdf.cell(col_widths[i], row_h, _safe(h), border="B")
        x0 += col_widths[i]
    pdf.ln(row_h)

    # Body
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*_INK)
    for row in rows:
        if pdf.get_y() > 265:
            pdf.add_page()
        x0 = _LM
        for i, cell in enumerate(row):
            pdf.set_xy(x0, pdf.get_y())
            pdf.cell(col_widths[i], row_h, _safe(str(cell)), border=0)
            x0 += col_widths[i]
        pdf.ln(row_h)
        # thin rule between rows
        _rule(pdf)

    pdf.ln(6)


# ---------------------------------------------------------------------------
# Section order
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
    "07_assembly":            {"title": "Analyst Narrative",               "subtitle": None,                                          "num": None},
    "02_market_intelligence": {"title": "Market Intelligence",             "subtitle": "Live prices and current market context",      "num": None},
    "03_geology":             {"title": "Geology & Resources",             "subtitle": "Deposit geology and resource assessment",     "num": "1"},
    "04_economics":           {"title": "Economics & Financial Analysis",  "subtitle": "Capital costs, operating costs, projections", "num": "2"},
    "05_risks":               {"title": "Risks & Uncertainties",           "subtitle": "Material risks and mitigations",              "num": "3"},
    "06_dcf_model":           {"title": "DCF Financial Model",             "subtitle": "Discounted cash flow analysis",               "num": "4"},
    "00_data_sources":        {"title": "Appendix A — Source Documents",   "subtitle": None,                                          "num": None},
    "01_project_facts":       {"title": "Project Facts",                   "subtitle": None,                                          "num": None},
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
            _bg(self)
            _accent_bar(self)
            if self.page_no() == 1:
                return
            # Subtle running header
            self.set_y(10)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*_GRAY)
            proj = _safe(project_id.replace("_", " ").replace("-", " ").title())
            self.cell(0, 5, proj, align="L")
            self.set_y(10)
            self.cell(0, 5, "Extract", align="R")
            self.set_y(17)
            _rule(self)
            self.ln(5)

        def footer(self):
            self.set_y(-14)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*_GRAY)
            self.cell(0, 6, "For internal research purposes only. Not investment advice.", align="L")
            self.set_y(-14)
            self.cell(0, 6, f"{self.page_no() - 1}", align="R")

    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(_LM, 18, _RM)

    # ── Cover ────────────────────────────────────────────────────────────────
    pdf.add_page()

    pdf.set_y(22)

    # Publication label
    _label(pdf, "Extract  —  Technical Analysis Report")
    pdf.ln(5)

    # Project title
    proj_display = project_id.replace("_", " ").replace("-", " ").title()
    _h1(pdf, proj_display)
    pdf.ln(3)

    # Study level / stage
    assembly = sections.get("07_assembly", {})
    stage = ""
    if isinstance(assembly, dict):
        stage = assembly.get("project_stage") or assembly.get("study_level") or ""
    if stage and stage.lower() not in ("unknown", "not specified", ""):
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(*_INK_SOFT)
        pdf.cell(0, 7, _safe(str(stage)), ln=True)
        pdf.ln(2)

    _rule(pdf)
    pdf.ln(6)

    # Meta line
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_GRAY)
    pdf.cell(0, 5, _safe(f"{date_str}  —  Run {run_id}  —  Internal / Confidential"), ln=True)
    pdf.ln(10)

    # Disclaimer
    _caption(pdf,
        "This report is generated by an AI system for internal research purposes only. "
        "It does not constitute investment advice or a formal technical study. "
        "All figures and conclusions should be verified against primary source documents."
    )

    # ── Content pages ────────────────────────────────────────────────────────
    ordered_keys = _PDF_SECTION_ORDER + [k for k in sections if k not in _PDF_SECTION_ORDER]

    for section_key in ordered_keys:
        if section_key not in sections:
            continue
        content  = sections[section_key]
        meta_s   = _PDF_SECTION_META.get(section_key, {})
        title    = meta_s.get("title") or SECTION_TITLES.get(section_key, section_key.replace("_", " ").title())
        subtitle = meta_s.get("subtitle")
        num      = meta_s.get("num")

        pdf.add_page()
        _section_break(pdf, title, subtitle, num)

        # ── Analyst Narrative ─────────────────────────────────────────────
        if section_key == "07_assembly" and isinstance(content, dict):
            # Key callouts — plain inline list, no boxes
            callouts = content.get("key_callouts")
            if isinstance(callouts, list) and callouts:
                _label(pdf, "Key metrics")
                pdf.ln(2)
                for c in callouts:
                    v = _safe(str(c.get("value", "")))
                    l = _safe(str(c.get("label", "")))
                    ctx = c.get("context", "")
                    pdf.set_font("Helvetica", "B", 10.5)
                    pdf.set_text_color(*_INK)
                    pdf.write(6.5, v + "  ")
                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(*_INK_SOFT)
                    pdf.write(6.5, l + ("  —  " + _safe(str(ctx)) if ctx else ""))
                    pdf.ln(7)
                pdf.ln(4)
                _rule(pdf)
                pdf.ln(6)

            # Narrative prose
            narrative = content.get("narrative")
            if isinstance(narrative, str):
                _prose(pdf, narrative)

            # Analyst conclusion
            conclusion = content.get("analyst_conclusion")
            if isinstance(conclusion, str):
                pdf.ln(4)
                _rule(pdf)
                pdf.ln(5)
                _label(pdf, "Analyst conclusion")
                pdf.ln(2)
                pdf.set_font("Helvetica", "I", 10.5)
                pdf.set_text_color(*_INK)
                pdf.multi_cell(_PW, 6.2, _safe(conclusion))
                pdf.ln(2)

            # Consistency flags — plain text, no box
            flags = content.get("consistency_flags")
            if isinstance(flags, list) and flags:
                pdf.ln(4)
                _rule(pdf)
                pdf.ln(5)
                _label(pdf, "Consistency notes")
                pdf.ln(2)
                for flag in flags:
                    pdf.set_font("Helvetica", "", 9.5)
                    pdf.set_text_color(*_INK_SOFT)
                    pdf.multi_cell(_PW, 5.8, _safe(f"- {flag}"))
                    pdf.ln(1)

        # ── Market Intelligence ───────────────────────────────────────────
        elif section_key == "02_market_intelligence" and isinstance(content, dict):
            if content.get("error"):
                _caption(pdf, str(content["error"]))
            else:
                gathered_at = content.get("gathered_at", "")
                if gathered_at:
                    _caption(pdf, f"Data gathered: {gathered_at}")
                    pdf.ln(4)

                # Live prices — inline label: value list
                live_prices = content.get("live_prices", {}).get("prices", {})
                macro_inds  = content.get("macro_indicators", {}).get("indicators", {})
                price_items: list[tuple[str, str]] = []
                for name, data in live_prices.items():
                    v = data.get("price")
                    u = data.get("unit", "")
                    if v is not None:
                        val_str = f"{v:,.2f} {u}".strip() if isinstance(v, (int, float)) else f"{v} {u}".strip()
                        price_items.append((name.replace("_", " ").title(), val_str))
                for name, data in macro_inds.items():
                    v = data.get("value")
                    u = data.get("unit", "")
                    if v is not None:
                        val_str = f"{v:,.2f} {u}".strip() if isinstance(v, (int, float)) else f"{v} {u}".strip()
                        price_items.append((name.replace("_", " ").title(), val_str))

                if price_items:
                    _label(pdf, "Live market data")
                    pdf.ln(2)
                    _kv_list(pdf, price_items)
                    pdf.ln(4)
                    _rule(pdf)
                    pdf.ln(6)

                # Project intelligence
                proj_intel = content.get("project_intelligence", {})
                if proj_intel.get("findings"):
                    subject = proj_intel.get("search_subject", "Project")
                    _label(pdf, f"Project intelligence — {subject}")
                    pdf.ln(2)
                    _prose(pdf, proj_intel["findings"], size=10)

                # Commodity market
                comm = content.get("commodity_market", {})
                if comm.get("analysis"):
                    _label(pdf, f"Commodity market — {comm.get('commodity', '')}")
                    pdf.ln(2)
                    _prose(pdf, comm["analysis"], size=10)

                # Macro context
                macro = content.get("macro_context", {})
                if macro.get("analysis"):
                    _label(pdf, "Macroeconomic context")
                    pdf.ln(2)
                    _prose(pdf, macro["analysis"], size=10)

                notice = content.get("notice")
                if notice:
                    pdf.ln(2)
                    _caption(pdf, notice)

        # ── DCF Financial Model ───────────────────────────────────────────
        elif section_key == "06_dcf_model" and isinstance(content, dict):
            if not content.get("model_ran"):
                reason = content.get("reason", "DCF model did not run.")
                _caption(pdf, str(reason))
            else:
                notes = content.get("assumptions_notes")
                if isinstance(notes, str):
                    _caption(pdf, notes)
                    pdf.ln(5)

                summary = content.get("summary")
                if isinstance(summary, dict):
                    _label(pdf, "Valuation summary")
                    pdf.ln(2)
                    skip = {"project_id", "scenario", "after_tax", "notes", "aisc_unit"}
                    kv = [
                        (k.replace("_", " ").title(),
                         f"{v:,}" if isinstance(v, (int, float)) else str(v))
                        for k, v in summary.items()
                        if k not in skip and v is not None
                    ]
                    _kv_list(pdf, kv)
                    pdf.ln(4)
                    _rule(pdf)
                    pdf.ln(6)

                cash_flows = content.get("cash_flows")
                if isinstance(cash_flows, list) and cash_flows:
                    _label(pdf, "Annual cash flows")
                    pdf.ln(3)

                    def _fmt(v):
                        if v is None: return "-"
                        if isinstance(v, (int, float)): return f"{v:,.0f}"
                        return str(v)

                    headers   = ["Year", "Revenue", "OpEx", "CapEx", "Tax", "FCF", "PV"]
                    col_widths = [16, 28, 26, 26, 22, 28, 28]
                    rows_data  = [
                        [
                            str(cf.get("year", "")),
                            _fmt(cf.get("gross_revenue")),
                            _fmt(cf.get("opex")),
                            _fmt(cf.get("capex")),
                            _fmt(cf.get("tax")),
                            _fmt(cf.get("free_cash_flow")),
                            _fmt(cf.get("present_value")),
                        ]
                        for cf in cash_flows[:20]
                    ]
                    _simple_table(pdf, headers, rows_data, col_widths)

        # ── Data sources ──────────────────────────────────────────────────
        elif section_key == "00_data_sources" and isinstance(content, dict):
            notice = content.get("notice")
            if isinstance(notice, str):
                _caption(pdf, notice)
                pdf.ln(6)

            files = content.get("source_files", [])
            if files:
                _label(pdf, f"Source documents ({len(files)})")
                pdf.ln(3)
                for f in files:
                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(*_INK)
                    pdf.cell(0, 6.5, _safe(f"  {f}"), ln=True)
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
                    _label(pdf, "Visual references")
                    pdf.ln(3)
                try:
                    pdf.image(str(img_path), w=min(_PW, 130))
                    _caption(pdf, img_name)
                    pdf.ln(4)
                    shown += 1
                except Exception:
                    pass

        # ── Generic sections (geology, economics, risk, project facts) ────
        else:
            flat_lines: list[str] = []
            _flatten_for_pdf(content, flat_lines)

            for line in flat_lines:
                line = _safe(str(line))
                if not line.strip():
                    pdf.ln(2)
                    continue
                line = " ".join(w[:120] if len(w) > 120 else w for w in line.split())

                if line.startswith("*"):
                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(*_INK)
                    pdf.set_x(_LM + 4)
                    pdf.multi_cell(_PW - 4, 6, line)
                    pdf.set_x(_LM)
                elif line.endswith(":") and len(line) < 50:
                    pdf.ln(3)
                    _label(pdf, line.rstrip(":"))
                    pdf.ln(1)
                else:
                    colon_pos = line.find(":")
                    if 0 < colon_pos < 35 and "\n" not in line[:colon_pos]:
                        pdf.set_font("Helvetica", "B", 10)
                        pdf.set_text_color(*_INK_SOFT)
                        pdf.write(6.2, line[:colon_pos + 1] + "  ")
                        pdf.set_font("Helvetica", "", 10)
                        pdf.set_text_color(*_INK)
                        pdf.write(6.2, line[colon_pos + 1:].strip())
                        pdf.ln(6.2)
                    else:
                        pdf.set_font("Helvetica", "", 10.5)
                        pdf.set_text_color(*_INK)
                        pdf.multi_cell(_PW, 6.2, line)
                        pdf.ln(1.5)

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

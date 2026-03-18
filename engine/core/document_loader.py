"""
Document loader — extracts readable text from every supported file format.

Supported formats:
  .txt / .md / .csv   — plain text, read directly
  .pdf                — full text extracted via pymupdf (page by page)
  .xlsx / .xls        — each sheet converted to a readable table via openpyxl
  .docx / .doc        — paragraphs and tables extracted via python-docx
  .png / .jpg / .jpeg / .tiff — image described by Claude vision API
  .dxf                — layer names, text entities, dimensions via ezdxf
  .dwg                — attempted via ezdxf; returns None if unreadable
"""

from __future__ import annotations

import base64
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def load_document(file_path: Path) -> str | None:
    """
    Extract text content from a file.
    Returns a string on success, None if the file cannot be read.
    """
    suffix = file_path.suffix.lower()

    if suffix in {".txt", ".md", ".csv"}:
        return file_path.read_text(errors="replace")

    if suffix == ".pdf":
        return _extract_pdf(file_path)

    if suffix in {".xlsx", ".xls"}:
        return _extract_excel(file_path)

    if suffix in {".docx", ".doc"}:
        return _extract_docx(file_path)

    if suffix in {".png", ".jpg", ".jpeg", ".tiff"}:
        return _extract_image(file_path)

    if suffix in {".dxf", ".dwg"}:
        return _extract_cad(file_path)

    return None


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def _extract_pdf(path: Path) -> str:
    import fitz  # pymupdf

    doc = fitz.open(str(path))
    pages = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            pages.append(f"[Page {i}]\n{text}")
    doc.close()
    return "\n\n".join(pages) if pages else ""


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------

def _extract_excel(path: Path) -> str:
    import openpyxl

    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    parts = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = []
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            # skip completely empty rows
            if any(c.strip() for c in cells):
                rows.append("\t".join(cells))
        if rows:
            parts.append(f"[Sheet: {sheet_name}]\n" + "\n".join(rows))
    wb.close()
    return "\n\n".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# Word / DOCX
# ---------------------------------------------------------------------------

def _extract_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    parts = []

    for block in doc.element.body:
        tag = block.tag.split("}")[-1] if "}" in block.tag else block.tag

        if tag == "p":
            from docx.oxml.ns import qn
            text = "".join(
                node.text or ""
                for node in block.iter()
                if node.tag == qn("w:t")
            )
            if text.strip():
                parts.append(text)

        elif tag == "tbl":
            # Extract table as tab-separated rows
            for row in block.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr"):
                cells = []
                for cell in row.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc"):
                    cell_text = "".join(
                        t.text or ""
                        for t in cell.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
                    )
                    cells.append(cell_text.strip())
                if any(cells):
                    parts.append("\t".join(cells))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Images — described by Claude vision
# ---------------------------------------------------------------------------

def _extract_image(path: Path) -> str | None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return f"[Image: {path.name} — ANTHROPIC_API_KEY not set, image could not be described]"

    import anthropic

    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".tiff": "image/tiff",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = mime_map.get(path.suffix.lower(), "image/jpeg")

    image_data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "This image is from a mining project technical document. "
                            "Describe in technical detail what you see — including any "
                            "geological features, cross-sections, drill hole locations or "
                            "collar maps, mine plans, pit designs, ore body outlines, "
                            "assay data tables, grade shell plots, production charts, "
                            "processing flow sheets, infrastructure layouts, or financial "
                            "figures. Extract any visible numbers, labels, coordinates, "
                            "scale bars, legends, or annotations. Be as specific as possible."
                        ),
                    },
                ],
            }
        ],
    )

    description = response.content[0].text.strip()
    return f"[Image: {path.name}]\n{description}"


# ---------------------------------------------------------------------------
# DXF / DWG — CAD files
# ---------------------------------------------------------------------------

def _extract_cad(path: Path) -> str | None:
    import ezdxf

    try:
        doc = ezdxf.readfile(str(path))
    except Exception:
        return f"[CAD: {path.name} — could not be parsed]"

    parts = [f"[CAD File: {path.name}]"]

    # Layer names (often encode geological or survey info)
    layers = [layer.dxf.name for layer in doc.layers]
    if layers:
        parts.append("Layers: " + ", ".join(layers))

    msp = doc.modelspace()
    text_items: list[str] = []
    dimensions: list[str] = []

    for entity in msp:
        dxftype = entity.dxftype()

        if dxftype in ("TEXT", "MTEXT"):
            try:
                text = entity.dxf.text if dxftype == "TEXT" else entity.text
                text = text.strip()
                if text:
                    text_items.append(text)
            except Exception:
                pass

        elif dxftype == "DIMENSION":
            try:
                val = entity.dxf.actual_measurement
                if val:
                    dimensions.append(f"{val:.3g}")
            except Exception:
                pass

        elif dxftype == "INSERT":
            # Block references — extract attribute values
            try:
                for attrib in entity.attribs:
                    val = attrib.dxf.text.strip()
                    if val:
                        text_items.append(val)
            except Exception:
                pass

    if text_items:
        parts.append("Text annotations:\n" + "\n".join(text_items[:200]))
    if dimensions:
        parts.append("Dimensions: " + ", ".join(dimensions[:100]))

    return "\n\n".join(parts)

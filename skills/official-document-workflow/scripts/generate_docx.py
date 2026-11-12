#!/usr/bin/env python3
"""Generate a Chinese official-document DOCX from JSON input."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


FORMAT = {
    "margins_cm": {"top": 3.7, "bottom": 3.5, "left": 2.8, "right": 2.6},
    "title_font": "方正小标宋_GBK",
    "body_font": "仿宋_GB2312",
    "h1_font": "黑体",
    "h2_font": "楷体_GB2312",
    "song_font": "宋体",
    "title_size": 22,
    "body_size": 16,
    "small_size": 14,
    "line_spacing": 28,
    "first_line_indent": 32,
}


def set_run_font(run, font_name: str, size_pt: int, bold: bool = False) -> None:
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    run.font.size = Pt(size_pt)
    run.font.bold = bold


def set_paragraph(paragraph, *, indent: bool = True, align=None) -> None:
    pf = paragraph.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(FORMAT["line_spacing"])
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.first_line_indent = Pt(FORMAT["first_line_indent"]) if indent else Pt(0)
    if align is not None:
        paragraph.alignment = align


def set_cell_shading(cell, fill: str = "FFFFFF") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def setup_document() -> Document:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(FORMAT["margins_cm"]["top"])
    section.bottom_margin = Cm(FORMAT["margins_cm"]["bottom"])
    section.left_margin = Cm(FORMAT["margins_cm"]["left"])
    section.right_margin = Cm(FORMAT["margins_cm"]["right"])

    style = doc.styles["Normal"]
    style.font.name = FORMAT["body_font"]
    style._element.rPr.rFonts.set(qn("w:eastAsia"), FORMAT["body_font"])
    style.font.size = Pt(FORMAT["body_size"])
    style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    style.paragraph_format.line_spacing = Pt(FORMAT["line_spacing"])
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.space_after = Pt(0)
    return doc


def add_text(doc: Document, text: str, *, font: str, size: int, bold: bool = False,
             indent: bool = True, align=None) -> None:
    p = doc.add_paragraph()
    set_paragraph(p, indent=indent, align=align)
    run = p.add_run(text)
    set_run_font(run, font, size, bold)


def add_body_line(doc: Document, line: str) -> None:
    stripped = line.strip()
    if not stripped:
        doc.add_paragraph()
        return

    if stripped.startswith("## "):
        add_text(
            doc,
            stripped[3:].strip(),
            font=FORMAT["h1_font"],
            size=FORMAT["body_size"],
            bold=False,
        )
    elif stripped.startswith("### "):
        add_text(
            doc,
            stripped[4:].strip(),
            font=FORMAT["h2_font"],
            size=FORMAT["body_size"],
            bold=False,
        )
    elif stripped.startswith("# "):
        add_text(
            doc,
            stripped[2:].strip(),
            font=FORMAT["title_font"],
            size=FORMAT["title_size"],
            bold=False,
            indent=False,
            align=WD_ALIGN_PARAGRAPH.CENTER,
        )
    elif re.match(r"^[一二三四五六七八九十]+、", stripped):
        # 中文序号一级标题：黑体
        add_text(
            doc,
            stripped,
            font=FORMAT["h1_font"],
            size=FORMAT["body_size"],
            bold=False,
        )
    elif re.match(r"^（[一二三四五六七八九十]+）", stripped):
        # 中文序号二级标题：楷体
        add_text(
            doc,
            stripped,
            font=FORMAT["h2_font"],
            size=FORMAT["body_size"],
            bold=False,
        )
    else:
        add_text(
            doc,
            stripped,
            font=FORMAT["body_font"],
            size=FORMAT["body_size"],
            bold=False,
        )


def normalize_body(body: Any) -> list[str]:
    if isinstance(body, list):
        return [str(item) for item in body]
    if isinstance(body, str):
        return body.splitlines()
    return [str(body)]


def generate(data: dict[str, Any], output: Path) -> None:
    doc = setup_document()

    doc_number = data.get("doc_number", "").strip()
    title = data.get("title", "公文标题").strip()
    recipient = data.get("recipient", "").strip()
    body = normalize_body(data.get("body", []))
    signature = data.get("signature") or data.get("issuer", "")
    date = data.get("date", "")
    attachments = data.get("attachments", []) or []
    copy_to = data.get("copy_to", "")

    if doc_number:
        add_text(
            doc,
            doc_number,
            font=FORMAT["body_font"],
            size=FORMAT["body_size"],
            indent=False,
            align=WD_ALIGN_PARAGRAPH.CENTER,
        )

    add_text(
        doc,
        title,
        font=FORMAT["title_font"],
        size=FORMAT["title_size"],
        bold=False,
        indent=False,
        align=WD_ALIGN_PARAGRAPH.CENTER,
    )

    if recipient:
        if not recipient.endswith(("：", ":")):
            recipient += "："
        add_text(
            doc,
            recipient,
            font=FORMAT["body_font"],
            size=FORMAT["body_size"],
            indent=False,
            align=WD_ALIGN_PARAGRAPH.LEFT,
        )

    for line in body:
        add_body_line(doc, line)

    if attachments:
        add_body_line(doc, "")
        add_text(
            doc,
            "附件：" + "；".join(str(item) for item in attachments),
            font=FORMAT["body_font"],
            size=FORMAT["body_size"],
        )

    if signature:
        add_body_line(doc, "")
        add_text(
            doc,
            str(signature),
            font=FORMAT["body_font"],
            size=FORMAT["body_size"],
            indent=False,
            align=WD_ALIGN_PARAGRAPH.RIGHT,
        )
    if date:
        add_text(
            doc,
            str(date),
            font=FORMAT["body_font"],
            size=FORMAT["body_size"],
            indent=False,
            align=WD_ALIGN_PARAGRAPH.RIGHT,
        )

    if copy_to:
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cell = table.cell(0, 0)
        set_cell_shading(cell, "FFFFFF")
        p = cell.paragraphs[0]
        run = p.add_run("抄送：" + str(copy_to))
        set_run_font(run, FORMAT["body_font"], FORMAT["small_size"])

    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input JSON file")
    parser.add_argument("--output", required=True, help="Output DOCX file")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    generate(data, Path(args.output))
    print(f"Generated {args.output}")


if __name__ == "__main__":
    main()


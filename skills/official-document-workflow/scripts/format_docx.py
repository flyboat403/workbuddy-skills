#!/usr/bin/env python3
"""Apply core GB/T 9704-style formatting to an existing DOCX."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


FORMAT = {
    "margins_cm": {"top": 3.7, "bottom": 3.5, "left": 2.8, "right": 2.6},
    "title_font": "方正小标宋_GBK",
    "body_font": "仿宋_GB2312",
    "h1_font": "黑体",
    "h2_font": "楷体_GB2312",
    "title_size": 22,
    "body_size": 16,
    "line_spacing": 28,
    "first_line_indent": 32,
}


def set_run_font(run, font_name: str, size_pt: int, bold: bool = False) -> None:
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    run.font.size = Pt(size_pt)
    run.font.bold = bold


def paragraph_kind(text: str, index: int) -> str:
    stripped = text.strip()
    if index == 0 and stripped:
        return "title"
    if re.match(r"^[一二三四五六七八九十]+、", stripped):
        return "h1"
    if re.match(r"^（[一二三四五六七八九十]+）", stripped):
        return "h2"
    if re.match(r"^\d+[.．]", stripped):
        return "h3"
    return "body"


def format_paragraph(paragraph, kind: str) -> None:
    pf = paragraph.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(FORMAT["line_spacing"])
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)

    if kind == "title":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf.first_line_indent = Pt(0)
        font, size, bold = FORMAT["title_font"], FORMAT["title_size"], False
    elif kind == "h1":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.first_line_indent = Pt(FORMAT["first_line_indent"])
        font, size, bold = FORMAT["h1_font"], FORMAT["body_size"], False
    elif kind == "h2":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.first_line_indent = Pt(FORMAT["first_line_indent"])
        font, size, bold = FORMAT["h2_font"], FORMAT["body_size"], False
    else:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.first_line_indent = Pt(FORMAT["first_line_indent"])
        font, size, bold = FORMAT["body_font"], FORMAT["body_size"], False

    for run in paragraph.runs:
        set_run_font(run, font, size, bold)


def format_docx(input_path: Path, output_path: Path) -> None:
    doc = Document(input_path)
    for section in doc.sections:
        section.top_margin = Cm(FORMAT["margins_cm"]["top"])
        section.bottom_margin = Cm(FORMAT["margins_cm"]["bottom"])
        section.left_margin = Cm(FORMAT["margins_cm"]["left"])
        section.right_margin = Cm(FORMAT["margins_cm"]["right"])

    content_index = 0
    for paragraph in doc.paragraphs:
        if not paragraph.text.strip():
            continue
        kind = paragraph_kind(paragraph.text, content_index)
        format_paragraph(paragraph, kind)
        content_index += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    format_docx(Path(args.input), Path(args.output))
    print(f"Formatted {args.output}")


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""Inspect key DOCX format settings and write a Markdown audit report."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


EXPECTED_MM = {"top": 37, "bottom": 35, "left": 28, "right": 26}
TOLERANCE_MM = 1.5
ACCEPTABLE_BODY_FONTS = {"仿宋_GB2312", "仿宋", "FangSong", "FangSong_GB2312"}


def cm_to_mm(value) -> float:
    return value.cm * 10


def status(ok: bool) -> str:
    return "pass" if ok else "fail"


def check_margins(doc: Document) -> list[dict[str, str]]:
    section = doc.sections[0]
    actual = {
        "top": cm_to_mm(section.top_margin),
        "bottom": cm_to_mm(section.bottom_margin),
        "left": cm_to_mm(section.left_margin),
        "right": cm_to_mm(section.right_margin),
    }
    findings = []
    for key, expected in EXPECTED_MM.items():
        value = actual[key]
        ok = abs(value - expected) <= TOLERANCE_MM
        findings.append({
            "item": f"margin_{key}",
            "result": status(ok),
            "expected": f"{expected}mm",
            "actual": f"{value:.1f}mm",
        })
    return findings


def is_heading_text(text: str) -> bool:
    return bool(
        re.match(r"^[一二三四五六七八九十]+、", text)
        or re.match(r"^（[一二三四五六七八九十]+）", text)
    )


def find_body_paragraph(paragraphs):
    """Pick a genuine body paragraph, skipping title, recipient, and headings.

    Body paragraphs are left/justified, first-line indented ~2 chars, and not
    Chinese-ordinal headings. Falls back to the last non-empty paragraph.
    """
    for p in paragraphs:
        if p.alignment == WD_ALIGN_PARAGRAPH.CENTER:
            continue
        indent = getattr(p.paragraph_format.first_line_indent, "pt", None)
        if not indent or indent < 20:
            continue
        if is_heading_text(p.text.strip()):
            continue
        return p
    return paragraphs[-1]


def check_body_paragraphs(doc: Document) -> list[dict[str, str]]:
    findings = []
    paragraphs = [p for p in doc.paragraphs if p.text.strip()]
    if not paragraphs:
        return [{
            "item": "content",
            "result": "fail",
            "expected": "non-empty document",
            "actual": "no non-empty paragraphs",
        }]

    sample = find_body_paragraph(paragraphs)
    pf = sample.paragraph_format
    line_spacing = pf.line_spacing.pt if getattr(pf.line_spacing, "pt", None) else None
    # Distinguish an explicit 0 indent (a violation) from an unset one (skip,
    # to avoid false positives on docs that inherit indent from a style).
    indent = pf.first_line_indent.pt if pf.first_line_indent is not None else None

    if line_spacing is not None:
        findings.append({
            "item": "line_spacing",
            "result": status(abs(line_spacing - 28) <= 1.5),
            "expected": "28pt",
            "actual": f"{line_spacing:.1f}pt",
        })

    if indent is not None:
        findings.append({
            "item": "first_line_indent",
            "result": status(abs(indent - 32) <= 3),
            "expected": "32pt",
            "actual": f"{indent:.1f}pt",
        })

    body_font = sample_body_font(sample)
    if body_font is not None:
        findings.append({
            "item": "body_font",
            "result": status(body_font in ACCEPTABLE_BODY_FONTS),
            "expected": "仿宋_GB2312 / 仿宋",
            "actual": body_font,
        })

    return findings


def sample_body_font(paragraph) -> str | None:
    """Read the east-Asian font of the first run that carries one."""
    for run in paragraph.runs:
        rpr = run._element.rPr
        if rpr is None:
            continue
        rfonts = rpr.rFonts
        if rfonts is None:
            continue
        east_asia = rfonts.get(qn("w:eastAsia"))
        if east_asia:
            return east_asia
    return None


def write_report(findings: list[dict[str, str]], output_path: Path) -> None:
    verdict = "pass" if all(item["result"] == "pass" for item in findings) else "fail"
    lines = [
        "# 格式审校报告",
        "",
        "## Verdict",
        verdict,
        "",
        "## Findings",
        "",
        "| Item | Result | Expected | Actual |",
        "|---|---|---|---|",
    ]
    for item in findings:
        lines.append(
            f"| {item['item']} | {item['result']} | {item['expected']} | {item['actual']} |"
        )
    lines.extend([
        "",
        "## Notes",
        "",
        "This script checks core machine-readable settings only. Final human review should still check document type, official tone, headings, attachments, signature, date, and print section.",
        "",
    ])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    doc = Document(args.input)
    findings = []
    findings.extend(check_margins(doc))
    findings.extend(check_body_paragraphs(doc))
    write_report(findings, Path(args.output))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()


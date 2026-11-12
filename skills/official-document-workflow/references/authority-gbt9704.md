# GB/T 9704-2012 公文格式权威规则

This file is the single format authority for this skill. If scripts or references disagree, this file wins.

## Page

| Item | Rule |
|---|---|
| Paper | A4, 210mm x 297mm |
| Top margin | 37mm |
| Bottom margin | 35mm |
| Left margin | 28mm |
| Right margin | 26mm |
| Approximate text area | 156mm x 225mm |
| Lines per page | About 22 |
| Characters per line | About 28 |

## Fonts and sizes

| Element | Font | Size |
|---|---|---|
| Title | 方正小标宋_GBK or 方正小标宋简体 fallback | 2号, about 22pt |
| Body | 仿宋_GB2312 or 仿宋 fallback | 3号, about 16pt |
| Level 1 heading | 黑体 | 3号, about 16pt |
| Level 2 heading | 楷体_GB2312 or 楷体 fallback | 3号, about 16pt |
| Level 3 heading | 仿宋_GB2312, bold when needed | 3号, about 16pt |
| Page number | 宋体 | about 14-15pt |
| Print/copy section | 仿宋_GB2312 | 4号, about 14pt |
| Latin text & digits | Times New Roman | same size as the surrounding Chinese element |

## Paragraphs

- Body paragraphs: first-line indent 2 Chinese characters, usually 32pt.
- Body alignment: justified.
- Line spacing: fixed 28pt.
- Spacing before/after: 0pt unless document element spacing requires otherwise.
- Title: centered, no first-line indent.
- Recipient: left aligned, no first-line indent, ending with a full-width colon when appropriate.
- Signature/date: usually right aligned or centered according to document type and local practice.

## Heading hierarchy

Use this hierarchy unless the user provides a required outline:

```text
一、一级标题
（一）二级标题
1. 三级标题
（1）四级标题
```

Recommended styles:

- First level: 黑体 3号
- Second level: 楷体_GB2312 3号
- Third and fourth level: 仿宋_GB2312 3号

## Masthead elements (版头)

Font and size rules for the elements above the red separator line. These elements are NOT built by the DOCX scripts (see skill "DOCX scope"); the rules are provided for audit and manual red-head production.

| Element | Font | Size | Notes |
|---|---|---|---|
| 份号 (document serial) | 黑体 | 3号, about 16pt | 6-digit Arabic with leading zeros, top-left of the版心, line 1 |
| 密级/保密期限 (security level) | 黑体 | 3号, about 16pt | 顶格, line 2 |
| 紧急程度 (urgency) | 黑体 | 3号, about 16pt | 顶格, line 3 |
| 发文字号 (doc number) | 仿宋_GB2312 | 3号, about 16pt | centered; for上行文 left by one char |
| 签发人 (issuer line label) | 仿宋_GB2312 | 3号, about 16pt | for上行文, label left by one char |
| 签发人姓名 (issuer name) | 楷体_GB2312 | 3号, about 16pt | right by one char |

## Common elements

Core official document elements may include:

- Issuer mark
- Document number
- Title
- Recipient
- Body
- Attachment note
- Signature
- Date
- Copy-to section
- Print section

Not every document needs every element. The document type and user task determine required elements.

## Punctuation and dates

- Use Chinese punctuation in Chinese text.
- Use Chinese book-title marks `《》` where appropriate.
- Use Chinese parentheses `（）` for heading hierarchy.
- Dates should usually be written as `2026年6月26日`; do not write `06月`.
- Use six-angle brackets in document numbers: `〔2026〕`.

## Tool rule

All DOCX scripts should apply these values:

```json
{
  "margins_mm": {"top": 37, "bottom": 35, "left": 28, "right": 26},
  "line_spacing_pt": 28,
  "body_size_pt": 16,
  "title_size_pt": 22,
  "first_line_indent_pt": 32
}
```


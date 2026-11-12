---
name: official-document-workflow
description: Codex skill for Chinese official document expert workflows. Use when the user asks to draft, revise, audit, format, or generate Chinese official documents such as notices, reports, requests, replies, letters, meeting minutes, work summaries, work plans, or leadership speeches, especially when GB/T 9704-2012 formatting, official tone, DOCX output, or multi-step review is needed.
---

# Official Document Workflow

Use this skill to run a single-Skill expert workflow for Chinese official document drafting, revision, review, and DOCX formatting.

## Operating principle

Act as one orchestrator coordinating seven logical experts:

1. **Orchestrator**: choose the workflow, manage checkpoints, resolve conflicts, and assemble final delivery.
2. **Intake Expert**: identify task mode, document type, missing fields, and whether user confirmation is required.
3. **Drafting Expert**: create the first draft from the selected document type and available facts.
4. **Restructure Expert**: analyze and reorganize source materials in revision tasks.
5. **Style Expert**: improve official tone without changing facts.
6. **Format Audit Expert**: check against the authoritative format standard.
7. **DOCX Tool Expert**: generate, format, or inspect Word documents with scripts.

Do not let experts maintain separate standard copies. Treat `references/authority-gbt9704.md` as the single source of truth for format rules.

## Required references

Load only what is needed:

- For format rules: `references/authority-gbt9704.md`
- For document type selection: `references/document-types.md`
- For reusable structures: `references/templates.md`
- For wording and tone: `references/language-style.md`
- For pre-drafting positioning: `references/drafting-positions.md`
- For final review: `references/review-checklists.md`

## Workflow selection

Choose one of three modes.

### Mode A: Create a new official document

Use when the user provides a topic, purpose, institution, or rough requirements.

Process:

1. Identify document type and required elements.
2. Ask for missing core elements when they block drafting.
3. Resolve the four pre-drafting positions (see `references/drafting-positions.md`): narrative (定叙事), policy mainline (定主线), authority boundary (定边界), and voice (定语态).
4. Create `brief.json` mentally or as a file when producing artifacts; record the positions under `positions`.
5. Draft in Markdown, following the resolved positions.
6. Review official tone, document-type fit, and the held positions.
7. Audit format requirements.
8. Generate DOCX if requested or naturally expected.
9. Deliver draft, DOCX path, and review notes.

### Mode B: Revise or restructure source material

Use when the user provides existing material, a rough draft, meeting notes, fragmented facts, or prior documents.

Process:

1. Preserve all concrete facts, figures, dates, names, and policy references unless the user says otherwise.
2. Produce a structure analysis before heavy rewriting for complex materials, using the four pre-drafting positions as the analytical lens (see `references/drafting-positions.md`): how the source narrates, what it aligns to, whose authority it claims, and whose voice it speaks in.
3. Rebuild the document using MECE grouping and conclusion-led headings, applying the resolved positions.
4. Improve official tone.
5. Audit format and document-type fit, and verify the held positions.
6. Generate DOCX if requested.

### Mode C: Format or audit an existing document

Use when the user provides DOCX, Markdown, or text and mainly needs compliance checking or formatting.

Process:

1. Run content/format audit.
2. Use `scripts/format_docx.py` for existing DOCX when applicable.
3. Use `scripts/check_format.py` for DOCX inspection.
4. Report pass/fail findings and required fixes.

## Core element policy

Core elements usually include:

- Document type
- Issuer
- Recipient / main sending unit
- Title or subject
- Body facts and requirements
- Date
- Signature / issuing unit

Ask the user only when a missing element blocks correctness. For optional elements, infer conservatively and state the assumption.

## Intermediate artifacts

When producing files, use these names:

- `brief.json`: task profile and required fields
- `outline.md`: proposed structure
- `draft.md`: first draft
- `structure-analysis.md`: source-material analysis for revision mode
- `revised-draft.md`: revised content
- `style-review.md`: tone and wording notes
- `format-audit.md`: format compliance report
- `format-spec.json`: concrete format parameters
- `final.docx`: final Word document
- `final-review.md`: final pass/fail review

## Quality gates

Use these gates before final delivery:

1. **Task fit**: document type and task mode are correct.
2. **Completeness**: required document elements are present.
3. **Content integrity**: facts, numbers, and user-provided details are preserved.
4. **Structure**: headings and sections match the document type.
5. **Positioning**: the four pre-drafting positions (narrative / policy mainline / authority boundary / voice) are resolved per `references/drafting-positions.md` and held in the delivered draft.
6. **Tone**: wording is formal, accurate, concise, and non-colloquial.
7. **Format**: GB/T 9704-2012 key requirements are followed.
8. **File output**: DOCX exists, opens, and uses the expected margins, fonts, and spacing when generated.

## Conflict rules

- Format conflicts: `references/authority-gbt9704.md` wins.
- Document-type conflicts: `references/document-types.md` wins.
- User request conflicts with formal standard: pause and ask for confirmation.
- Style edits must not change facts.
- Script output conflicts with format standard: fix the script result or rerun `scripts/format_docx.py`.

## DOCX scope

The scripts produce a correctly typeset document body: page margins, fonts, sizes, fixed line spacing, first-line indent, and heading levels per GB/T 9704-2012. They do not build the formal 版头 (发文机关标志 red masthead, 红色反线 separator, 签发人). Deliver output as a compliant body / review draft, not a print-ready 红头文件. When the user needs a full 红头 issuance, state this boundary.

## DOCX scripts

Scripts require Python 3 and `python-docx`.

Generate a DOCX from JSON:

```bash
python3 scripts/generate_docx.py --input brief.json --output final.docx
```

Format an existing DOCX:

```bash
python3 scripts/format_docx.py --input input.docx --output formatted.docx
```

Check DOCX format:

```bash
python3 scripts/check_format.py --input final.docx --output format-audit.md
```

## JSON input for DOCX generation

Use this shape:

```json
{
  "document_type": "notice",
  "issuer": "XX单位",
  "doc_number": "XX发〔2026〕1号",
  "recipient": "各有关单位：",
  "title": "关于开展XX工作的通知",
  "body": [
    "一、总体要求",
    "第一段正文。",
    "（一）具体分工",
    "第二段正文。"
  ],
  "signature": "XX单位",
  "date": "2026年6月26日",
  "attachments": [],
  "copy_to": ""
}
```

Heading detection in `body`: lines starting with a Chinese ordinal like `一、` render as level-1 headings (黑体), `（一）` as level-2 headings (楷体_GB2312). Markdown prefixes also work: `##` for level 1, `###` for level 2, `#` for the centered title. Everything else renders as 仿宋 body text. Put heading lines as their own array items, not inline with body sentences.

## Final delivery format

For ordinary chat output, deliver:

1. Final draft or summary of revisions.
2. Generated file path when a DOCX is created.
3. Format/tone audit summary.
4. Any assumptions or missing fields.

For file-producing tasks, place deliverables in the user-requested location or a clear `outputs/` path.


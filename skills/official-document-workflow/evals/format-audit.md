# Eval: format-audit

Prompt:

```text
这是我已经写好的一份通知（DOCX），麻烦只做格式检查，不要改内容。帮我看看符不符合公文格式国标，哪里不对、怎么改。
（附件：一份正文用宋体小四、行距 1.5 倍、首行未缩进、页边距为 Word 默认值的 notice.docx）
```

Expected:

- Enters format-only / audit mode (Mode C), does not rewrite the content.
- Runs `scripts/check_format.py` to inspect the DOCX.
- Reports pass/fail against GB/T 9704-2012 key items: margins (37/35/28/26mm), body font 仿宋_GB2312, body size 三号/16pt, line spacing fixed 28pt, first-line indent 2 characters/32pt.
- Flags the concrete violations in the sample: wrong body font, wrong size, non-fixed line spacing, missing indent, default margins.
- Gives an actionable fix list and offers to run `scripts/format_docx.py` to auto-correct.
- Treats `references/authority-gbt9704.md` as the format authority when findings conflict.
- Does not invent content or change facts.

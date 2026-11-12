---
name: jianbao-generator
description: 将微信公众号文章套版生成为《四川省邓仕川名师工作室简报》docx。当用户要求"把微信文章转成简报""生成工作室简报""套用简报格式""按模板做简报"时使用。以用户确认过的模板（含报头红头、方正小标宋标题、仿宋正文、自动编号小标题、图注、落款表）为基准，自动完成标题断行、引言/小标题/正文切分、正文图提取与装饰图过滤、图注识别、期号与日期替换。
agent_created: true
disable-model-invocation: true
---

# 简报生成器（jianbao-generator）

将微信文章结构化 JSON 套版为《四川省邓仕川名师工作室简报》docx，格式基准为用户人工修改确认过的
`template/四川省邓仕川工作室简报-模板.docx`（2026-08-06 定稿）。

## 目录结构

```
jianbao-generator/
├── SKILL.md                    本说明
├── template/
│   └── 四川省邓仕川工作室简报-模板.docx   格式基准模板（勿改动段落结构）
└── scripts/
    └── make_jianbao.py         生成脚本（lxml + Pillow）
```

## 前置条件

- 运行环境：`~/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe`
  （已装 lxml + Pillow；也可用托管解释器
  `~/.workbuddy-ai/binaries/python/versions/3.13.12/python.exe`，
  同样具备 lxml 6.x + Pillow 12.x）
- 校验工具（可选）：`pandoc`（本机未安装；无 pandoc 时改用
  「zip 完整性 + 全部 XML 可解析 + rels 图片目标存在」三项校验，见下方校验命令）

## 输入准备

**两种来源都可**：

- **A. 微信文章**（原始设计）：抓取文章得到 `wx_article.json` + 图片目录。
- **B. 非微信来源**（同样可用，见文末「非微信来源用法」）：PPT/课件、邀请函、活动照片等，
  由自己**手工构造**同一套 JSON（title/publish/blocks），图片直接放目录。
  简报正文由你根据素材撰写，脚本只负责套版。

输入为一个结构化 JSON（字段见下）+ 一个按序命名的图片目录：

```json
{
  "title": "文章标题",
  "publish": "2026-06-28 21:46",
  "author": "作者",
  "url": "原文链接",
  "blocks": [
    ["text", "正文文本…图注文字&nbsp;一、小标题&nbsp;正文…"],
    ["img", "https://…/640?wx_fmt=png"],
    ...
  ]
}
```

- blocks 为 `["text"|"img", 内容]` 数组，按文章顺序。
- text 块约定：图注写在本块开头、以 `&nbsp;` 与正文分隔（且该块前一个是 img 块时才会被识别为图注）；
  小标题形如 `一、实地走访&nbsp;正文`（`&nbsp;` 或 2+ 空格或全角空格分隔）。
- **独立图注块**：若图注单独成一个 text 块（不含 `&nbsp;`，前一个是 img 块，文本 ≤ 40 字且非数字开头），
  也会被识别为图注——适用于图注后无正文、直接跟下一张图的文章（如 2026年第2期）。
- **连续图注**：一张图后跟两条独立图注块（如第3期 img5 后依次为"漫剧创作实操""部分作品展示"），
  第二条跟随上一条识别，两条均渲染为图注样式（2026-08-06 修复：仅在未识别为图注时才重置 last_was_cap）。
- **独立小标题块**：整块形如 `一、XXX`（无 `&nbsp;` 分隔，1~20 字）也识别为 heading 自动编号，
  适用于小标题独占一段的文章（如第3期"一、AI现状认知与工具搭建"）。
- 图片目录：`img0.png / img1.png / …`，序号与 blocks 中 img 块顺序一致（可用 weixin-ocr-pipeline
  技能产出，或自行抓取下载）。

脚本自动处理：
- 剔除文末署名块（"文图丨…" / "文丨…" / "编辑丨…" / 含"投稿邮箱"的块）
- **只保留最后一个正文 text 块之前的 img 块**（过滤文末 gif 横幅/表情/小图标等装饰图）
- 兜底过滤 .gif 与任一边 < 120px 的图片

## 使用步骤

1. 准备 `wx_article.json` 与图片目录 `wx_imgs/`（见上）。
2. 运行：

```bash
cd <工作目录>
"~/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe" \
  "~/.workbuddy-ai/skills/jianbao-generator/scripts/make_jianbao.py" \
  --json wx_article.json --imgs-dir wx_imgs \
  --out 输出.docx --issue "2026年第2期" \
  [--date "2026年7月15日"] [--title "自定义标题"]
```

> `--template` 已有默认值，且按脚本自身位置定位（`<skill>/template/四川省邓仕川工作室简报-模板.docx`），
> 跨机器、跨用户名都可用，**不需要再手写绝对路径**。

3. 校验：本机无 pandoc 时用下列三项代替（任一失败即不可交付）：

```bash
python - <<'PY'
import zipfile, re, lxml.etree as ET
f='输出.docx'; z=zipfile.ZipFile(f); names=set(z.namelist())
assert z.testzip() is None, 'zip 损坏'
for n in z.namelist():
    if n.endswith(('.xml','.rels')): ET.fromstring(z.read(n))
r=z.read('word/_rels/document.xml.rels').decode('utf-8')
for rid,tgt in re.findall(r'Id="(rId\d+)"[^>]*?Target="([^"]+)"', r):
    if 'media' in tgt: assert 'word/'+tgt in names, (rid, tgt)
print('校验通过')
PY
```

最后用 WPS/Word 打开目检排版。

### 参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `--json` | 是 | 结构化 JSON 路径（微信文章或手工构造） |
| `--imgs-dir` | 是 | 图片目录（img0.png/img1.png/…，也接受 .jpg/.jpeg/.webp） |
| `--out` | 是 | 输出 docx 路径 |
| `--issue` | 是 | 期号，如 `2026年第2期`（写入报头期号） |
| `--date` | 否 | 印发日期，如 `2026年7月15日`；缺省取文章 publish |
| `--title` | 否 | 简报标题；缺省取文章标题。标题分两行可用 `|` 手动断行（如 `邓仕川名师工作室\|AIGC数字设计实战专项培训顺利开展`），否则自动在标点后断行 |
| `--no-enhance` | 否 | 禁用图片轻度调色增强。**默认开启**：饱和度 ×1.18、对比度 ×1.10（不调亮度）。手机原图多为室内拍摄+平台压缩，饱和度/对比度偏低（"灰蒙"感），增强后色彩更鲜亮；需与原图逐像素一致时用本开关 |
| `--template` | 否 | 模板路径，缺省用 skill 自带模板（按脚本位置定位） |

**图片自动缩放**：正文图最大像素宽 `MAX_PX_W = 1400`（显示宽仅 13.9cm，1400px ≈ 256 DPI）。
手机原图 4000~5700px 若不缩放，存成 PNG 会让 docx 膨胀到 50MB+；缩放后 4 张图约 7.5MB。
如需更高分辨率改脚本里的 `MAX_PX_W`。

## 格式规范（从用户修改稿识别，2026-08-06）

| 元素 | 格式 |
|---|---|
| 报头 | LOGO(rId11) + 红头文本框"四 川 省 职 业 院 校 '双 师 型'名 师 工 作 室 / 工 作 简 报"（方正小标宋简体 sz=52、方正公文黑体 sz=84，颜色 CD1F1E，带 w14:textOutline 描边） |
| 期号 | `（2026年第X期）`，普通 run，仿宋_GB2312 szCs=32 |
| 标题 | 1~2 段，pStyle=`000026`（"一、标题"：居中、方正小标宋简体、szCs=32、行距 560 固定），优先在标点后断行 |
| 引言/正文 | 仿宋_GB2312、两端对齐、首行缩进 2 字符（firstLineChars=200）、行距 240 auto |
| 小标题 | 独立段，`numPr`(numId=1→abstractNumId=0, numFmt=chineseCountingThousand, lvlText="%1、") 自动编号"一、二、三…"，加粗，仿宋_GB2312 |
| 正文图 | 居中，宽 5000000 EMU（约 13.9cm），高按原图比例；3 张内复用模板槽位 rId12/13/14 → word/media/image2/3/4.png，超出自动生成 rId15+ 与 image5+.png。**默认做轻度调色增强**（饱和 ×1.18 / 对比 ×1.10，`--no-enhance` 关闭），并**自动等比缩放到最大宽 1400px**（控体积，见参数表） |
| 图注 | 居中、仿宋_GB2312、sz=28 / szCs=18 |
| 落款 | 表格（含嵌套表：编辑核稿/审稿签发/报送发；外层行1：印数17份），日期与编号行同步替换 |
| 落款表结构 | 行0 tc0：日期段+空段+**嵌套表**（编辑核稿/审稿签发/报送发）；行1 tc0：印数（17份）。脚本必须保持该结构 |

### 模板段落索引（修改模板后需重新核对）

`[0]`报头 `[1]`日期行 `[2]`空行 `[3]`标题1 `[4]`标题2 `[5]`空行 `[6]`正文段
`[7]`小标题段 `[9]`图片段 `[10]`图注段 `[21]`落款表 `[22]`表后空行 `[末尾]`sectPr

## 关键坑（务必遵守）

1. **必须用 lxml.etree 解析/序列化**：标准库 xml.etree.ElementTree.tostring 会把
   命名空间重写为 `ns0:/ns1:` 前缀，导致 pandoc 报 DocxError 打不开。
   序列化用 `ET.tostring(root, encoding='UTF-8', xml_declaration=True, standalone=True)`。
2. **zip 图片条目路径必须带 `word/` 前缀**：rels 的 Target 是相对 `word/` 解析的
   （`media/image2.png`），但 zip 内条目路径是 `word/media/image2.png`。写错前缀时
   Word 仍显示模板旧图、新图成为孤儿条目——务必用 `SLOT_FILES = ['word/media/image2.png', …]`。
3. **装饰图过滤靠位置而非尺寸**：微信文章文末的 gif 横幅/表情/小图都排在最后一个正文
   text 块之后，按"最后一个 text 块之前的 img 块"过滤最可靠；尺寸/格式仅作兜底。
4. 图片写入前用 Pillow 转 RGB 再存 PNG，透明/调色板图（RGBA/P/LA）需 `convert('RGB')`。
5. 小标题的"一、二、三"由 numbering.xml 的 chineseCountingThousand 自动生成，
   段落文本只写"实地走访"这类词干；pandoc 会渲染成 "1. 2. 3." 属正常差异，Word 中正确。
6. **替换表格内文本绝不能扁平化**：禁止对整个表格 `findall('.//w:t')` 拼接全文后
   `set_text`（会把全部文字塞进第一个 run、嵌套表/其他行清空，表格变一团）。必须**逐段处理**：
   遍历表格全部 `w:p` 后代，每段内用**跨 run 精确替换**（只改覆盖目标文本的 run 区间，
   其余 run 文本与格式原样保留）。`replace_text_in` 已实现该逻辑，勿改回全局拼接。
7. 落款表是"表格内嵌表格"结构（行0 tc0 内嵌"编辑核稿/审稿签发/报送发"小表），
   任何遍历都要区分直接子元素与递归后代，避免误伤嵌套内容。
8. **新增第 4 张及以后的图片，rels 的 Target 不能带 `word/` 前缀**（2026-09-23 修复）：
   模板原有关系写作 `Target="media/image1.png"`（相对 `word/` 解析），
   而 zip 条目路径必须写 `word/media/image5.png`。二者前缀相反，极易写错——
   写错时 Word 里第 4 张图显示为裂图（目标解析成 `word/word/media/…`）。
   脚本里 `SLOT_FILES`（zip 条目）带 `word/`，新加关系的 Target（rels）**不带**。
9. **紧跟在图片/图注之后的 text 块会被判为图注**，因此
   **绝不能让"小标题块"紧跟在 img 或 caption 之后**（≤40 字、非数字开头 → 被吞成图注）。
   对策：在每段图注之后插入一个**空 text 块** `["text", ""]`。
   空块既不产生图注（`text.strip()` 为空被跳过）、也不产生段落（`split_sections('')` 返回空），
   但会把 `last_was_img` / `last_was_cap` 复位，使后面的小标题正确识别。
10. **图注文字不要以数字开头**（如"2026年…培训班现场"会被判为非图注而变成正文段）。
    改为"全市…培训班现场"这类非数字开头写法。
11. 正文段落里**不要出现连续 2 个以上空格或全角空格（U+3000）**：
   `split_sections` 的小标题正则以"2+ 空格 / 全角空格"为分隔符，正文里出现会被误切。
   中文正文用中文标点、词间不加空格即可（"GB/T 9704—2012"这类单个空格安全）。

## 非微信来源用法（2026-09-23 新增，已验证）

素材不是微信文章时（如"我拿这份 PPT 讲了课，请写简报"），流程如下：

1. **提取事实**：从课件 PDF/PPTX 抽文字（`pypdf` 足够），从邀请函/培训指南抽主办单位、
   承办单位、时间、地点、主讲人身份；**时间地点以正式文件（邀请函、培训指南）为准**，
   课件封面日期常是制稿时的旧值，不要直接采信。
2. **撰写正文**：按 4~6 个小节组织（与模板"实地走访/专题报告/深度研讨/未来展望"同构），
   每节 1 段 200~300 字；小标题写成 `一、词干`（≤20 字、无空格），正文不含小标题。
3. **现场照片**：按顺序复制为 `img0.jpg/img1.jpg/…`，图注 ≤40 字且非数字开头。
4. **构造 JSON**：按「空文本块」规则（关键坑 9）在每张图注后插 `["text", ""]`；
   最后一个 img 块必须排在最后一个 text 块之前，否则会被当装饰图剔除。
5. 运行脚本 → 三项校验 → 交付。

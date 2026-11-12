---
name: brand-icon-collector
description: 批量收集品牌/产品官方图标（logo、标志、icon），导出矢量为 SVG、位图为 512px 透明 PNG，并按分类或厂商排成一览图、总览页或矩阵。当用户说「找 XX 的图标」「要一批 logo」「收集这几个模型/厂商的标识」「做一页图标总览」「PPT/课件里要放各品牌 logo」「把图标排成几行几列」时使用。也适用于用户想用 Pexels、Unsplash、Pixabay 之类的图库去找品牌 logo 的情况——那些是摄影图库，根本没有品牌标识，必须先按本技能换源，否则会白跑一趟。Make sure to use this skill whenever the user needs brand marks, product logos, or company icons in any quantity, even if they only say「找几张图」「配个图标」and never mention "logo" or "SVG".
---

# 品牌图标采集

一句话概括：**先确认要的是"品牌标识"还是"摄影图"，再按源优先级探测取矢量，最后拼图核验并成套交付。**

这类任务翻车通常不在下载，而在三件事上：源选错（拿摄影图库找 logo）、slug 猜错（抓回 404 还以为是网络问题）、拿了图不看（缩到 46px 才发现在 512 画布上糊成一团）。

## 第 0 步：这张图是什么性质

先分清两类需求，走的路完全不同：

| 需求 | 典型说法 | 该用什么 |
| --- | --- | --- |
| **品牌标识** | 「DeepSeek 的图标」「各厂商 logo」「模型标志」 | 本技能：品牌图标库 + 官网 |
| **摄影 / 插画** | 「一张科技感的配图」「背景图」「氛围图」 | Pexels / Unsplash 之类图库 |

品牌标识**不存在于摄影图库里**。Pexels、Unsplash 收录的是摄影师作品，不会有企业商标。用户如果点名要用这类图库找 logo，直接说明原因并切到品牌源——不要硬搜，不要用风格相近的图凑数，更不要用 AI 生图伪造一个"看起来像"的标。

## 第 1 步：探测源可用性

三个公开源覆盖绝大多数品牌，**先探再抓**：

```bash
python scripts/iconkit.py probe --slugs deepseek,openai,gemini,glm,wan,veo
```

输出四列：LobeHub 单色、LobeHub 彩色变体、Simple Icons、以及建议走哪条路。

优先级与理由：

1. **LobeHub Icons**（`@lobehub/icons-static-svg`，MIT）—— AI 与科技品牌覆盖最全，很多有专门的 `-color` 彩色变体。走 `registry.npmmirror.com` 镜像取文件，`unpkg.com` 在国内基本不通。
2. **Simple Icons**（CC0）—— 通用品牌，返回带官方品牌色的 SVG，色值可靠。
3. **svgl**（`https://api.svgl.app`）—— 返回全量 JSON 清单，可检索标题；条目数约六七百，适合查是否有官方彩色矢量。
4. **源外搜索**（见第 3 步）—— 三源都没有时，用搜索引擎找官网、第三方矢量站与开源图标仓库。
5. **官网 favicon** —— 顺带一提：favicon 要先有官网地址，而官网往往也是搜出来的，所以它排在搜索之后。多为人造位图，质量参差。
6. **自绘文字标识** —— 见第 3 步。

slug 命名**不统一**，是主要坑源：Gemini 是 `googlegemini`、GLM 是 `zhipu`、Kimi 是 `kimi` 而公司是 `moonshotai`、OpenAI 的图标名是 `openai` 而非 `chatgpt`。别猜，先 probe。详细对照见 `references/sources.md`。

## 第 2 步：批量抓取

准备 `brands.json`，每项描述一个品牌：

```json
[
  {"slug": "deepseek", "mono": "deepseek", "color": "simpleicons:deepseek",
   "zh": "深度求索", "en": "DeepSeek", "vendor": "深度求索", "cat": "llm"}
]
```

- `slug` 是输出文件名，用品牌英文名小写，给公司标识加后缀区分（`anthropic` / `anthropic-claude`）
- `mono` 是 LobeHub 里的图标名；`color` 可写 `lobehub:xxx-color`、`simpleicons:xxx`，或写 `none` 表示该品牌本就只有黑色标准形态。**省略 `color` 则自动探测**：先试 LobeHub 彩色变体，再试 Simple Icons
- `cat` 用于分类排版；`vendor` 用于厂商归组

```bash
python scripts/iconkit.py fetch --brands brands.json --out ./品牌图标
```

产出固定目录结构：

```
品牌图标/
├─ svg/mono/*.svg        单色矢量（纯黑填充，可自由改色）
├─ svg/color/*.svg       官方配色矢量
├─ png/mono-512/*.png    单色 512px 透明底
├─ png/color-512/*.png   彩色 512px 透明底
└─ manifest.json         清单：slug / 中英文名 / 厂商 / 分类 / 文件路径 / 来源
```

为什么这套结构值得固守：SVG 进 PPT/Word 缩放不虚，PNG 用于网页和快速预览；单色版是为了深色背景和统一视觉，彩色版是为了识别度；`manifest.json` 让后续排版脚本不必再猜文件名，也让"这份图标从哪来的"有据可查。

抓不到的品牌脚本会明确列出来，不静默跳过——看到失败清单再进第 3 步。

## 第 3 步：补缺，并且诚实地补

先在 svgl 里按标题检索一次，确认真的没有官方矢量，再决定怎么补。有些产品**本身就只有文字标识（wordmark）**，没有独立图形符号，这时候"没有图形 logo"是事实，不是资料缺失。

补法按优先级：

### 1. 源外搜索（升级路径，别当默认路径）

三个固定源的好处是确定性——slug 对了就一定拿得到、格式干净、许可明确。搜索引擎是**升级路径**：三源 probe 全部失败，或对某个标"是不是最新版"没把握时才动用。别一上来就搜，搜索结果噪声大、许可不清、还常混着粉丝重绘的旧版标。

先用脚本生成现成的查询链接：

```bash
python scripts/iconkit.py search-hints --slugs wan,seedream --zh "通义万相,Seedream"
```

执行搜索用 **multi-search-engine** 技能（同在本机 skills 目录）的引擎模板与反爬流程，本技能不重复实现。几条实测要点：

- **百度必须先取会话**：先 `GET https://www.baidu.com/` 拿 Cookie，再带 Cookie 搜，否则返回 1.5KB 的反爬空壳页
- **搜狗微信可直连**：`https://wx.sogou.com/weixin?type=2&query={关键词}`——国产产品的发布稿、品牌介绍多在微信公众号，这是找中文品牌官方色值与标识形态最有效的入口
- **DuckDuckGo / Google 在部分网络不通**：不通就换 Bing INT（`cn.bing.com/search?q={}&ensearch=1`）或国内引擎
- 查询词模板：英文 `"品牌名" logo svg filetype:svg`、`site:github.com 品牌名 logo`；中文 `品牌名 官网 品牌标志`、`品牌名 发布 品牌`

搜到之后的三种落点，按可信度排序：

1. **官网本体**——首选「内联 SVG 提取」（见下方专节），其次 `<link rel="apple-touch-icon">`（通常是最大的官方位图，180px 居多）、`<link rel="icon">`、og-image。这是唯一权威来源
2. **开源图标仓库**——`gilbarbara/logos`（GitHub，约 500+ 品牌 SVG）、Wikimedia Commons。质量好且带来源
3. **第三方矢量站**（vectorseek、seeklogo、logowik、worldvectorlogo）——能找到，但常见两类坑：标是粉丝重绘的旧版；许可写"仅编辑用途"。**取之前必须回官网核对形状与配色**，取之后在 README 里注明出处与许可限制

#### 官网内联 SVG 提取（官网落点的标准做法）

现代官网的导航栏 logo 多半以内联 `<svg>` 写在首页 HTML 里——这是比任何第三方矢量站都权威的矢量源，而且 fill 色值就是官方品牌色。用捆绑脚本一步完成扫描、挑选、派生：

```bash
python scripts/extract_inline_svg.py --url https://www.wps.com/ --out ./WPS图标 --name wps
```

脚本自动：扫描页面上全部内联 SVG 并按「上下文含 logo、尺寸合理、path 数」打分排序 → 选最高分候选 → 清洗框架属性 → 派生彩色 / 单色黑 / 纯白三版 SVG + 512px 透明 PNG → 抓 apple-touch-icon → 出预览拼图（含深底效果）与 manifest。选错了用 `--list-only` 看候选清单，`--pick 序号` 重选。

实测要点（WPS 案例）：

- **国内站与国际站的资产质量可能天差地别**：wps.cn 的 favicon 只有 32px base64，而 wps.com 导航栏藏着 122×28 的完整矢量字标。两个区域官网都查一遍再下结论
- 官网 SVG 的 `<path>` 常是**非自闭合写法**（`<path ...>` 缺 `/>`），截取子集（比如把红 W 标从字标里切出来）时必须补 `/>`，否则 resvg 报 `expected 'path' tag`；整段提取一般无此问题，脚本已内置修复
- 官网 SVG 带框架噪声属性（Vue 的 `data-v-xxx` 等），脚本会清洗
- 字标与图形标常在同一 SVG 里靠 fill 颜色区分（如红色 path = 图形标、黑色 path = 字母），按 fill 拆分即可得到方形图标；**fill 色值就是官方品牌色，直接采用，不臆造**
- 渐变填充（`fill="url(#...)"`）无法用替换 fill 的方式做单色/白色版——这类只能交付彩色原版，单色需求走重绘或标注说明
- 扫描会命中大量 UI 小图标（箭头、菜单 16×16 之类），脚本的打分已将其排到末尾；`--list-only` 的清单本身也有价值——里面列出的多色 28×28 图标常是同厂商的产品家族图标，可顺带收进集合

### 3. 明确告知并留痕

无论自绘还是取自第三方，都要在清单里留 `wordmark: true` 或 `color_src` 来源标记，版式里打标签（自绘项写「自绘文字标识（该产品无官方矢量标识）」），README 单列一节说明性质与许可限制。

自绘规范：圆角方形 + 厂商品牌色底 + 白色产品名，文字用 fontTools 转成矢量路径（不依赖字体，任意缩放不糊）。品牌色从该厂商既有标识里取，不臆造。

```bash
python scripts/iconkit.py wordmark --brands wordmarks.json --out ./品牌图标
```

```json
[{"slug": "wan", "text": "万相", "font": "cjk", "color": "#FF6A00",
  "zh": "通义万相", "en": "Wan", "vendor": "阿里巴巴", "cat": "image"}]
```

绝不做的：用风格相近的别的产品的标顶替；用 AI 生成一个"大概长这样"的图形；把位图放大后当矢量交付。

## 第 4 步：排版

两种视图，按用户语境选：

**分类一览图**（默认，课件里最常用）

```bash
python scripts/iconkit.py sheet --manifest ./品牌图标/manifest.json --out ./品牌图标 \
  --group-by cat --cols 4 --label llm=语言模型 --label image=生图模型 --label video=视频模型
```

**厂商 × 模态矩阵**（想表达"谁在做全模态"时）

```bash
python scripts/iconkit.py matrix --manifest ./品牌图标/manifest.json --out ./品牌图标 --skip llm-company
```

**HTML 总览页**（要可点按下载、要放在浏览器里给人挑）——参照 `references/layouts.md` 的骨架手写生成脚本，卡片里并排放「彩色 / 单色」两块预览，配四个下载按钮。分类视图和厂商视图各出一版，数据都从 `manifest.json` 读，标题和统计数字由代码生成而非手写。

版式硬规则（细节见 `references/layouts.md`）：

- 白底或浅灰底（`#F4F5F7`），绝不用深色底配黑图标
- 一览图默认 **4 列**，单元格 282×214，图标 116px，名称 17px 粗体居中，英文名 12px 灰色
- 标题后带计数（`语言模型（12）`），副标题一行列出英文名，底部一行注明文件位置与来源
- 两列同格放多个条目时，第二个的 x 坐标要按第一个文本的实际宽度推进（`textlength`），不要用固定步长，否则长名字会压到下一个图标上

## 第 5 步：核验，必须看图

生成完立刻拼图或截图看，不要只信脚本没报错：

- 联系表直接用看图工具检查：有没有空白格、糊图、错标、文字压字、标签被裁
- HTML 用无头浏览器截图：`msedge --headless=new --disable-gpu --window-size=1240,1400 --screenshot=out.png "file:///..."`，中文路径要 URL 编码
- 重点看 `manifest` 里 `wordmark: true` 的项：文字是否完整落在圆角框内、粗细是否与其他官方图标视觉重量相当

## 交付时说什么

除了文件位置，至少交代三件事：**哪些品牌有官方彩色版、哪些只有单色（及原因）、哪些是自绘的**。用户拿去做课件时会直接引用这些图标，来源和许可必须能追溯。

README 里固定写入：单色版来自 LobeHub Icons（MIT）、彩色版来自 LobeHub 或 Simple Icons（CC0）、自绘项单独说明；商标权归各权利人，仅用于教学研究与演示等合理引用。

## 环境要点

- `pip install resvg-py pillow fonttools`。SVG 转 PNG 用 `resvg_py`（`cairosvg` 在 Windows 上常装不上）
- `resvg_py.svg_to_bytes(svg_string=..., width=, height=, background=None)` 支持透明底
- PIL 的 `paste` 坐标必须是 int，浮点会抛 `TypeError`
- 批量抓取间隔 0.2~0.3 秒，避免触发限流

## 参考

- `references/sources.md` —— 源地址、slug 对照表、已确认无矢量源的品牌、favicon 兜底写法、源外搜索的第三方矢量站清单、官网内联 SVG 提取要点
- `references/layouts.md` —— 一览图与总览页的完整参数、卡片结构、HTML 风格骨架
- `scripts/extract_inline_svg.py` —— 官网内联 SVG 提取（扫描打分 → 三色派生 → 预览 → manifest）
- 配套技能 `multi-search-engine` —— 16 引擎搜索模板与反爬 Cookie 流程，本技能第 3 步的"源外搜索"直接复用它，不重复实现

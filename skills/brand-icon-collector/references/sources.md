# 图标源与 slug 对照

## 源地址

| 源 | 取法 | 许可 | 特点 |
| --- | --- | --- | --- |
| LobeHub Icons | `https://registry.npmmirror.com/@lobehub/icons-static-svg/latest/files/icons/{name}.svg` | MIT | AI/科技品牌最全，`{name}-color.svg` 常有官方彩色变体 |
| Simple Icons | `https://cdn.simpleicons.org/{slug}` | CC0 | 通用品牌，SVG 根节点带 `fill="#RRGGBB"` 官方品牌色 |
| svgl | `https://api.svgl.app`（GET 返回全量数组） | 混合 | 每条含 `title` / `category` / `route`，适合检索确认有无官方矢量 |
| 官网 favicon | 抓页面 `<link rel="icon">` / `apple-touch-icon` | 商标 | 兜底用，多为位图 |

**不要用 `unpkg.com` 取 LobeHub**——国内网络环境基本不通，返回 000。npmmirror 镜像可用且同步最新版本。

Simple Icons 的 CDN 支持加色：`https://cdn.simpleicons.org/deepseek/000000`（末尾追加六位色值可直接换色）。

## slug / 图标名对照（实测）

| 品牌 | LobeHub 图标名 | Simple Icons slug | 备注 |
| --- | --- | --- | --- |
| DeepSeek | `deepseek` | `deepseek` | 彩色 `deepseek-color` 也存在，但 Simple Icons 的官方色（#5786FE）更准 |
| OpenAI / ChatGPT | `openai` | — | 官方标准色即黑，无彩色版；`chatgpt` 不是 slug |
| Claude | `claude` | `claude` | 彩色 #D97757 |
| Anthropic（公司标） | `anthropic` | `anthropic` | 与 Claude 是两个不同标识，别混 |
| Grok / xAI | `grok` | — | 仅单色；`xai` 不存在，`x` 是推特 |
| 豆包 | `doubao` | — | 有 `doubao-color`（渐变） |
| Kimi | `kimi` | `kimi` | 公司 slug 是 `moonshotai` |
| 智谱 GLM | `zhipu` | — | `glm` / `chatglm` 在 LobeHub 只有 `chatglm`，Simple Icons 无 |
| MiniMax | `minimax` | `minimax` | 有彩色变体 |
| Gemini | `gemini` | `googlegemini` | Simple Icons 里 `gemini` 是 404 |
| 通义千问 Qwen | `qwen` | `qwen` | LobeHub 的 `qwen-color` 实为无填充单色文件，用 Simple Icons 的 #6950EF |
| Meta | `meta` | `meta` | 有 `meta-color`（蓝渐变）；另有 `metaai` 是 Meta AI 助手标 |
| Midjourney | `midjourney` | — | 仅单色 |
| DALL·E | `dalle` | — | 有 `dalle-color` |
| FLUX | `flux` | `flux` | Simple Icons 色值 #5468FF |
| Stable Diffusion | `stability` | — | 有 `stability-color`；`stablediffusion` 是 404 |
| Ideogram | `ideogram` | — | 仅单色 |
| Adobe Firefly | `adobefirefly` | — | 有彩色变体 |
| 即梦 Dreamina | `jimeng` | — | 有彩色变体；官网 `jimeng.jianying.com` |
| 混元 | `hunyuan` | — | 有彩色变体 |
| CogView | `cogview` | — | 有 `cogview-color` |
| ComfyUI | `comfyui` | — | 有彩色变体 |
| Sora | `sora` | — | 有 `sora-color` |
| Runway | `runway` | — | 仅单色 |
| Pika | `pika` | — | 仅单色 |
| Luma | `luma` | — | 有 `luma-color`；`lumalabs` 是 404 |
| 可灵 Kling | `kling` | — | 有 `kling-color` |
| 海螺 Hailuo | `hailuo` | — | 有 `hailuo-color` |
| Vidu | `vidu` | — | 有彩色变体 |
| PixVerse | `pixverse` | — | 有彩色变体 |
| CogVideoX | `cogview` 同源目录下有 `cogvideo` | — | 有 `cogvideo-color` |
| Hedra | `hedra` | — | 仅单色 |

## 已确认无官方矢量源的品牌

以下在 LobeHub / Simple Icons / svgl 三处均无矢量文件（2026-11 实测），且这些产品本身以文字标识为主：

- 通义万相 Wan（官网 `wan.video`，favicon 为 ico）
- Seedream、Seedance（字节 Seed 系列，标识为 `ByteDance｜Seed` 文字组合）
- Veo（Google，只有 "Veo" 字样，无独立图形）

处理方式：用 `iconkit.py wordmark` 自绘，并在版式中打标签说明。

## favicon 兜底写法

```bash
curl -sL -A "Mozilla/5.0 ... Chrome/120" "https://站点/" -o page.html
grep -o -i '<link[^>]*rel="[^"]*icon[^"]*"[^>]*>' page.html
```

拿到 URL 后可直接下载。注意 ico 格式 PIL 能读，但尺寸通常只有 32/48px，放大后不可用——只能做小尺寸徽标，不能当矢量交付。

## 官网内联 SVG 提取要点

用 `scripts/extract_inline_svg.py --url <官网> --out <目录> --name <slug>`，自动扫描 → 打分 → 派生彩色/单色/白色 + PNG + 预览 + manifest。以下为实测（wps.com）沉淀的要点：

**找哪个站**

- 国内站与国际站资产质量可能天差地别：wps.cn favicon 仅 32px base64，wps.com 导航栏却有 122×28 完整矢量字标。**两个区域官网都查**
- 官网打不开时，新闻稿子页、关于我们页、帮助中心的页头同样可能内联 logo

**页内位置信号**

- 导航栏 logo 的 `<svg>` 前后 300 字符内通常含 `logo` / `brand`（脚本按此加分）
- logo 类 SVG 的特征：viewBox 宽高比接近品牌标形态（字标扁长如 122×28，图形标方形如 27.759²）、path 数 ≥ 2、fill 为具体品牌色
- 28×28 左右的多色图标常是**同厂商产品家族图标**（WPS 全家桶各产品标），可顺带收集
- 16×16 及以下的单 path 图标基本是 UI 箭头/菜单，脚本已靠打分排到末尾

**技术坑**

- `<path>` 非自闭合写法（`<path ...>` 缺 `/>`）很常见：整段提取时文档自洽无碍；**截取子集（按 fill 拆分图形标/字标）时必须补 `/>`**，否则 resvg 报 `expected 'path' tag`
- 框架噪声属性（Vue `data-v-xxx` 等）需清洗
- 字标与图形标在同一 SVG 里靠 fill 颜色区分（红 path = 图形标、黑 path = 字母），按 fill 拆分即可；**fill 色值即官方品牌色**（WPS 案例：#FF1B1F）
- 渐变填充（`fill="url(#...)"`）无法替换 fill 做单色/白色版，只能交付彩色原版
- `<svg>` 嵌套超过一层的块会被扫描器丢弃（logo 场景罕见）
- 部分官网用位图/字体渲染 logo，页面无内联 SVG——脚本会明确提示，此时退回 apple-touch-icon（通常 180px，最大官方位图）或 favicon

**许可**

内联 SVG 同样是商标。README 记录提取自哪个页面；仅用于教学、研究与演示等合理引用。

## 源外搜索（三源 probe 全失败时的升级路径）

用 `iconkit.py search-hints --slugs <品牌>` 生成查询链接，配合 `multi-search-engine` 技能的引擎模板与反爬流程执行（获取地址见 SKILL.md 参考；未安装时按下表引擎要点手工执行）。

**实测网络要点（2026-11）**

| 引擎 | 可达性 | 关键点 |
| --- | --- | --- |
| 搜狗微信 | 直连可用 | 中文产品发布稿/品牌介绍的主入口 |
| 百度 | 需先取会话 | 先 GET 首页拿 Cookie 再搜，否则返回 1.5KB 反爬空壳页 |
| Bing CN / INT | 可用 | `ensearch=1` 切国际版 |
| Google / DDG | 视网络而定 | 不通就换国内引擎，别死磕 |

**第三方矢量站与可信度**

| 站点 | 特点 | 风险 |
| --- | --- | --- |
| 官网新闻稿 / 品牌页 | 唯一权威来源 | 无 |
| `github.com/gilbarbara/logos` | 约 500+ 品牌 SVG，质量高、带来源 | 覆盖以国际品牌为主 |
| Wikimedia Commons | 有官方 SVG 的品牌较全 | 部分为旧版标 |
| vectorseek / seeklogo / logowik / worldvectorlogo | 收录广、好搜到 | 常见粉丝重绘旧版；许可多为"仅编辑用途" |

**核验规则（不可跳过）**：从第三方站取的标，必须回官网 favicon、新闻稿页头或 og-image 核对形状与配色是否一致；对不上就不用。README 里记录实际出处与许可限制。宁可自绘文字标识，也不用一个对不上的旧版标。

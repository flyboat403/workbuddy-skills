# WorkBuddy 技能合集

个人在 [WorkBuddy](https://www.workbuddy.cn)（腾讯 AI 工作台）中积累与收集的技能（Skills）合集。每个子目录是一个独立技能，含 `SKILL.md`（触发与执行说明）及配套的 `scripts/`、`references/`。

## 合集清单

| 技能 | 用途 | 类型 |
| --- | --- | --- |
| [brand-icon-collector](skills/brand-icon-collector/) | 批量收集品牌/产品官方图标（logo），导出 SVG + 512px PNG，按模态/厂商排一览图与矩阵 | 自创 · MIT |
| [session-temp-cleanup](skills/session-temp-cleanup/) | 会话/任务收尾时的临时文件与中间产物清理，含回收站空间释放诊断 | 自创 |
| [pexels-image-downloader](skills/pexels-image-downloader/) | Pexels API 搜索下载高质量免费图片，自动调整尺寸与格式验证 | 收集（[openclaw/skills](https://github.com/openclaw/skills)） |
| [chinese-literature](skills/chinese-literature/) | 中文文献检索与采集（CNKI 注入搜索 / RSS 顶刊监控 / NCPSSD 开放获取） | 收集（[MartyYao/Chinese-Literature-Skill](https://github.com/MartyYao/Chinese-Literature-Skill)，MIT，含本地审计记录） |
| [steelman](skills/steelman/) | 对问题做双向钢人论证：重述问题、正反最强论证、定位分歧 | 自创 |
| [md2wechat](skills/md2wechat/) | Markdown 转微信公众号文章 HTML，含主题排版与封面图 | 收集（SkillHub v3.1.0） |
| [z-video-downloader](skills/z-video-downloader/) | 视频链接/清单批量下载（YouTube/B站/抖音/视频号等），断点续传 | 收集 + 本地修补（补丁记录见其 LOCAL-PATCHES.md） |
| [official-document-workflow](skills/official-document-workflow/) | 中文公文写作/审改/排版（GB/T 9704-2012），docx 输出 | 收集（SkillHub v1.0.0） |
| [jianbao-generator](skills/jianbao-generator/) | 微信文章套版生成为名师工作室简报 docx（红头/仿宋/自动编号） | 自创（含简报模板） |

## 安装

方式一（推荐）：将单个技能目录复制到 WorkBuddy 用户级技能目录：

```bash
cp -r skills/brand-icon-collector ~/.workbuddy-ai/skills/
```

方式二：在 WorkBuddy「技能管理 → 本地技能 → 导入技能」中选择对应目录的 `SKILL.md`。

## 依赖提示

- `brand-icon-collector`：`pip install resvg-py pillow fonttools`（详见其 SKILL.md「环境要点」）
- `pexels-image-downloader`：需配置 `PEXELS_API_KEY` 环境变量（[免费申请](https://www.pexels.com/api/)）
- `z-video-downloader`：依赖 yt-dlp，见其 SKILL.md
- `chinese-literature`：CNKI 通道依赖浏览器注入环境，NCPSSD 通道零依赖

## 来源与许可

- 标注「自创」的技能为本仓库作者编写，采用 MIT 许可（见 `skills/brand-icon-collector/LICENSE.txt`）。
- 标注「收集」的技能版权归原作者所有；各目录内的 `_meta.json` / `WORKBUDDY-AUDIT.md` 保留了原始出处与版本信息，便于溯源与同步上游。
- 品牌图标检索类技能仅整理工具与流程；各品牌标识商标权归其权利人所有，仅限教学、研究与演示等合理引用。

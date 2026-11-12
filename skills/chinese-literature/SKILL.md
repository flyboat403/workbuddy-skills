---
name: chinese-literature
description: "中文文献检索与采集（三通道：CNKI 浏览器注入搜索 + CNKI RSS 顶刊监控 + NCPSSD 开放获取搜索）。CNKI 通道支持关键词检索、CSSCI/EI/北大核心/CSCD 高级过滤、论文详情提取（摘要/关键词/DOI/基金/分类号）、期刊收录查询、Zotero 批量导出；NCPSSD 通道零依赖、无需认证，返回题名/作者/刊名/年卷期页/摘要/关键词/DOI/基金/全文链接。用于文献综述、系统综述中的中文文献层。触发词：中文文献、查知网、知网、CNKI、检索中文论文、中文期刊、监控顶刊、CSSCI、北大核心、中文核心期刊、CSCD、文献综述中文部分、国家哲学社会科学文献中心、NCPSSD、社科文献、Chinese literature、CNKI search。"
metadata:
  version: "0.1.1"
  upstream_repo: MartyYao/Chinese-Literature-Skill
  upstream_skill: chinese-literature
  ported_on: "2026-10-06"
  license: MIT
---

> ## WorkBuddy 适配说明（移植层，非上游原文）
>
> 本技能移植自 [MartyYao/Chinese-Literature-Skill](https://github.com/MartyYao/Chinese-Literature-Skill)
> v0.1.1（MIT）。以下为本机新增内容；**其下方自「# Chinese Literature Skill」起的正文为上游原文，未作改动**。
>
> ### 一、⚠️ 合规边界（本技能最重要的部分，先读这一节）
>
> 本技能的三个数据通道都指向**已发布明确爬取指令**的服务端。下表为 2026-10-06 实测的 robots.txt：
>
> | 通道 | 目标主机 | 该主机 robots.txt |
> |---|---|---|
> | CNKI 浏览器搜索 | `kns.cnki.net` | `User-agent: *` + **`Disallow: /`** |
> | CNKI RSS | `navi.cnki.net`、`rss.cnki.net` | 均 `User-agent: *` + **`Disallow: /`** |
> | NCPSSD 搜索 | `www.ncpssd.cn`（自身无 robots）<br>`ncpssd.org`（同一服务） | `.org` 上是 **`Disallow: /searchHandler/`** —— 正是该接口路径 |
>
> **因此本技能刻意与 `academic-research-deep-research` 并存，不合并、不互相引用。**
> 后者 §Legal and compliance boundary 明文写着 *"Zero scraping. CNKI, Wanfang, and VIP search
> and full-text pages are never fetched or parsed."* —— 本技能做的正是那件事。
> **两份文件各自陈述自己的边界；不得把其中一份的结论当作另一份的授权**，这是它们同时存在的唯一风险。
>
> **使用前请自行判断**：确认你有权以这些方式访问上述服务（例如经由本人所属机构已购授权），并遵守其服务条款。
> 本技能**不做任何绕过访问控制的动作**，也**不提供验证码识别**：CNKI 出现腾讯滑块时，按上游设计
> **停下来交给人工完成**（见下方 §验证码处理）。
>
> ### 二、依赖映射（WorkBuddy 环境）
>
> 上游的 CNKI 浏览器通道假定 Camofox 容器或 Chrome DevTools MCP。本机替代：
>
> | 上游假定 | WorkBuddy 替代 |
> |---|---|
> | `mcp__chrome-devtools__navigate_page` / `evaluate_script` | 技能 **`agent-browser`** 或 **`playwright-cli`**（打开页面 + 注入 JS） |
> | Camofox 容器（`camofox-manager.sh`） | 无对应物。改用上面的浏览器技能，或自行在浏览器里粘贴 `scripts/cnki-search.js` |
> | `browser_console(expression=…)` | 浏览器技能的「执行脚本」能力 |
>
> **CNKI RSS 与 NCPSSD 两个通道只依赖 Python 3 标准库**，不需要浏览器，开箱可用。
>
> ### 三、本机运行方式
>
> ```bash
> # 用本机托管解释器的绝对路径（不要用裸 python3）
> PY="~/.workbuddy-ai/binaries/python/versions/3.13.12/python.exe"
> SK="$HOME/.workbuddy-ai/skills/chinese-literature"
>
> "$PY" "$SK/scripts/cnki-rss.py" --list                 # 列出期刊代码（离线，不发请求）
> "$PY" "$SK/scripts/cnki-rss.py" --init                 # 交互式配置期刊
> "$PY" "$SK/scripts/ncpssd-search.py" 数字经济 --pages 1
> ```
>
> ⚠️ **`cnki-rss.py --init` 会把 `journals.json` 写到「当前工作目录」，不是技能目录**
> （上游 `init_config()` 用的是 `Path.cwd()`）。想让它跟着技能走，先 `cd` 到 `scripts/` 再运行，
> 或直接复制 `scripts/journals.template.json` 为 `scripts/journals.json` 再编辑。
>
> ⚠️ **不要在 `~/.workbuddy-ai/skills/` 下留备份副本** —— 备份目录里的 `SKILL.md` 会被技能加载器
> 当成第二个技能。备份请放 `~/.workbuddy-ai/_skill_backups/`。
>
> ### 四、与上游的差异 / 未实测项
>
> - 上游 `multi-agent/` 下三份说明（hermes / claude-code / pi-agent）**保留原样以尊重上游**，
>   WorkBuddy 用不上。注意 `for-claude-code.md` 引用的 `claude-skills/`、`claude-agents/`
>   目录**在上游仓库里并不存在**，且 `git clone` 仍是 `YOUR_REPO` 占位符 —— **那份安装说明是坏的，不要照做**。
> - **CNKI 两个通道本机未做实测**（有意为之：三主机 `Disallow: /`，不主动发起请求）。
>   脚本逻辑与选择器取自上游及其来源 `cookjohn/cnki-skills`（MIT）。
> - **NCPSSD 通道已本机实测可用**（实测记录见 `WORKBUDDY-AUDIT.md`）。
> - 安全审计：**P2（安全）** —— 无 `subprocess` / `eval` / `exec` / `pickle` / `socket` /
>   文件删除；硬编码端点仅 CNKI 三主机与 NCPSSD，无遥测、无外传。完整记录见 `WORKBUDDY-AUDIT.md`。
> - **更新方式**：本技能不是 git 仓库（拷贝式导入）。同步上游请走 `skill-sync-from-github`
>   的流程（备份 → 比对 → 审计 → 同步），并保留本 frontmatter 与本节适配说明。
>
> ---

# Chinese Literature Skill

中文文献检索与采集。两通道策略，按场景自动切换。

## 两通道总览

| 通道 | 技术方案 | 适用场景 | 可靠性 |
|------|---------|---------|--------|
| **CNKI 浏览器搜索** | Camofox + JS 注入（`browser_console`） | 主动关键词搜索、高级检索（CSSCI 过滤）、论文详情、期刊查询 | ✅ 已验证：搜索"数字经济"返回 134,836 条结构化结果 |
| **CNKI RSS** | Python urllib + CookieJar（两步认证） | 日常监控顶刊新论文 | ✅ 稳定，无验证码 |

## 快速使用

### 场景 1：关键词搜索知网

```python
# 1. 确保 Camofox 已启动
# 2. 导航到 CNKI 搜索页
# 3. 注入 JS 执行搜索 + 提取
```

完整流程见 `references/cnki-browser-search.md`，JS 代码见 `scripts/cnki-search.js`。

### 场景 2：监控顶刊 RSS

```python
# 使用 scripts/cnki-rss.py 采集
python3 scripts/cnki-rss.py JJYJ GLSJ --output md
```

## 与 paper-workflow 的集成

在 paper-workflow 的阶段 1（文献检索与综述）中，中文文献部分由本技能提供：

```
paper-workflow 阶段 1 流程（中文部分）:

1. 运行 CNKI RSS 采集 → 获取顶刊最新论文
2. 按用户关键词运行 CNKI 浏览器搜索 → 获取针对性结果
3. 合并 → 去重 → 分类 → 写入 Obsidian 02-文献/
```

**触发条件**：当 paper-workflow 处于阶段 1，且用户明确要求搜索中文文献时，自动加载本技能。

## 验证码处理

CNKI 使用腾讯滑块验证码（`#tcaptcha_transform_dy`）。检测逻辑：

```javascript
const cap = document.querySelector('#tcaptcha_transform_dy');
// SDK 预加载时 top=-1000000px（屏幕外），只有 top>=0 才真正可见
if (cap && cap.getBoundingClientRect().top >= 0) {
  return { error: 'captcha' };
}
```

检测到验证码 → 暂停 → 通知用户手动完成 → 用户确认后重试。

## 注意事项

1. **CNKI 搜索无需登录**，但下载 PDF 需要机构登录
2. **搜索不要太快**——CNKI 对短时间大量请求会触发验证码
3. **Camofox 需要预热**约 15 秒（`camofox-manager.sh start`）
4. **RSS 每刊最多返回 20 篇**，时间范围有限
5. **中文期刊预出版**标注未来月份，用状态文件增量处理

## 本技能依赖

- Camofox 浏览器容器（`~/.hermes/scripts/camofox-manager.sh`）
- Python 3（urllib, xml.etree.ElementTree）
- 可选：Zotero（用于文献管理）

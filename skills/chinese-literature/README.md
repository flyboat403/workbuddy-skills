# Chinese Literature Skill v0.1.1

中文文献检索与采集技能——面向实证研究的通用文献管线。支持三通道策略：

- **CNKI 浏览器搜索**（按需主动搜索，含 CSSCI 高级过滤）
- **CNKI RSS 推送**（日常顶刊监控）
- **国家哲学社会科学文献中心 API**（开放获取，无需任何认证）

> **致谢**：本项目的 CNKI 浏览器搜索方案基于 [cookjohn/cnki-skills](https://github.com/cookjohn/cnki-skills)（MIT License），原项目为 Claude Code 提供了完整的 CNKI 前端 CSS 选择器和 JS 注入方案。在此基础之上，本项目新增了 CNKI RSS 推送通道、NCPSSD API 搜索通道、高级检索（CSSCI/EI/北大核心过滤）、论文详情提取、多 Agent 适配和首次安装配置向导。

> **适用学科**：本技能本身是**全学科通用**的，不限定任何研究领域。内置的默认期刊列表为经管类（仅因开发者的研究背景在此），用户通过 `python3 cnki-rss.py --init` 可自由配置任何 CNKI 收录的期刊——法学、社会学、教育学、工学、医学等均支持。NCPSSD 通道更是覆盖了全学科的中文社科文献。

## 概览

三通道策略覆盖中文文献检索需求：

```
用户需求
  │
  ├─ 日常监控顶刊 → CNKI RSS（被动，轻量，稳定）
  ├─ 主动关键词搜索 → CNKI 浏览器搜索（灵活，含 CSSCI 高级检索）
  └─ 开放获取搜索 → NCPSSD API（无需认证，不受反爬限制）
```

## 三通道决策矩阵

| 场景 | 通道 | 延迟 | 是否需要登录 | 验证码风险 |
|------|------|------|-------------|-----------|
| 监控经济研究/管理世界等顶刊最新论文 | CNKI RSS | ~1s/刊 | 否 | 无 |
| 跨关键词系统搜索，需 CSSCI/EI 过滤 | CNKI 浏览器搜索 | ~3-5s/次 | 否（搜索时） | 有（腾讯滑块） |
| 开放获取文献搜索（全学科） | **NCPSSD API** | ~0.5s/次 | **否** | **无** |
| 查看论文详情（摘要/关键词/DOI/基金） | CNKI 浏览器搜索 / NCPSSD | ~2s/篇 | 否 | 有/无 |
| 查期刊收录（是否北大核心/CSSCI/CSCD） | CNKI 浏览器搜索 | ~3s/次 | 否 | 有 |
| 浏览期刊目录 | CNKI 浏览器搜索 | ~2s/次 | 否 | 有 |
| 下载 PDF（开放获取） | NCPSSD | ~2s/篇 | 否 | 无 |
| 下载 PDF（CNKI） | CNKI 浏览器搜索 | ~5s/篇 | **是** | 有 |

## 首次安装

### 第 1 步：配置 CNKI RSS 期刊列表

CNKI RSS 通道需要你配置关注的期刊。运行配置向导：

```bash
cd Chinese\ Literature\ skill/scripts/
python3 cnki-rss.py --init
```

根据提示选择学科分组（经济学/管理学/会计与金融/综合社科），或自定义期刊。配置会自动写入 `journals.json`。

**以后需要修改期刊列表**，直接编辑 `journals.json`，增删期刊代码即可。代码可在 `https://navi.cnki.net/knavi/` 搜索期刊名后从 URL 中获取（4 位字母）。

### 第 2 步：验证 RSS 通道

```bash
python3 cnki-rss.py --all --output text
```

### 第 3 步：验证 NCPSSD 通道（推荐）

NCPSSD 通道不需要任何配置，直接运行：

```bash
python3 scripts/ncpssd-search.py 数字经济 --output text --pages 1
```

### 第 4 步：验证浏览器搜索通道（可选）

浏览器搜索需要 Camofox 浏览器环境（见下方依赖说明）。

## 项目结构

```
Chinese Literature skill/
├── README.md                        ← 本文件，GitHub 入口
├── SKILL.md                         ← Hermes 主技能文件
├── references/
│   ├── cnki-browser-search.md       ← CNKI 浏览器搜索方法（CSS 选择器、高级检索表单）
│   └── cnki-rss-access.md           ← CNKI RSS 两步 Cookie 认证
├── scripts/
│   ├── cnki-search.js               ← CNKI 浏览器搜索 JS 注入代码
│   ├── cnki-rss.py                  ← RSS 采集 Python 脚本
│   ├── ncpssd-search.py             ← NCPSSD API 搜索 Python 脚本
│   └── journals.template.json       ← 期刊配置模板
└── multi-agent/
    ├── for-hermes.md                ← Hermes Agent 使用说明
    ├── for-claude-code.md           ← Claude Code 适配说明
    └── for-pi-agent.md              ← Pi Agent 适配说明
```

## 使用方式

### 场景 1：CNKI RSS 顶刊监控

```bash
# 采集配置中所有期刊
python3 scripts/cnki-rss.py --all --output md

# 只采集特定期刊（不依赖配置文件）
python3 scripts/cnki-rss.py JJYJ GLSJ JRYJ

# 只返回最近 7 天的论文
python3 scripts/cnki-rss.py --all --days 7 --output text

# 查看当前配置
python3 scripts/cnki-rss.py --config

# 重新配置期刊列表
python3 scripts/cnki-rss.py --init
```

### 场景 2：NCPSSD 开放获取搜索

```bash
# 基本搜索
python3 scripts/ncpssd-search.py 数字经济

# 指定搜索字段
python3 scripts/ncpssd-search.py 数字经济 --field title

# 多页获取
python3 scripts/ncpssd-search.py 企业数字化转型 --pages 3

# Markdown 格式输出
python3 scripts/ncpssd-search.py 数字经济 --output md

# 按作者搜索
python3 scripts/ncpssd-search.py 吴非 --field creator
```

**NCPSSD 通道特点：**
- 无需任何认证、无需登录
- 无验证码、无反爬限制
- 返回结构化 JSON 数据（标题、作者、期刊、日期、摘要、关键词、DOI、PDF 链接）
- 覆盖全学科社会科学文献
- PDF 全文可开放获取下载

### 场景 3：CNKI 浏览器主动搜索

需浏览器环境（Camofox/Hermes 或 Chrome DevTools），注入 `scripts/cnki-search.js` 执行搜索。

完整流程见 `references/cnki-browser-search.md`。

## 与 paper-workflow 的集成

本技能专为 `paper-workflow` 的阶段 1（文献检索与综述）设计，提供中文文献检索层：

```
paper-workflow 阶段 1
  ├── 中文文献 ← Chinese Literature Skill
  │   ├── CNKI RSS（推送式监控）
  │   ├── CNKI 搜索（按需检索）
  │   └── NCPSSD（开放获取补充）
  ├── 英文文献 ← academic-literature-collector
  └── 去重 → Zotero → 综述撰写
```

## 安装到不同 Agent

### Hermes

```bash
cp -r 'Chinese Literature skill' ~/.hermes/skills/research/chinese-literature/
hermes skills list | grep chinese
```

### Claude Code

```bash
cp -r 'Chinese Literature skill/skills/' ~/.claude/skills/
cp -r 'Chinese Literature skill/multi-agent/for-claude-code.md' ~/.claude/agents/chinese-literature.md
```

### Pi Agent

参考 `multi-agent/for-pi-agent.md`。

## 后续计划

当前版本以 CNKI 和 NCPSSD 为主要数据源。后续计划加入更多中文文献来源：

- **万方数据** — 浏览器搜索方案（与 CNKI 类似的 JS 注入模式）
- **维普期刊** — 浏览器搜索方案
- **Crossref/OpenAlex 中文覆盖** — 通过 ISSN 匹配中文期刊

欢迎提交 Issue 或 PR 贡献更多数据源接入。

## 依赖

- **CNKI RSS 通道**：Python 3（urllib, xml.etree.ElementTree）
- **CNKI 浏览器搜索通道**：Camofox 浏览器容器（macOS）或 Chrome 远程调试
- **NCPSSD 通道**：Python 3（urllib，**零依赖**）
- **可选**：Zotero（用于文献管理）

## 授权

MIT License

# Claude Code 使用说明

本技能兼容 Claude Code 的 Chrome DevTools MCP 模式。原项目 cookjohn/cnki-skills（789⭐）是此方案的原型。

## 前置条件

1. 已安装 Claude Code CLI
2. Chrome 浏览器（用于远程调试）
3. Chrome DevTools MCP 服务器已配置

```bash
claude mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest
```

## 安装

```bash
git clone https://github.com/YOUR_REPO/chinese-literature-skill.git
cp -r chinese-literature-skill/claude-skills/ .claude/skills/
cp -r chinese-literature-skill/claude-agents/ .claude/agents/
```

## 启动 Chrome 远程调试

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222
```

## 工具映射

| 操作 | Claude Code MCP 工具 |
|------|---------------------|
| 导航 | `mcp__chrome-devtools__navigate_page` |
| 执行 JS | `mcp__chrome-devtools__evaluate_script` |
| 翻页 | `mcp__chrome-devtools__navigate_page`（直接导航到搜索结果 URL） |
| 标签页管理 | `mcp__chrome-devtools__list_pages` + `select_page` |

## 与 cnki-skills 的关系

本技能中的 CNKI 浏览器搜索部分（CSS 选择器、JS 注入逻辑）直接来自 cookjohn/cnki-skills。如果你已经在用 Claude Code + 那个项目，无需额外配置。本技能额外提供了 CNKI RSS 采集通道。

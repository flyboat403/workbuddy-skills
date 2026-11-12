# Hermes Agent 使用说明

本技能在 Hermes 中通过 `skill_view` 加载，核心操作通过内置浏览器工具（Camofox）完成。

## 加载技能

会话中直接触发关键词即可自动加载，或手动加载：

```
skill_view(name='chinese-literature')
```

## 工具映射

| 操作 | Hermes 工具 | 对应 cnki-skills 的 MCP 工具 |
|------|------------|------------------------------|
| 导航到 CNKI | `browser_navigate(url)` | `mcp__chrome-devtools__navigate_page` |
| 执行搜索 JS | `browser_console(expression=js_code)` | `mcp__chrome-devtools__evaluate_script` |
| 读取页面 | `browser_snapshot()` / `browser_vision()` | `mcp__chrome-devtools__snapshot` |
| 翻页 | `browser_console(expression=page_js)` | `mcp__chrome-devtools__evaluate_script` |
| 点击元素 | `browser_click(ref)` | `mcp__chrome-devtools__click_element` |
| 输入文字 | `browser_type(ref, text)` | `mcp__chrome-devtools__fill_input` |

## 启动 Camofox

```bash
# 首次使用前或 Camofox 未运行时
bash ~/.hermes/scripts/camofox-manager.sh start
# 预热约 15 秒
```

## 典型调用流程

### 关键词搜索

```python
# 1. 启动 Camofox（如未启动）
# 2. 导航到 CNKI 搜索页
browser_navigate("https://kns.cnki.net/kns8s/search")

# 3. 注入搜索 JS（替换关键词）
browser_console(expression=f"({cnki_search_js})().then(r => r)")

# 4. 解析返回的结构化结果
```

### 高级检索（CSSCI 过滤）

```python
browser_navigate("https://kns.cnki.net/kns/AdvSearch?classid=7NS01R8M")
browser_console(expression=f"({cnki_advanced_search_js})().then(r => r)")
```

### RSS 采集

```python
# 直接调用
terminal("python3 scripts/cnki-rss.py JJYJ GLSJ")
```

## 注意

- Camofox 必须启动，否则 browser_* 不可用
- CNKI 搜索无需登录，但下载 PDF 需要
- 检测到验证码时输出提示并等待用户手动处理

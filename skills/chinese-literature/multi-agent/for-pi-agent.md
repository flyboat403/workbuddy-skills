# Pi Agent 使用说明

Pi Agent 通过 CLI 调用，没有内置浏览器环境。本技能中只有 **CNKI RSS 通道** 可以在 Pi 中直接使用。

## 可用通道

### ✅ CNKI RSS（可用）

```bash
# 直接运行 Python 脚本
python3 scripts/cnki-rss.py JJYJ GLSJ --output md
```

Pi 可以调用本技能中的 `scripts/cnki-rss.py` 完成 RSS 采集。通过 `--output md` 获取 markdown 格式结果。

### ⚠️ CNKI 浏览器搜索（受限）

Pi Agent 没有浏览器环境，需要通过 delegate 给 Claude Code 或 Hermes 来执行浏览器操作。

## 集成方式

```yaml
# 在 Pi 的 config 中引用本技能
skills:
  - name: chinese-literature
    path: /path/to/Chinese Literature skill/
    channels:
      - rss: available
      - browser: not-available
      - pubscholar: not-available
```

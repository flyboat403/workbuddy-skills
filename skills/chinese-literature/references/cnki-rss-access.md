# CNKI RSS 采集参考

通过 CNKI 的 RSS feed 被动收集中文期刊最新论文。适合日常监控，无需处理验证码。

## 两步认证（关键）

CNKI RSS 需要先建立 Cookie 会话，直接请求返回 200 + 空 body。

```python
import urllib.request, http.cookiejar, xml.etree.ElementTree as ET

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# Step 1：访问期刊主页获取 Cookie（必须）
journal_url = f"https://navi.cnki.net/knavi/journals/{CNKI_CODE}/detail?uniplatform=NZKPT"
opener.open(urllib.request.Request(journal_url, headers=headers), timeout=15)

# Step 2：用同一 opener 抓 RSS
rss_url = f"https://navi.cnki.net/knavi/rss/{CNKI_CODE}"
resp = opener.open(urllib.request.Request(rss_url, headers=headers), timeout=15)
body = resp.read().decode("utf-8", errors="replace")
root = ET.fromstring(body)
```

## RSS URL 格式

标准格式：`https://navi.cnki.net/knavi/rss/{CNKI_CODE}`

例外——中国社会科学：`https://rss.cnki.net/knavi/rss/ZSHK?pcode=CJFD,CCJD`

## 期刊代码速查（公司金融相关）

| 期刊 | 代码 | 备注 |
|------|------|------|
| 经济研究 | JJYJ | |
| 管理世界 | GLSJ | |
| 会计研究 | KJYJ | |
| 金融研究 | JRYJ | |
| 中国工业经济 | GGYY | |
| 世界经济 | SJJJ | |
| 经济学(季刊) | JJXU | |
| 管理科学学报 | JCYJ | |
| 南开管理评论 | LKGP | |
| 公共管理学报 | GGGL | |
| 中国行政管理 | ZXGL | |
| 经济管理 | JJGL | |
| 中国社会科学 | ZSHK | 使用例外 URL |

CNKI 代码在出版物检索页 URL 中可见：`navi.cnki.net/knavi/journals/{CODE}/detail`

## RSS 字段

| 字段 | 说明 |
|------|------|
| `title` | 论文标题（中文） |
| `link` | CNKI 加密链接（需机构订阅） |
| `description` | 摘要 |
| `pubDate` | RFC 2822 格式（如 Tue, 19 May 2026 16:00:00 GMT） |
| `author` | 作者，分号分隔 |

## 增量更新（状态文件策略）

中文期刊每 1-2 个月一期，用状态文件而非绝对天数过滤：

```python
from pathlib import Path
from datetime import datetime

state_file = Path(".lit_collector_state")
now = datetime.utcnow()

if state_file.exists():
    cutoff = datetime.fromisoformat(state_file.read_text().strip())
else:
    cutoff = now  # 首次运行：获取当前全部最新

# 过滤 pubDate >= cutoff 的论文
new_papers = [p for p in papers if parse_date(p["pubDate"]) >= cutoff]

state_file.write_text(now.isoformat())
```

## 注意事项

- 每刊最多返回 20 篇最新论文，不分页
- 包含非论文条目（征稿启事、订阅通知等），需用标题过滤
- 日期格式规范，可直接解析
- 预出版论文标注未来月份，状态文件策略天然处理

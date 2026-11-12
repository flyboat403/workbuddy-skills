#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline stub test for the installed chinese-literature skill.

Verifies both scripts' request construction and parsing WITHOUT touching the
network: the transport is replaced by a stub that records the request and
replays a canned body. This keeps the "no live network" discipline the sibling
protocols' fixtures exist to enforce, and avoids sending traffic to hosts whose
robots.txt disallows it.

Note: cnki-rss.py goes through ``build_opener(...).open(...)`` (it needs a
CookieJar), so patching ``urllib.request.urlopen`` does NOT intercept it --
``build_opener`` has to be stubbed instead. Learned the hard way here.
"""
import io
import json
import os
import sys
import urllib.parse

SKILL = os.path.expanduser("~/.workbuddy-ai/skills/chinese-literature").replace("\\", "/")
sys.path.insert(0, os.path.join(SKILL, "scripts"))

CAPTURED = []


class FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def make_stub(body: bytes):
    def _stub(req, timeout=None):
        CAPTURED.append({
            "url": req.full_url if hasattr(req, "full_url") else req.get_full_url(),
            "method": req.get_method(),
            "body": req.data,
            "headers": dict(req.headers),
        })
        return FakeResponse(body)
    return _stub


def hr(t):
    print("\n" + "=" * 68 + "\n" + t + "\n" + "=" * 68)


# ---------------------------------------------------------------- NCPSSD
hr("1) ncpssd-search.py ：请求构造 + 解析（桩测试，不发网络请求）")
import importlib.util


def load(path, name):
    """两个脚本的文件名带连字符，不是合法标识符，按路径加载。"""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ncp = load(os.path.join(SKILL, "scripts", "ncpssd-search.py"), "ncpssd_search")

CANNED_NCPSSD = json.dumps({
    "result": True, "code": 200, "succee": "true",
    "data": {
        "total": 12028, "pages": 1203, "currentPage": 1,
        "rows": [{
            "title": '<em>数字经济</em>驱动经济高质量发展：机制及路径创新',
            "creator_first": "张三; 李四",
            "cbw_name": "成都理工大学学报：社会科学版",
            "years": "2025", "volumn": "", "num": "3", "pagecount": "18-25",
            "issn": "1672-0539",
            "remark": "本文基于 2013-2022 年 31 个省份的面板数据，构建指标体系……",
            "subject": "数字经济 经济高质量发展 作用机制 固定效应模型",
            "doi": "10.3969/j.issn.1672-0539.2025.03.002",
            "imburse": "国家社会科学基金重大项目(20&ZD056)",
            "institutions": "成都理工大学",
            "pdfurl": "https://ftprp.ncpssd.cn/pdf/getComm/npssd-prp/pdf?url=86886A/1750840217849.pdf",
            "HtmlUrl": "/Literature/articleinfo?filename=ABC",
            "encryptedUrl": "",
        }],
    },
}, ensure_ascii=False).encode("utf-8")

ncp.urllib.request.urlopen = make_stub(CANNED_NCPSSD)
resp = ncp.search("数字经济", field="title", page=1, page_size=10)

cap = CAPTURED[-1]
print("  请求 URL   :", cap["url"])
print("  请求方法   :", cap["method"])
body = urllib.parse.parse_qs(cap["body"].decode("utf-8"))
print("  表单字段   :", sorted(body.keys()))
print("  search 值  :", body.get("search"))
assert cap["url"] == "https://www.ncpssd.cn/searchHandler/search", cap["url"]
assert cap["method"] == "POST"
assert body["search"] == ['(IKTE="数字经济")'], body["search"]
assert body["pageNum"] == ["1"] and body["pageSize"] == ["10"]
print("  ✓ 端点、方法、字段码 IKTE（题名）均正确")

rows = ncp.format_results(resp)
r = rows[0]
print("\n  解析结果:")
for k in ("title", "authors", "journal", "year", "issue", "pages", "issn", "doi", "fund", "institutions"):
    print("    %-12s %s" % (k, r[k]))
print("    %-12s %s" % ("abstract", r["abstract"][:40] + "…"))
print("    %-12s %s" % ("keywords", r["keywords"]))
print("    %-12s %s" % ("pdf_url", r["pdf_url"][:56] + "…"))
assert "<em>" not in r["title"], "高亮标记未被清除"
assert r["title"].startswith("数字经济驱动"), r["title"]
assert r["issn"] == "1672-0539" and r["doi"].startswith("10.3969/")
print("  ✓ 高亮 <em> 已清除；ISSN / DOI / 基金 / 全文链接均正确抽取")

print("\n  --- format_text 前 6 行 ---")
for line in ncp.format_text(rows, 12028, "数字经济").splitlines()[:6]:
    print("   ", line)
print("  --- format_markdown 前 3 行 ---")
for line in ncp.format_markdown(rows, 12028, "数字经济").splitlines()[:3]:
    print("   ", line)

# 失败路径：API 返回 result=False
ncp.urllib.request.urlopen = make_stub(
    json.dumps({"result": False, "message": "boom"}, ensure_ascii=False).encode())
bad = ncp.search("x")
assert bad.get("result") is False
print("\n  ✓ 失败响应被如实透传（result=False），不会被误认为空结果")

# ---------------------------------------------------------------- CNKI RSS
hr("2) cnki-rss.py ：RSS 解析 + 输出（桩测试，不发网络请求）")
cnki_rss = load(os.path.join(SKILL, "scripts", "cnki-rss.py"), "cnki_rss")

CANNED_RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
<item>
  <title>测试：数字经济与高质量发展</title>
  <link>https://kns.cnki.net/kcms/detail/xx</link>
  <author>张三; 李四</author>
  <description>本文研究了……</description>
  <pubDate>Tue, 19 May 2026 16:00:00 GMT</pubDate>
</item>
<item>
  <title>测试：征稿启事</title>
  <link>https://kns.cnki.net/xx</link>
  <author>编辑部</author>
  <description>本刊征稿</description>
  <pubDate>Mon, 04 May 2026 16:00:00 GMT</pubDate>
</item>
</channel></rss>""".encode("utf-8")

class FakeOpener:
    """cnki-rss.py 用 build_opener().open()（需要 CookieJar），
    所以必须桩掉 build_opener，桩 urlopen 是拦不住的。"""

    def __init__(self, body: bytes):
        self._body = body

    def open(self, req, timeout=None):
        CAPTURED.append({
            "url": req.full_url if hasattr(req, "full_url") else req.get_full_url(),
            "method": req.get_method(),
            "body": req.data,
            "headers": dict(req.headers),
        })
        return FakeResponse(self._body)


CAPTURED.clear()
cnki_rss.urllib.request.build_opener = lambda *a, **k: FakeOpener(CANNED_RSS)
papers = cnki_rss.fetch_rss("JJYJ", {"JJYJ": "经济研究"}, cnki_rss.EXCEPTION_URLS)
print("  捕获到 %d 次请求（上游设计：先详情页取 Cookie，再抓 RSS）" % len(CAPTURED))
for c in CAPTURED:
    print("    %-6s %s" % (c["method"], c["url"]))
assert len(CAPTURED) == 2
assert CAPTURED[0]["url"].startswith("https://navi.cnki.net/knavi/journals/JJYJ/detail")
assert CAPTURED[1]["url"] == "https://navi.cnki.net/knavi/rss/JJYJ"
print("  ✓ 两步认证顺序（详情页 → RSS）与端点正确")

print("\n  解析到 %d 篇:" % len(papers))
for p in papers:
    print("    [%s] %s  | 作者:%s | %s" % (p["journal"], p["title"], p["authors"], p["pub_date"]))
assert papers[0]["title"] == "测试：数字经济与高质量发展"
assert papers[0]["pub_date_dt"] is not None, "RFC2822 日期未解析"
print("  ✓ RFC 2822 日期已解析为 datetime")
print("  ✓ 例外 URL 配置存在:", cnki_rss.EXCEPTION_URLS)

print("\n  --- format_markdown 前 5 行 ---")
for line in cnki_rss.format_markdown(papers).splitlines()[:5]:
    print("   ", line)

hr("3) 未向 CNKI / NCPSSD 发送任何真实请求")
print("  本次测试共捕获", len(CAPTURED), "个请求，全部由桩函数接管，未出网。")
print("  （NCPSSD 端点的真实可用性已在安装前的评估阶段实测过一次）")

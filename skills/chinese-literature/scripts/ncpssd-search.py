#!/usr/bin/env python3
"""
国家哲学社会科学文献中心（NCPSSD）搜索脚本

用法：
  python3 ncpssd-search.py 关键词                    搜索并返回结构化结果
  python3 ncpssd-search.py 关键词 --pages 3          获取前 3 页
  python3 ncpssd-search.py 关键词 --output md        Markdown 格式输出
  python3 ncpssd-search.py 关键词 --page-size 20     每页 20 条

示例：
  python3 ncpssd-search.py 数字经济
  python3 ncpssd-search.py 企业数字化转型 --output md --pages 2
"""

import sys, json, re, urllib.request, urllib.parse
from datetime import datetime

API_URL = "https://www.ncpssd.cn/searchHandler/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.ncpssd.cn/",
}
DEFAULT_SORT = "synUpdateType|DESC,date|DESC,ik_subject|DESC,id|DESC"


def build_search_query(keyword: str, field: str = "all") -> str:
    """
    构建 NCPSSD 搜索查询字符串。
    field: all - 所有字段, title - 题名, keyword - 关键词, creator - 作者
    """
    field_map = {
        "all": ("IKTE", "IKPYTE", "IKST", "IKET", "IKSE"),
        "title": ("IKTE",),
        "keyword": ("IKST",),
        "creator": ("IKCR", "IKCE"),
        "abstract": ("IKET",),
        "subject": ("IKSE",),
    }
    tags = field_map.get(field, field_map["all"])
    conditions = [f'{tag}="{keyword}"' for tag in tags]
    return "(" + " OR ".join(conditions) + ")"


def search(
    keyword: str,
    field: str = "all",
    page: int = 1,
    page_size: int = 10,
    sort: str = DEFAULT_SORT,
    ajax_keys: str = "",
) -> dict:
    """执行搜索，返回原始 API 响应"""
    query = build_search_query(keyword, field)
    data = {
        "search": query,
        "pageNum": str(page),
        "pageSize": str(page_size),
        "sort": sort,
        "sType": "0",
        "ajaxKeys": ajax_keys,
        "customShowCondition": keyword,
    }
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"result": False, "message": str(e)}


def clean_title(title: str) -> str:
    """去除搜索结果中的高亮标记"""
    return re.sub(r"<[^>]+>", "", title or "")


def format_results(api_data: dict) -> list[dict]:
    """将 API 响应转化为结构化结果列表"""
    rows = api_data.get("data", {}).get("rows", [])
    results = []
    for i, row in enumerate(rows, 1):
        results.append({
            "n": i,
            "title": clean_title(row.get("title", "")),
            "authors": (row.get("creator_first") or row.get("creator") or "").strip(),
            "journal": (row.get("cbw_name") or "").strip(),
            "date": (row.get("date") or "")[:10],
            "year": row.get("years", ""),
            "volume": (row.get("volumn") or "").strip(),
            "issue": (row.get("num") or "").strip(),
            "pages": (row.get("pagecount") or "").strip(),
            "abstract": (row.get("remark") or "").strip(),
            "keywords": (row.get("subject") or "").strip(),
            "doi": (row.get("doi") or "").strip(),
            "fund": (row.get("imburse") or "").strip(),
            "issn": (row.get("issn") or "").strip(),
            "institutions": (row.get("institutions") or "").strip(),
            "pdf_url": row.get("pdfurl", ""),
            "html_url": row.get("HtmlUrl", ""),
            "access_url": row.get("encryptedUrl", ""),
        })
    return results


def format_text(results: list[dict], total: int, keyword: str) -> str:
    """文本格式输出"""
    lines = [
        f"NCPSSD 搜索结果：{keyword}（共 {total} 条）",
        "=" * 60,
        "",
    ]
    for r in results:
        lines.append(f"{r['n']}. {r['title']}")
        if r["authors"]:
            lines.append(f"   作者：{r['authors']}")
        if r["journal"]:
            parts = [r["journal"]]
            if r["year"]:
                parts.append(r["year"])
            if r["volume"]:
                parts.append(f"第{r['volume']}卷")
            if r["issue"]:
                parts.append(f"第{r['issue']}期")
            lines.append(f"   来源：{'、'.join(parts)}")
        if r["abstract"]:
            ab = r["abstract"][:200]
            lines.append(f"   摘要：{ab}{'…' if len(r['abstract']) > 200 else ''}")
        if r["keywords"]:
            lines.append(f"   关键词：{r['keywords']}")
        if r["doi"]:
            lines.append(f"   DOI: {r['doi']}")
        if r["pdf_url"]:
            lines.append(f"   全文：https://www.ncpssd.cn{r['pdf_url']}")
        lines.append("")
    return "\n".join(lines)


def format_markdown(results: list[dict], total: int, keyword: str) -> str:
    """Markdown 格式输出"""
    lines = [f"# NCPSSD 搜索结果：{keyword}", "", f"> 共 {total} 条结果", ""]
    for r in results:
        lines.append(f"### {r['n']}. {r['title']}")
        if r["authors"]:
            lines.append(f"**作者：**{r['authors']}")
        if r["journal"]:
            parts = [f"*{r['journal']}*"]
            if r["year"]:
                parts.append(r["year"])
            if r["volume"]:
                parts.append(f"第{r['volume']}卷")
            if r["issue"]:
                parts.append(f"第{r['issue']}期")
            lines.append(f"**来源：**{'、'.join(parts)}")
        if r["abstract"]:
            lines.append(f"\n{r['abstract']}")
        if r["keywords"]:
            lines.append(f"\n**关键词：**{r['keywords']}")
        if r["doi"]:
            lines.append(f"\nDOI: `{r['doi']}`")
        if r["pdf_url"]:
            lines.append(f"\n[📄 下载全文](https://www.ncpssd.cn{r['pdf_url']})")
        lines.append("\n---\n")
    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="NCPSSD 文献搜索")
    parser.add_argument("keyword", nargs="?", help="搜索关键词")
    parser.add_argument("--field", choices=["all", "title", "keyword", "creator", "abstract", "subject"],
                        default="all", help="搜索字段（默认 all）")
    parser.add_argument("--page", type=int, default=1, help="起始页码（默认 1）")
    parser.add_argument("--pages", type=int, default=1, help="获取总页数（默认 1）")
    parser.add_argument("--page-size", type=int, default=10, help="每页条数（默认 10）")
    parser.add_argument("--output", choices=["text", "md", "json"], default="text",
                        help="输出格式（默认 text）")
    parser.add_argument("--sort", choices=["default", "time"], default="time",
                        help="排序方式（默认 time）")

    args = parser.parse_args()

    if not args.keyword:
        parser.print_help()
        return

    sort = DEFAULT_SORT if args.sort == "time" else "synUpdateType|DESC,id|ASC"
    all_results = []
    total = 0

    for p in range(args.page, args.page + args.pages):
        resp = search(args.keyword, args.field, p, args.page_size, sort)
        if not resp.get("result"):
            print(f"⚠️  搜索失败: {resp.get('message', '未知错误')}", file=sys.stderr)
            sys.exit(1)

        data = resp.get("data", {})
        total = data.get("total", 0)
        results = format_results(resp)
        all_results.extend(results)

        if len(all_results) >= total:
            break

    if args.output == "json":
        output = {
            "keyword": args.keyword,
            "total": total,
            "results": all_results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif args.output == "md":
        print(format_markdown(all_results, total, args.keyword))
    else:
        print(format_text(all_results, total, args.keyword))


if __name__ == "__main__":
    main()

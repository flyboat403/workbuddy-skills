#!/usr/bin/env python3
"""
CNKI RSS 采集脚本

用法：
  python3 cnki-rss.py [期刊代码1] [期刊代码2] ...    采集指定期刊
  python3 cnki-rss.py --all                          采集配置中所有期刊
  python3 cnki-rss.py --init                         首次配置（交互式）
  python3 cnki-rss.py --list                         列出可用期刊代码
  python3 cnki-rss.py --config                       查看当前配置

示例：
  python3 cnki-rss.py JJYJ GLSJ
  python3 cnki-rss.py --all --days 7 --output md
"""

import sys, os, re, json
import urllib.request, http.cookiejar
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── 预设期刊（当没有 journals.json 配置文件时作为保底） ─────
DEFAULT_JOURNALS = {
    "JJYJ": "经济研究",
    "GLSJ": "管理世界",
    "KJYJ": "会计研究",
    "JRYJ": "金融研究",
    "GGYY": "中国工业经济",
    "SJJJ": "世界经济",
    "JJXU": "经济学(季刊)",
    "JCYJ": "管理科学学报",
    "LKGP": "南开管理评论",
    "GGGL": "公共管理学报",
    "ZXGL": "中国行政管理",
    "JJGL": "经济管理",
}

# ZSHK 使用例外 URL
EXCEPTION_URLS = {
    "ZSHK": "https://rss.cnki.net/knavi/rss/ZSHK?pcode=CJFD,CCJD"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# ── 学科分组（用于 --init 交互式配置） ─────────────────────
GROUPS = {
    "经济学": ["JJYJ", "SJJJ", "JJXU", "GGYY", "JCYJ"],
    "管理学": ["GLSJ", "LKGP", "GGGL", "ZXGL"],
    "会计与金融": ["KJYJ", "JRYJ"],
    "综合社科": ["ZSHK", "JJGL"],
}


# ── 配置管理 ──────────────────────────────────────────────

def find_config() -> Path | None:
    """查找 journals.json，优先脚本同目录"""
    script_dir = Path(__file__).parent.resolve()
    for d in [script_dir, Path.cwd()]:
        p = d / "journals.json"
        if p.exists():
            return p
    return None


def load_journals() -> dict:
    """加载期刊配置，找不到配置时返回预设"""
    config_path = find_config()
    if config_path is None:
        return DEFAULT_JOURNALS

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        raw = data.get("journals", data)
        # 过滤掉以 // 开头的注释键
        return {k: v for k, v in raw.items() if not k.startswith("//")}
    except (json.JSONDecodeError, KeyError):
        print(f"⚠️  journals.json 格式错误，使用默认配置", file=sys.stderr)
        return DEFAULT_JOURNALS


def load_exception_urls() -> dict:
    """加载例外 RSS URL"""
    config_path = find_config()
    if config_path is None:
        return EXCEPTION_URLS

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return data.get("exception_urls", EXCEPTION_URLS)
    except json.JSONDecodeError:
        return EXCEPTION_URLS


def show_config():
    """显示当前配置"""
    config_path = find_config()
    if config_path:
        print(f"配置文件：{config_path}")
        print(json.dumps(json.loads(config_path.read_text(encoding="utf-8")),
                         ensure_ascii=False, indent=2))
    else:
        print("未找到 journals.json 配置文件，当前使用内置默认期刊：")
        for code, name in sorted(DEFAULT_JOURNALS.items(), key=lambda x: x[1]):
            print(f"  {code}  → {name}")
        print()
        print("运行 python3 cnki-rss.py --init 创建配置文件。")


def init_config():
    """首次配置向导"""
    target = Path.cwd() / "journals.json"
    if target.exists():
        print(f"⚠️  {target} 已存在。如需重新配置，请先删除该文件。")
        return

    print("=" * 60)
    print("  CNKI RSS 采集工具 — 首次配置")
    print("=" * 60)
    print()
    print("本工具支持以下学科分组（选择后自动填入对应期刊）：")
    print()

    group_names = sorted(GROUPS.keys())
    for i, g in enumerate(group_names, 1):
        codes = GROUPS[g]
        names = [f"{c}({DEFAULT_JOURNALS[c]})" for c in codes if c in DEFAULT_JOURNALS]
        print(f"  [{i}] {g:　<8} → {'、'.join(names)}")
    print(f"  [{len(group_names)+1}] 自定义（手动输入期刊代码）")
    print()

    selected_codes = {}
    try:
        choice = input("请选择学科分组（输入编号，多个用逗号分隔，如 1,3）: ").strip()
        indices = [int(x.strip()) for x in choice.split(",") if x.strip()]
        for idx in indices:
            if 1 <= idx <= len(group_names):
                g = group_names[idx - 1]
                for code in GROUPS[g]:
                    if code in DEFAULT_JOURNALS:
                        selected_codes[code] = DEFAULT_JOURNALS[code]
            elif idx == len(group_names) + 1:
                custom = input("输入自定义期刊代码（用逗号分隔，如 JJYJ,GLSJ）: ").strip()
                for c in re.split(r"[,，\s]+", custom):
                    c = c.strip().upper()
                    if c:
                        selected_codes[c] = DEFAULT_JOURNALS.get(c, c)
    except (ValueError, IndexError):
        print("输入无效，将使用默认配置。")
        selected_codes = dict(DEFAULT_JOURNALS)

    if not selected_codes:
        selected_codes = dict(DEFAULT_JOURNALS)

    # 写入配置
    config = {
        "// 说明": "本文件是 CNKI RSS 采集工具的期刊配置文件。",
        "// 如何查找更多 CNKI 期刊代码": "打开 https://navi.cnki.net/knavi/ → 搜索期刊名 → URL 末尾的 4 位字母代码。",
        "journals": selected_codes,
        "exception_urls": EXCEPTION_URLS,
    }

    target.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"✅ 配置文件已写入：{target}")
    print(f"   共 {len(selected_codes)} 个期刊。")
    print()
    print("如需修改，直接编辑 journals.json 文件，或重新运行 python3 cnki-rss.py --init。")
    print("运行 python3 cnki-rss.py --all --output md 开始采集。")


def list_journals(journals: dict):
    """列出配置中可用的期刊"""
    print("可用期刊代码：")
    for code, name in sorted(journals.items(), key=lambda x: x[1]):
        print(f"  {code}  → {name}")
    print()
    print("学科分组参考：")
    for g, codes in sorted(GROUPS.items()):
        names = [f"{c}" for c in codes if c in journals]
        if names:
            print(f"  {g}: {'、'.join(names)}")


# ── RSS 采集核心 ──────────────────────────────────────────

def fetch_rss(code: str, journals: dict, exception_urls: dict) -> list[dict]:
    """获取指定期刊代码的 RSS 论文列表"""
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar)
    )

    # Step 1：访问期刊详情页，获取 Cookie
    journal_url = (
        f"https://navi.cnki.net/knavi/journals/{code}/detail?uniplatform=NZKPT"
    )
    try:
        opener.open(
            urllib.request.Request(journal_url, headers=HEADERS), timeout=15
        )
    except Exception as e:
        print(f"⚠️  [{code}] Cookie 认证失败: {e}", file=sys.stderr)
        return []

    # Step 2：抓取 RSS
    rss_url = exception_urls.get(
        code, f"https://navi.cnki.net/knavi/rss/{code}"
    )
    try:
        resp = opener.open(
            urllib.request.Request(rss_url, headers=HEADERS), timeout=15
        )
        body = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"⚠️  [{code}] RSS 获取失败: {e}", file=sys.stderr)
        return []

    if not body.strip():
        print(f"⚠️  [{code}] RSS 为空（可能 Cookie 过期）", file=sys.stderr)
        return []

    # 解析 RSS
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        print(f"⚠️  [{code}] XML 解析失败: {e}", file=sys.stderr)
        return []

    papers = []
    for item in root.iter("item"):
        pub_date_str = item.findtext("pubDate", "")
        pub_date = None
        if pub_date_str:
            try:
                pub_date = datetime.strptime(
                    pub_date_str, "%a, %d %b %Y %H:%M:%S %Z"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        papers.append({
            "code": code,
            "journal": journals.get(code, code),
            "title": item.findtext("title", "").strip(),
            "link": item.findtext("link", "").strip(),
            "authors": item.findtext("author", "").strip(),
            "summary": item.findtext("description", "").strip(),
            "pub_date": pub_date_str,
            "pub_date_dt": pub_date,
        })

    return papers


def filter_by_days(papers: list[dict], days: int) -> list[dict]:
    """按天数过滤"""
    if days <= 0:
        return papers
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return [
        p for p in papers
        if p["pub_date_dt"] and p["pub_date_dt"] >= cutoff
    ]


def format_markdown(papers: list[dict]) -> str:
    """输出 Markdown 格式"""
    lines = [f"# CNKI RSS 采集结果 ({datetime.now().strftime('%Y-%m-%d %H:%M')})", ""]

    # 按期刊分组
    by_journal = {}
    for p in papers:
        by_journal.setdefault(p["journal"], []).append(p)

    for jname, jpapers in by_journal.items():
        lines.append(f"## {jname}（{len(jpapers)} 篇）")
        lines.append("")
        for p in jpapers:
            lines.append(f"- **{p['title']}**")
            if p["authors"]:
                lines.append(f"  作者：{p['authors']}")
            if p["pub_date"]:
                lines.append(f"  日期：{p['pub_date']}")
            lines.append("")

    return "\n".join(lines)


def format_json(papers: list[dict]) -> str:
    """输出 JSON 格式"""
    clean = []
    for p in papers:
        clean.append({
            "journal": p["journal"],
            "title": p["title"],
            "link": p["link"],
            "authors": p["authors"],
            "summary": p["summary"],
            "pub_date": p["pub_date"],
        })
    return json.dumps(clean, ensure_ascii=False, indent=2)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="CNKI RSS 采集工具")
    parser.add_argument("codes", nargs="*", help="期刊代码，如 JJYJ GLSJ")
    parser.add_argument("--all", action="store_true", help="采集配置中所有期刊")
    parser.add_argument("--days", type=int, default=0, help="只返回最近 N 天的论文")
    parser.add_argument("--output", choices=["md", "json", "text"], default="text",
                        help="输出格式（默认 text）")
    parser.add_argument("--list", action="store_true", help="列出可用的期刊代码")
    parser.add_argument("--init", action="store_true", help="首次配置向导")
    parser.add_argument("--config", action="store_true", help="查看当前配置")

    args = parser.parse_args()

    # 加载配置
    journals = load_journals()
    exception_urls = load_exception_urls()

    # ── 配置命令 ──
    if args.init:
        init_config()
        return

    if args.config:
        show_config()
        return

    if args.list:
        list_journals(journals)
        return

    # ── 首次运行提醒 ──
    if find_config() is None and (args.all or args.codes):
        print("ℹ️  未找到 journals.json 配置文件。如需自定义期刊列表，请运行：")
        print("   python3 cnki-rss.py --init")
        print("   或复制 journals.template.json 为 journals.json 后编辑。")
        print()

    # 确定采集目标
    if args.all:
        codes = list(journals.keys())
    elif args.codes:
        codes = args.codes
    else:
        parser.print_help()
        return

    # 采集
    all_papers = []
    for code in codes:
        papers = fetch_rss(code, journals, exception_urls)
        all_papers.extend(papers)

    # 过滤
    if args.days > 0:
        all_papers = filter_by_days(all_papers, args.days)

    # 按日期排序
    all_papers.sort(key=lambda p: p["pub_date_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    # 输出
    if args.output == "md":
        print(format_markdown(all_papers))
    elif args.output == "json":
        print(format_json(all_papers))
    else:
        print(f"共 {len(all_papers)} 篇论文")
        for p in all_papers:
            print(f"  [{p['journal']}] {p['title']}")
            if p["authors"]:
                print(f"    作者：{p['authors']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从官网页面提取内联 SVG logo —— 品牌图标的权威兜底来源。

导航栏 / 页头的 logo 常以 <svg> 内联形式写在官网首页里，这是唯一权威的矢量来源
（比第三方矢量站的粉丝重绘可靠得多）。本脚本：

  1. 抓取官网页面（或读本地 HTML），扫描全部内联 <svg>；
  2. 按「logo 相似度」打分排序（上下文含 logo、尺寸合理、path 数量）；
  3. 自动选最佳候选，清洗后派生 彩色 / 单色黑 / 纯白 三版 + 512px 透明 PNG；
  4. 顺带抓取 apple-touch-icon（通常最大的官方位图）；
  5. 生成预览拼图（含深底白色版效果）与 manifest 片段。

用法
  python extract_inline_svg.py --url https://www.wps.com/ --out ./WPS图标 --name wps
  python extract_inline_svg.py --html saved.html --out ./out --name wps --pick 2
  python extract_inline_svg.py --url ... --list-only        # 只列出候选，不产出

自动选中的候选若不对，用 --list-only 看清单，再 --pick 序号 重跑。

依赖：resvg_py、pillow。只用标准库解析 HTML，不引入 BeautifulSoup。
"""

import argparse
import io
import json
import os
import re
import urllib.request

from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

# 自闭合单例标签：官网 SVG 常有非自闭合写法（<path ...> 缺 />），拼接子集前必须补齐
SINGLETONS = ("path", "rect", "circle", "ellipse", "line", "polygon", "polyline", "use")


# ---------------------------------------------------------------- 抓取

def fetch_html(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", errors="ignore")


def fetch_bytes(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


# ---------------------------------------------------------------- 解析

def iter_svg_blocks(html):
    """按 <svg ...> ... </svg> 配对扫描（容忍一层嵌套）。"""
    opens = [(m.start(), m.end()) for m in re.finditer(r"<svg\b", html)]
    closes = [m.end() for m in re.finditer(r"</svg>", html)]
    for start, tag_end in opens:
        depth = 1
        pos = tag_end
        for c in closes:
            if c <= pos:
                continue
            depth -= 1
            pos = c
            if depth == 0:
                yield start, pos, html[start:pos]
                break
        # 嵌套超过一层或未闭合的丢弃（logo 场景罕见）


def svg_meta(block, context):
    def attr(name):
        m = re.search(name + r'="([^"]+)"', block)
        return m.group(1) if m else ""

    vb = attr("viewBox")
    dims = [float(x) for x in vb.replace(",", " ").split()] if vb else []
    w, h = (dims[2], dims[3]) if len(dims) == 4 else (0.0, 0.0)
    if not w or not h:  # 退回 width/height 属性
        try:
            w, h = float(attr("width").rstrip("px") or 0), float(attr("height").rstrip("px") or 0)
        except ValueError:
            w, h = 0.0, 0.0
    paths = len(re.findall(r"<path\b", block))
    fills = sorted({f for f in re.findall(r'fill="([^"]+)"', block) if f.lower() != "none"})
    ctx = context.lower()
    score = 0
    if "logo" in ctx:
        score += 3
    if re.search(r'class="[^"]*(logo|brand)', block, re.I):
        score += 2
    if paths >= 2:
        score += 1
    if 20 <= max(w, h) <= 800:
        score += 1
    if max(w, h) and max(w, h) < 20:
        score -= 3
    return {
        "viewBox": vb or f"{attr('width')} {attr('height')}",
        "w": w, "h": h, "paths": paths, "fills": fills,
        "score": score, "has_gradient": "Gradient" in block,
    }


def scan(html):
    out = []
    for start, end, block in iter_svg_blocks(html):
        if "<path" not in block and "<rect" not in block and "<circle" not in block:
            continue
        meta = svg_meta(block, html[max(0, start - 300):start])
        meta["index"] = len(out)
        meta["block"] = block
        out.append(meta)
    return out


# ---------------------------------------------------------------- 清洗与派生

def clean(block):
    b = re.sub(r'\s*data-v-[0-9a-f]+', "", block)          # Vue scoped
    b = re.sub(r'\s*(?:ng-|k-)[a-z-]+="[^"]*"', "", b)      # 其他框架属性
    return b


def fix_unclosed(svg):
    """单例标签开/闭数量不齐时，强制自闭合（官网原始 SVG 常见坑）。"""
    for tag in SINGLETONS:
        n_open = len(re.findall(rf"<{tag}\b(?![^>]*/>)", svg))
        n_close = len(re.findall(rf"</{tag}>", svg))
        if n_open > n_close:
            svg = re.sub(rf"<({tag}\b[^>]*?)(?<!/)>", r"<\1/>", svg)
    return svg


def recolor(svg, target):
    """把所有填充/描边统一换成 target（none 除外）。渐变 logo 不适用，见参考文档。"""
    svg = re.sub(r'fill="(?!none)[^"]*"', f'fill="{target}"', svg)
    svg = re.sub(r'stroke="(?!none)[^"]*"', f'stroke="{target}"', svg)
    return svg


def to_png(svg, long_side=512):
    import resvg_py

    m = re.search(r'viewBox="[^"]*\s+([\d.]+)\s+([\d.]+)"', svg)
    w, h = (float(m.group(1)), float(m.group(2))) if m else (1.0, 1.0)
    if w >= h:
        width, height = long_side, max(1, round(long_side * h / w))
    else:
        width, height = max(1, round(long_side * w / h)), long_side
    raw = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=width, height=height, background=None))
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), (width, height)


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description="官网内联 SVG logo 提取")
    ap.add_argument("--url", help="官网页面地址")
    ap.add_argument("--html", help="本地 HTML 文件（离线模式）")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--name", required=True, help="slug，如 wps")
    ap.add_argument("--pick", type=int, default=None, help="候选序号（缺省自动选最高分）")
    ap.add_argument("--list-only", action="store_true", help="只列出候选")
    ap.add_argument("--no-appicon", action="store_true", help="不抓 apple-touch-icon")
    args = ap.parse_args()

    html = open(args.html, encoding="utf-8", errors="ignore").read() if args.html else fetch_html(args.url)
    cands = scan(html)
    if not cands:
        print("未找到内联 SVG —— 该官网可能用位图/字体渲染 logo，改走 apple-touch-icon / favicon 兜底。")
        return
    cands.sort(key=lambda c: -c["score"])

    print(f"{'序号':<4}{'分数':<5}{'viewBox':<18}{'path':<6}填充色")
    for c in cands:
        vb = f"{c['w']:.0f}x{c['h']:.0f}" if c["w"] else "?"
        print(f"{c['index']:<4}{c['score']:<5}{vb:<18}{c['paths']:<6}{', '.join(c['fills'][:4])}")

    if args.list_only:
        return

    pick = args.pick if args.pick is not None else cands[0]["index"]
    chosen = next(c for c in cands if c["index"] == pick)
    print(f"\n选中候选 {pick}（viewBox {chosen['viewBox']}）")

    os.makedirs(args.out, exist_ok=True)
    color = fix_unclosed(clean(chosen["block"]))
    mono = recolor(color, "#000000")
    white = recolor(color, "#FFFFFF")

    files = {}
    for suffix, svg in (("color", color), ("mono", mono), ("white", white)):
        name = f"{args.name}-{suffix}.svg"
        open(os.path.join(args.out, name), "w", encoding="utf-8").write(svg)
        png, size = to_png(svg)
        pname = f"{args.name}-{suffix}-512.png"
        open(os.path.join(args.out, pname), "wb").write(png)
        files[suffix] = {"svg": name, "png": pname, "png_size": size}
        print(f"  ✓ {name} + {pname} {size}")

    # apple-touch-icon：通常最大的官方位图
    appicon = None
    if not args.no_appicon and args.url:
        m = re.search(r'<link[^>]*rel="apple-touch-icon"[^>]*href="([^"]+)"', html) or \
            re.search(r'<link[^>]*href="([^"]+)"[^>]*rel="apple-touch-icon"', html)
        if m:
            href = m.group(1)
            icon_url = href if href.startswith("http") else urllib.parse.urljoin(args.url, href)
            try:
                data = fetch_bytes(icon_url)
                pname = f"{args.name}-appicon.png"
                open(os.path.join(args.out, pname), "wb").write(data)
                appicon = pname
                print(f"  ✓ {pname}（{len(data)//1024}KB）")
            except Exception as e:
                print(f"  apple-touch-icon 抓取失败：{e}")

    # 预览拼图：白底 彩色/单色 + 深底 白色
    imgs = {k: Image.open(os.path.join(args.out, v["png"])) for k, v in files.items()}
    W = 1200
    sheet = Image.new("RGB", (W, 520), "#FFFFFF")
    sheet.paste(imgs["color"].resize((560, int(imgs["color"].height * 560 / imgs["color"].width)), Image.LANCZOS),
                (40, 50), imgs["color"].resize((560, int(imgs["color"].height * 560 / imgs["color"].width)), Image.LANCZOS))
    sheet.paste(imgs["mono"].resize((560, int(imgs["mono"].height * 560 / imgs["mono"].width)), Image.LANCZOS),
                (40, 200), imgs["mono"].resize((560, int(imgs["mono"].height * 560 / imgs["mono"].width)), Image.LANCZOS))
    dark = Image.new("RGB", (W, 170), "#1F2329")
    sheet.paste(dark, (0, 350))
    wht = imgs["white"].resize((560, int(imgs["white"].height * 560 / imgs["white"].width)), Image.LANCZOS)
    sheet.paste(wht, (40, 385), wht)
    if appicon:
        a = Image.open(os.path.join(args.out, appicon)).convert("RGBA")
        a = a.resize((150, int(a.height * 150 / a.width)), Image.LANCZOS)
        sheet.paste(a, (660, 395), a)
    if imgs["color"].width / imgs["color"].height < 1.2:  # 方形/竖版标放到右侧
        sq = imgs["color"].resize((200, int(imgs["color"].height * 200 / imgs["color"].width)), Image.LANCZOS)
        sheet.paste(sq, (660, 60), sq)
    sheet.save(os.path.join(args.out, "preview.png"))
    print("  ✓ preview.png")

    manifest = {
        "slug": args.name,
        "source": args.url or args.html,
        "pick_index": pick,
        "candidates": [{k: c[k] for k in ("index", "viewBox", "paths", "fills", "score")} for c in cands],
        "files": {k: v["svg"] for k, v in files.items()} | {k: v["png"] for k, v in files.items()},
        "appicon": appicon,
        "note": "内联 SVG 提取自官网页面；商标权归品牌权利人，仅限教学/研究/演示等合理引用",
    }
    json.dump(manifest, open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("  ✓ manifest.json")


if __name__ == "__main__":
    import urllib.parse  # noqa: F401  (urljoin 在 main 内通过 urllib.parse 使用)
    main()

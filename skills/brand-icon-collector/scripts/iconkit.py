#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""iconkit — 品牌图标采集工具包：探测 / 抓取 / 自绘 / 版式。

子命令
  probe     探测一批 slug 在三个公开图标源里的可用性（先探测，不要盲抓）
  fetch     批量抓取并导出 512px SVG + PNG，写 manifest.json
  wordmark  为"无官方矢量源"的产品自绘文字标识
  sheet     按分类或厂商排成联系表 PNG
  matrix    排成「厂商 × 模态」矩阵 PNG

依赖：pip install resvg-py pillow fonttools

设计说明
  · 单色版统一为 512 画布、纯黑填充 —— 便于在 PPT 里一键改色；
  · 彩色版保留官方品牌色 —— 便于做封面、对比表；
  · 全部输出透明底 PNG，另附矢量 SVG，两条腿走路。
"""

import argparse
import io
import json
import os
import re
import sys
import time
import urllib.request

# LobeHub Icons 静态 SVG 包（MIT）。unpkg 在国内常被墙，走 npmmirror 镜像。
LOBEHUB = "https://registry.npmmirror.com/@lobehub/icons-static-svg/latest/files/icons"
# Simple Icons（CC0），返回带官方品牌色的 SVG。
SIMPLE = "https://cdn.simpleicons.org"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) iconkit/1.0"}

DEFAULT_LABELS = {"llm": "语言模型", "image": "生图模型", "video": "视频模型"}


# ---------------------------------------------------------------- 网络

def _get(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def lobehub(name):
    return _get(f"{LOBEHUB}/{name}.svg")


def simpleicons(name):
    return _get(f"{SIMPLE}/{name}")


def exists(url, timeout=15):
    req = urllib.request.Request(url, headers=UA, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


# ---------------------------------------------------------------- SVG 处理

def normalize(svg, force_black=False):
    """统一 512 画布；去掉 1em 尺寸与内联 style；单色版压成纯黑。"""
    svg = re.sub(r'(height|width)="1em"', r'\1="512"', svg)
    svg = re.sub(r'\s*style="flex:none;line-height:1"', "", svg)
    if force_black:
        # currentColor 与根节点 fill 都要处理，否则 Simple Icons 会保留品牌色
        svg = svg.replace("currentColor", "#000000")
        svg = re.sub(r'fill="#[0-9A-Fa-f]{3,8}"', 'fill="#000000"', svg, count=1)
    if 'width="512"' not in svg:
        svg = svg.replace("<svg ", '<svg width="512" height="512" ', 1)
    return svg


def to_png(svg, size=512):
    import resvg_py
    from PIL import Image

    raw = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=size, height=size, background=None))
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------- 字体

FONT_ALIASES = {
    "cjk": ["C:/Windows/Fonts/msyhbd.ttc", "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"],
    "latin": ["C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Helvetica.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "latin-black": ["C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/arialbd.ttf",
                    "/System/Library/Fonts/Helvetica.ttc"],
    "cjk-reg": ["C:/Windows/Fonts/msyh.ttc", "/System/Library/Fonts/PingFang.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"],
}


def pick_font(spec):
    """spec 可以是字体别名，也可以是绝对路径。返回 (path, ttc_index)。"""
    if os.path.isfile(spec):
        return (spec, 0)
    for p in FONT_ALIASES.get(spec, []):
        if os.path.isfile(p):
            return (p, 0)
    raise FileNotFoundError(f"找不到字体：{spec}（可传绝对路径）")


# ---------------------------------------------------------------- probe

def cmd_probe(args):
    slugs = [s.strip() for s in args.slugs.split(",") if s.strip()]
    print(f"{'slug':<26}{'lobehub':<10}{'+color':<10}{'simpleicons':<12}建议")
    for s in slugs:
        a = exists(f"{LOBEHUB}/{s}.svg")
        b = exists(f"{LOBEHUB}/{s}-color.svg")
        c = exists(f"{SIMPLE}/{s}")
        if a and b:
            hint = "LobeHub 双色"
        elif a:
            hint = "LobeHub 单色" + ("（品牌本身即黑色）" if not b else "")
        elif c:
            hint = "Simple Icons（含官方色）"
        else:
            hint = "无矢量源 → 考虑 wordmark 或官网 favicon"
        print(f"{s:<26}{'OK' if a else '-':<10}{'OK' if b else '-':<10}{'OK' if c else '-':<12}{hint}")
        time.sleep(args.delay)


# ---------------------------------------------------------------- fetch

def resolve_color(b, slug, mono_name):
    """返回彩色 SVG 文本；无彩色版返回 None。"""
    spec = b.get("color")
    if spec == "none":
        return None, None
    if spec:
        kind, _, name = spec.partition(":")
        if not name:
            kind, name = "lobehub", spec
        try:
            if kind == "simpleicons":
                return simpleicons(name), f"simpleicons:{name}"
            return lobehub(name), f"lobehub:{name}"
        except Exception:
            return None, None
    # 未指定则自动探测：LobeHub 彩色变体 → Simple Icons
    for name_, kind, fn in ((f"{mono_name}-color", "lobehub", lobehub), (slug, "simpleicons", simpleicons)):
        try:
            return fn(name_), f"{kind}:{name_}"
        except Exception:
            continue
    return None, None


def cmd_fetch(args):
    brands = json.load(open(args.brands, encoding="utf-8"))
    out = os.path.abspath(args.out)
    dirs = {
        "mono_svg": os.path.join(out, "svg", "mono"),
        "color_svg": os.path.join(out, "svg", "color"),
        "mono_png": os.path.join(out, "png", "mono-512"),
        "color_png": os.path.join(out, "png", "color-512"),
    }
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)

    manifest, failed = [], []
    for b in brands:
        slug = b["slug"]
        mono_name = b.get("mono") or slug

        mono_svg = None
        src = None
        try:
            mono_svg, src = lobehub(mono_name), f"lobehub:{mono_name}"
        except Exception:
            try:
                mono_svg, src = simpleicons(b.get("simple") or slug), f"simpleicons:{slug}"
            except Exception as e:
                print(f"  ✗ {slug}: 无单色源（{e}）")
                failed.append({"slug": slug, "reason": "no mono source"})
                continue

        mono_svg = normalize(mono_svg, force_black=True)
        open(os.path.join(dirs["mono_svg"], f"{slug}.svg"), "w", encoding="utf-8").write(mono_svg)
        open(os.path.join(dirs["mono_png"], f"{slug}.png"), "wb").write(to_png(mono_svg))

        rec = {
            "slug": slug,
            "zh": b.get("zh", slug),
            "en": b.get("en", slug),
            "vendor": b.get("vendor", ""),
            "cat": b.get("cat", ""),
            "modality": b.get("modality", b.get("cat", "")),
            "vgroup": b.get("vgroup", b.get("vendor", "")),
            "files": {
                "mono_svg": f"svg/mono/{slug}.svg",
                "mono_png": f"png/mono-512/{slug}.png",
            },
            "mono_src": src,
        }

        color_svg, csrc = resolve_color(b, slug, mono_name)
        if color_svg:
            color_svg = normalize(color_svg)
            open(os.path.join(dirs["color_svg"], f"{slug}.svg"), "w", encoding="utf-8").write(color_svg)
            open(os.path.join(dirs["color_png"], f"{slug}.png"), "wb").write(to_png(color_svg))
            rec["files"]["color_svg"] = f"svg/color/{slug}.svg"
            rec["files"]["color_png"] = f"png/color-512/{slug}.png"
            rec["color_src"] = csrc
        manifest.append(rec)
        print(f"  ✓ {slug:<20} {'彩色+单色' if color_svg else '仅单色'}")
        time.sleep(args.delay)

    mpath = os.path.join(out, "manifest.json")
    if os.path.exists(mpath) and not args.fresh:
        old = {r["slug"]: r for r in json.load(open(mpath, encoding="utf-8"))}
        for r in manifest:
            old[r["slug"]] = r
        order = [r["slug"] for r in brands]
        manifest = [old[s] for s in order if s in old] + [v for k, v in old.items() if k not in order]
    json.dump(manifest, open(mpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"\n完成：{len(manifest)} 项写入 {mpath}")
    if failed:
        print("失败：", ", ".join(f["slug"] for f in failed))
        print("→ 这些品牌改用 `wordmark` 子命令自绘，或取官网 favicon。")


# ---------------------------------------------------------------- wordmark

def text_to_path(text, font_spec):
    """把文本转成 SVG path 数据 + 字体单位包围盒 + upem。"""
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont

    path, idx = pick_font(font_spec)
    font = TTFont(path, fontNumber=idx)
    upem = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    glyphset = font.getGlyphSet()
    hmtx = font["hmtx"]

    pen, bpen, x = SVGPathPen(glyphset), BoundsPen(glyphset), 0
    for ch in text:
        gname = cmap.get(ord(ch))
        if gname is None:
            raise KeyError(f"字体 {path} 缺字：{ch}")
        g = glyphset[gname]
        t = (1, 0, 0, 1, x, 0)
        g.draw(TransformPen(pen, t))
        g.draw(TransformPen(bpen, t))
        x += hmtx[gname][0]
    if not bpen.bounds:
        raise ValueError("字形为空")
    return pen.getCommands(), bpen.bounds, upem


def wordmark_svg(text, font_spec, color, mono, tile=512, inset=26, radius=100,
                 max_w=0.72, max_h=0.30):
    d, (x0, y0, x1, y1), _ = text_to_path(text, font_spec)
    size = tile - inset * 2
    k = min(size * max_w / (x1 - x0), size * max_h / (y1 - y0))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    tx, ty = tile / 2 - k * cx, tile / 2 + k * cy
    bg = "#000000" if mono else color
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{tile}" height="{tile}" '
        f'viewBox="0 0 {tile} {tile}">'
        f'<rect x="{inset}" y="{inset}" width="{size}" height="{size}" rx="{radius}" fill="{bg}"/>'
        f'<g transform="translate({tx:.2f},{ty:.2f}) scale({k:.6f},{-k:.6f})">'
        f'<path d="{d}" fill="#FFFFFF"/></g></svg>'
    )


def cmd_wordmark(args):
    items = json.load(open(args.brands, encoding="utf-8"))
    out = os.path.abspath(args.out)
    dirs = {
        "mono_svg": os.path.join(out, "svg", "mono"),
        "color_svg": os.path.join(out, "svg", "color"),
        "mono_png": os.path.join(out, "png", "mono-512"),
        "color_png": os.path.join(out, "png", "color-512"),
    }
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)

    mpath = os.path.join(out, "manifest.json")
    manifest = json.load(open(mpath, encoding="utf-8")) if os.path.exists(mpath) else []

    for it in items:
        slug = it["slug"]
        text = it.get("text") or it.get("en") or slug
        font = it.get("font", "latin")
        color = it.get("color", "#333333")
        mono_svg = wordmark_svg(text, font, color, True)
        color_svg = wordmark_svg(text, font, color, False)
        open(os.path.join(dirs["mono_svg"], f"{slug}.svg"), "w", encoding="utf-8").write(mono_svg)
        open(os.path.join(dirs["color_svg"], f"{slug}.svg"), "w", encoding="utf-8").write(color_svg)
        open(os.path.join(dirs["mono_png"], f"{slug}.png"), "wb").write(to_png(mono_svg))
        open(os.path.join(dirs["color_png"], f"{slug}.png"), "wb").write(to_png(color_svg))

        rec = {
            "slug": slug,
            "zh": it.get("zh", text),
            "en": it.get("en", text),
            "vendor": it.get("vendor", ""),
            "cat": it.get("cat", ""),
            "modality": it.get("modality", it.get("cat", "")),
            "vgroup": it.get("vgroup", it.get("vendor", "")),
            "wordmark": True,
            "files": {
                "mono_svg": f"svg/mono/{slug}.svg",
                "mono_png": f"png/mono-512/{slug}.png",
                "color_svg": f"svg/color/{slug}.svg",
                "color_png": f"png/color-512/{slug}.png",
            },
            "color_src": "self-drawn wordmark",
        }
        manifest = [r for r in manifest if r["slug"] != slug]
        # 插到同厂商条目后面，保持分组顺序
        idx = None
        for i, r in enumerate(manifest):
            if it.get("vgroup") and r.get("vgroup") == it["vgroup"]:
                idx = i + 1
        if idx is None:
            same = [i for i, r in enumerate(manifest) if r.get("cat") == it.get("cat")]
            idx = same[-1] + 1 if same else len(manifest)
        manifest.insert(idx, rec)
        print(f"  ✓ {slug:<20} 自绘文字标识「{text}」")

    json.dump(manifest, open(mpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nmanifest 更新为 {len(manifest)} 项")


# ---------------------------------------------------------------- sheet

def load_pil_fonts():
    from PIL import ImageFont

    def first(alias, size):
        for p in FONT_ALIASES.get(alias, []):
            if os.path.isfile(p):
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    return {
        "title": first("cjk", 26),
        "name": first("cjk", 17),
        "sub": first("cjk-reg", 12),
        "note": first("cjk-reg", 12),
        "sec": first("cjk", 16),
        "meta": first("cjk-reg", 11),
    }


def cmd_sheet(args):
    from PIL import Image, ImageDraw

    data = json.load(open(args.manifest, encoding="utf-8"))
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    F = load_pil_fonts()

    labels = dict(DEFAULT_LABELS)
    for kv in args.label or []:
        k, _, v = kv.partition("=")
        labels[k] = v

    if args.group_by == "cat":
        keys = []
        for b in data:
            if b.get("cat") and b["cat"] not in keys:
                keys.append(b["cat"])
        groups = [(k, labels.get(k, k), [b for b in data if b.get("cat") == k]) for k in keys]
    elif args.group_by == "vendor":
        keys = []
        for b in data:
            v = b.get("vgroup") or b.get("vendor") or "其他"
            if v not in keys:
                keys.append(v)
        groups = [(k, k, [b for b in data if (b.get("vgroup") or b.get("vendor") or "其他") == k]) for k in keys]
    else:
        groups = [("all", args.title or "品牌图标", data)]

    PAD, TOP = 34, 104
    for gi, (key, title, items) in enumerate(groups):
        if not items:
            continue
        cols = args.cols
        w = PAD * 2 + cols * args.cell_w
        rows = (len(items) + cols - 1) // cols
        h = TOP + rows * args.cell_h + 62
        img = Image.new("RGB", (w, h), "#FFFFFF")
        d = ImageDraw.Draw(img)

        d.text((PAD, 34), f"{title}（{len(items)}）", font=F["title"], fill="#1F2329")
        subtitle = " · ".join((b["en"].split(" / ")[0] or b["slug"]) for b in items)
        d.text((PAD, 70), subtitle, font=F["note"], fill="#7A828E")

        for i, b in enumerate(items):
            r, c = divmod(i, cols)
            x0 = PAD + c * args.cell_w
            y0 = TOP + r * args.cell_h
            src = b["files"].get("color_png") or b["files"]["mono_png"]
            ic = Image.open(os.path.join(out, src)).resize((args.icon, args.icon), Image.LANCZOS)
            img.paste(ic, (int(x0 + (args.cell_w - args.icon) // 2), y0 + 30), ic)

            name = b.get("zh") or b.get("en") or b["slug"]
            tw = d.textlength(name, font=F["name"])
            d.text((x0 + (args.cell_w - tw) / 2, y0 + 158), name, font=F["name"], fill="#1F2329")
            sub = (b.get("en") or "").split(" / ")[0]
            tw = d.textlength(sub, font=F["sub"])
            d.text((x0 + (args.cell_w - tw) / 2, y0 + 184), sub, font=F["sub"], fill="#8A919C")

        d.text((PAD, h - 42), args.footer, font=F["note"], fill="#9AA1AB")

        name_out = f"sheet-{gi + 1:02d}-{key}.png"
        img.save(os.path.join(out, name_out), optimize=True)
        print(f"  ✓ {name_out}  {img.size}  {len(items)} 项")


# ---------------------------------------------------------------- matrix

def cmd_matrix(args):
    from PIL import Image, ImageDraw

    data = [b for b in json.load(open(args.manifest, encoding="utf-8"))
            if not args.skip or b.get("cat") not in args.skip.split(",")]
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    F = load_pil_fonts()

    mods = [(k, labels_v, fg, bg) for (k, labels_v, fg, bg) in [
        ("llm", "语言", "#2F5BD7", "#E8EEFC"),
        ("image", "生图", "#6B3FD4", "#EFE9FD"),
        ("video", "视频", "#C26410", "#FDEEE0"),
    ]]
    for kv in args.label or []:
        k, _, v = kv.partition("=")
        mods = [(mk, v if mk == k else mv, fg, bg) for mk, mv, fg, bg in mods]

    groups = {}
    for b in data:
        groups.setdefault(b.get("vgroup") or b.get("vendor") or "其他", []).append(b)
    multi = sorted([(k, v) for k, v in groups.items() if len(v) >= 2], key=lambda kv: (-len(kv[1]), kv[0]))
    single = sorted([(k, v) for k, v in groups.items() if len(v) == 1], key=lambda kv: kv[0])

    # 列宽按最宽的单元格内容动态计算，避免多条目溢出列边界被下一列图块盖住
    probe_img = Image.new("RGB", (8, 8))
    probe_d = ImageDraw.Draw(probe_img)
    need = 0
    for _, items in multi:
        for mk, _, _, _ in mods:
            wsum = 16
            for b in [x for x in items if x.get("cat") == mk]:
                nm = b.get("zh") or b.get("en") or b.get("slug", "")
                wsum += int(58 + probe_d.textlength(nm, font=F["name"])) + 20
            need = max(need, wsum)
    CW = max(324, need + 8)

    PAD, VW, RH, HDR = 34, 210, 118, 46
    W = PAD * 2 + VW + CW * len(mods)
    TOP = 116
    single_top = TOP + HDR + RH * len(multi) + 46
    s_rows = (len(single) + 5) // 6
    H = single_top + 34 + s_rows * 84 + 44

    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)

    d.text((PAD, 34), args.title, font=F["title"], fill="#1F2329")
    d.text((PAD, 74), f"{len(groups)} 家厂商 · {len(data)} 个模型 · 其中 {len(multi)} 家覆盖两个及以上模态",
           font=F["sub"], fill="#7A828E")

    d.rectangle([PAD, TOP, W - PAD, TOP + HDR], fill="#F7F8FA")
    d.text((PAD + 16, TOP + 15), "厂商", font=F["sec"], fill="#5B6472")
    for i, (_, lab, fg, _) in enumerate(mods):
        d.text((PAD + VW + CW * i + 16, TOP + 15), lab, font=F["sec"], fill=fg)
    d.line([PAD, TOP + HDR, W - PAD, TOP + HDR], fill="#E6E8EB", width=1)

    for r, (vname, items) in enumerate(multi):
        y0 = TOP + HDR + r * RH
        if r % 2 == 1:
            d.rectangle([PAD, y0, W - PAD, y0 + RH], fill="#FCFCFD")
        d.text((PAD + 16, y0 + 44), vname, font=F["name"], fill="#1F2329")
        d.text((PAD + 16, y0 + 70), f"{len(items)} 个模型", font=F["meta"], fill="#9AA1AB")
        for i, (mk, _, _, _) in enumerate(mods):
            x = PAD + VW + CW * i
            sub = [b for b in items if b.get("cat") == mk]
            if not sub:
                d.text((x + 16, y0 + 50), "—", font=F["sec"], fill="#CDD2DA")
                continue
            cx = x + 16
            for b in sub:
                src = b["files"].get("color_png") or b["files"]["mono_png"]
                ic = Image.open(os.path.join(out, src)).resize((48, 48), Image.LANCZOS)
                img.paste(ic, (int(cx), y0 + 34), ic)
                nm = b.get("zh") or b.get("en")
                d.text((int(cx) + 58, y0 + 44), nm, font=F["name"], fill="#1F2329")
                d.text((int(cx) + 58, y0 + 64), (b.get("en") or "").split(" / ")[0],
                       font=F["meta"], fill="#9AA1AB")
                cx += 58 + d.textlength(nm, font=F["name"]) + 20
        if r:
            d.line([PAD, y0, W - PAD, y0], fill="#EFF1F4", width=1)

    d.line([PAD + 4, single_top - 22, PAD + 4, single_top + 4], fill="#2F5BD7", width=4)
    d.text((PAD + 16, single_top - 14), "仅覆盖单一模态的厂商", font=F["sec"], fill="#1F2329")
    for k, (vname, items) in enumerate(single):
        r, c = divmod(k, 6)
        x, y = PAD + c * 190, single_top + 26 + r * 84
        b = items[0]
        src = b["files"].get("color_png") or b["files"]["mono_png"]
        ic = Image.open(os.path.join(out, src)).resize((38, 38), Image.LANCZOS)
        img.paste(ic, (x, y + 10), ic)
        d.text((x + 48, y + 12), b.get("zh") or b.get("en"), font=F["name"], fill="#1F2329")
        d.text((x + 48, y + 32), vname, font=F["meta"], fill="#9AA1AB")

    d.text((PAD, H - 34), args.footer, font=F["meta"], fill="#A6ACB5")
    p = os.path.join(out, args.name)
    img.save(p, optimize=True)
    print(f"  ✓ {args.name}  {img.size}")


# ---------------------------------------------------------------- search hints

# 搜索引擎模板（与 multi-search-engine 技能同源；国内引擎先取首页会话再搜）
def cmd_search_hints(args):
    from urllib.parse import quote

    slugs = [s.strip() for s in args.slugs.split(",") if s.strip()]
    zh = [z.strip() for z in args.zh.split(",")] if args.zh else []
    zh += [""] * (len(slugs) - len(zh))

    for s, z in zip(slugs, zh):
        label = f"{s}" + (f" / {z}" if z else "")
        print(f"== {label}")
        # 英文源：官方矢量、聚合站、开源图标仓库
        print(f"  Google 官方矢量 : https://www.google.com/search?q={quote(f'\"{s}\" logo svg filetype:svg')}")
        print(f"  GitHub 仓库     : https://www.google.com/search?q={quote(f'site:github.com {s} logo svg')}")
        print(f"  维基共享        : https://commons.wikimedia.org/w/index.php?search={quote(f'{s} logo')}&title=Special:MediaSearch&type=image")
        # 中文源：国产产品的官网与发布稿往往只有中文引擎收得到
        if z:
            print(f"  百度（中文）    : https://www.baidu.com/s?wd={quote(f'{z} 官网 品牌 标志')}")
            print(f"  搜狗微信        : https://wx.sogou.com/weixin?type=2&query={quote(f'{z} 官方发布 品牌')}")
        else:
            print(f"  百度（中文）    : https://www.baidu.com/s?wd={quote(f'{s} logo 官网')}")
            print(f"  搜狗微信        : https://wx.sogou.com/weixin?type=2&query={quote(f'{s} 官方发布')}")
        print("  提示：百度需先 GET 首页取会话 Cookie 再搜，否则返回 1.5KB 反爬空壳页；")
        print("        搜狗微信可直连。搜到第三方矢量站后，务必回官网 favicon/新闻稿核对形状与配色。")


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(prog="iconkit", description="品牌图标采集工具包")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("probe", help="探测 slug 在各图标源的可用性")
    p.add_argument("--slugs", required=True, help="逗号分隔，如 deepseek,openai,flux")
    p.add_argument("--delay", type=float, default=0.2)
    p.set_defaults(func=cmd_probe)

    h = sub.add_parser("search-hints", help="为抓不到的品牌生成搜索引擎查询链接")
    h.add_argument("--slugs", required=True, help="逗号分隔的品牌 slug 或英文名")
    h.add_argument("--zh", default="", help="可选：中文名（逗号分隔，与 slugs 一一对应）")
    h.set_defaults(func=cmd_search_hints)

    f = sub.add_parser("fetch", help="批量抓取并导出")
    f.add_argument("--brands", required=True, help="brands.json 路径")
    f.add_argument("--out", required=True, help="输出目录")
    f.add_argument("--delay", type=float, default=0.25)
    f.add_argument("--fresh", action="store_true", help="不合并已有 manifest")
    f.set_defaults(func=cmd_fetch)

    w = sub.add_parser("wordmark", help="自绘文字标识")
    w.add_argument("--brands", required=True, help="wordmarks.json 路径")
    w.add_argument("--out", required=True)
    w.set_defaults(func=cmd_wordmark)

    s = sub.add_parser("sheet", help="按分类/厂商排联系表")
    s.add_argument("--manifest", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--group-by", choices=["cat", "vendor", "none"], default="cat")
    s.add_argument("--cols", type=int, default=4)
    s.add_argument("--cell-w", type=int, default=282)
    s.add_argument("--cell-h", type=int, default=214)
    s.add_argument("--icon", type=int, default=116)
    s.add_argument("--label", action="append", help="cat=显示名，可多次")
    s.add_argument("--title")
    s.add_argument("--footer", default="单色 / 彩色 SVG 与 512px PNG 见同目录 svg、png 文件夹")
    s.set_defaults(func=cmd_sheet)

    m = sub.add_parser("matrix", help="厂商 × 模态矩阵")
    m.add_argument("--manifest", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--name", default="厂商跨模态矩阵.png")
    m.add_argument("--title", default="厂商跨模态布局")
    m.add_argument("--skip", default="", help="跳过的 cat，逗号分隔（如公司标识所在的 cat）")
    m.add_argument("--label", action="append")
    m.add_argument("--footer", default="图标来源：LobeHub Icons / Simple Icons；自绘项见 README")
    m.set_defaults(func=cmd_matrix)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

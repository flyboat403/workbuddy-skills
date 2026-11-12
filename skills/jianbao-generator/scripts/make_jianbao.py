# -*- coding: utf-8 -*-
"""《四川省邓仕川名师工作室简报》docx 生成器
以用户确认过的模板（template/四川省邓仕川工作室简报-模板.docx）为基准，
将微信文章结构化 JSON（wx_article.json 格式）套版为同格式简报。

格式要点（2026-08-06 从用户修改稿识别）：
- 报头：LOGO + 红头文本框（方正小标宋简体 sz=52 / 方正公文黑体 sz=84，CD1F1E）+ 期号
- 标题：1~2 段，样式 pStyle=000026（一、标题：居中、方正小标宋简体、szCs=32、行距560固定）
- 引言/正文：仿宋_GB2312、两端对齐、首行缩进2字符、行距240（auto）
- 小节标题：独立段 + numPr 自动编号(numId=1, chineseCountingThousand "%1、") + 加粗 + 仿宋_GB2312
- 图片：居中、宽度 5000000 EMU(约13.9cm)，高度按原图比例
- 图注：居中、仿宋_GB2312、sz=28 / szCs=18
- 落款：表格（编辑部/审核签发/报送发/印数17份），日期自动同步

用法:
  python make_jianbao.py --json wx_article.json --imgs-dir wx_imgs \
      --out 输出.docx --issue "2026年第2期" [--date "2026年7月15日"] [--title "自定义标题"]
依赖: lxml, Pillow
"""
import argparse
import json
import os
import re
import sys
import zipfile
from io import BytesIO

import lxml.etree as ET
from PIL import Image, ImageEnhance

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
WP = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
RNS_OFF = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
RNS_PKG = '{http://schemas.openxmlformats.org/package/2006/relationships}'
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

IMG_W_EMU = 5000000  # 图片宽约 13.9cm
# 正文图最大像素宽：手机原图常见 4000~5700px，直接存 PNG 会让 docx 膨胀到 50MB+。
# 显示宽度仅 13.9cm（约 5.47 英寸），1400px 已相当于 256 DPI，印刷与屏幕均足够。
# 超出则等比缩放（长宽比不变，不影响 cy 计算）。
MAX_PX_W = 1400
# 模板中的正文图位（rId 与 media 文件固定可用，可覆盖）。
# ⚠️ 注意前缀：模板内图片条目路径为 word/media/imageN.png（rels 的 Target
#    相对 word/ 解析为 media/imageN.png，但 zip 条目必须带 word/ 前缀）
SLOT_RIDS = ['rId12', 'rId13', 'rId14']
SLOT_FILES = ['word/media/image2.png', 'word/media/image3.png', 'word/media/image4.png']


# ---------- 工具 ----------
def ptext(p):
    return ''.join(t.text or '' for t in p.findall('.//' + W + 't'))


def set_text(p, text):
    """把段落文本写入第一个 w:t，其余 w:t 清空（保留各 run 字体格式）"""
    ts = p.findall('.//' + W + 't')
    if not ts:
        return False
    ts[0].text = text
    ts[0].set(XML_SPACE, 'preserve')
    for t in ts[1:]:
        t.text = ''
    return True


def _replace_in_runs(ts, full, old, new):
    """在 run 文本序列中精确替换 old -> new。
    只改动覆盖 old 区间的 run，其余 run 文本与格式原样保留。
    返回是否发生替换。"""
    i = full.find(old)
    if i < 0:
        return False
    j = i + len(old)
    pos = 0
    replaced = False
    for t in ts:
        tlen = len(t.text or '')
        start, end = pos, pos + tlen
        pos = end
        if not replaced:
            # run 与 [i, j) 区间不相交 -> 不动
            if end <= i or start >= j:
                continue
            before = full[start:i] if start < i else ''
            after = full[j:end] if end > j else ''
            t.text = before + new + after
            replaced = True
        else:
            # 已写入 new；后续 run 若仍在 old 区间内则清空（或保留其区间外尾部）
            if start < j:
                after = full[j:end] if end > j else ''
                t.text = after
            else:
                break
        if t.text:
            t.set(XML_SPACE, 'preserve')
    return True


def replace_text_in(ps, old, new):
    """在段落/表格中跨 run 匹配 old 并替换为 new。
    ⚠️ 逐段处理：表格会递归遍历其全部 w:p 后代逐个替换，
    绝不在整个表格上做全文拼接 + set_text（那会扁平化整张表）。"""
    cnt = 0
    for p in ps:
        pars = [p] if p.tag == W + 'p' else p.findall('.//' + W + 'p')
        for par in pars:
            ts = par.findall('.//' + W + 't')
            if not ts:
                continue
            full = ''.join(t.text or '' for t in ts)
            if _replace_in_runs(ts, full, old, new):
                cnt += 1
    return cnt


def split_title(title, max_first=13):
    """标题拆 1~2 行：支持 '|' 手动断行；否则优先在标点后断行，最后按字数"""
    if '|' in title:
        parts = [s.strip() for s in title.split('|') if s.strip()]
        if len(parts) >= 2:
            return parts[:2]
    for sep in ('！', '？', '。', '，', '!', '?', '：'):
        idx = title.find(sep)
        if 0 < idx <= max_first:
            return [title[:idx + 1], title[idx + 1:]]
    if len(title) > max_first:
        return [title[:max_first], title[max_first:]]
    return [title]


def split_sections(text):
    """从剥离图注后的正文文本中切出 引言/小标题/正文 序列。
    返回 [('pre'|'body'|'heading', 内容), ...] 按原文顺序。
    小标题模式: "一、实地走访" 后接 &nbsp; 或 2+ 空格或全角空格
    """
    items = []
    pat = re.compile(
        r'([一二三四五六七八九十]+)、(?!\d)([^\s&nbsp;，。！？]{1,14}?)'
        r'(?:&nbsp;|\u3000|\s{2,})(.+)', re.S)
    rest = text.strip()
    m = pat.search(rest)
    while m:
        pre = rest[:m.start()].strip('&nbsp; ')
        if pre:
            items.append(('pre', pre))
        items.append(('heading', m.group(2)))
        rest = m.group(3)
        m = pat.search(rest)
    if rest.strip():
        kind = 'body' if items else 'pre'
        items.append((kind, rest.strip('&nbsp; ')))
    return items


def img_size_px(path):
    with Image.open(path) as im:
        return im.size


def calc_cy(w_px, h_px):
    return int(IMG_W_EMU * h_px / w_px)


# ---------- 图片轻度调色增强 ----------
# 微信文章原图多为室内手机拍摄 + 平台压缩，饱和度/对比度偏低（"灰蒙"感）。
# 默认对正文图做轻度增强：饱和度 +18%、对比度 +10%（不调亮度，避免过曝）。
ENHANCE_COLOR = 1.18    # 饱和度因子
ENHANCE_CONTRAST = 1.10  # 对比度因子


def enhance_image(im):
    """对 PIL Image 做轻度调色增强，返回新 Image。"""
    im = im.convert('RGB')
    im = ImageEnhance.Color(im).enhance(ENHANCE_COLOR)
    im = ImageEnhance.Contrast(im).enhance(ENHANCE_CONTRAST)
    return im


# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', required=True, help='微信文章结构化 JSON 路径')
    ap.add_argument('--imgs-dir', required=True, help='图片目录（img0.png/img1.png/...）')
    ap.add_argument('--out', required=True, help='输出 docx 路径')
    ap.add_argument('--issue', required=True, help='期号，如 "2026年第2期"')
    ap.add_argument('--date', default=None, help='印发日期，如 "2026年7月15日"；缺省取文章发布日期')
    ap.add_argument('--title', default=None, help='简报标题；缺省取文章标题')
    ap.add_argument('--no-enhance', action='store_true',
                    help='禁用图片轻度调色增强（默认开启：饱和度+18% 对比度+10%），'
                         '需要与微信原图完全一致时使用')
    ap.add_argument('--template',
                    default=os.path.join(os.path.dirname(os.path.dirname(
                        os.path.abspath(__file__))),
                        'template', '四川省邓仕川工作室简报-模板.docx'),
                    help='模板 docx 路径；缺省用 skill 自带模板（相对本脚本定位，跨机器可用）')
    args = ap.parse_args()

    art = json.load(open(args.json, encoding='utf-8'))
    title = args.title or art['title']
    issue = args.issue
    date = args.date or art.get('publish', '')[:10].replace('-', '年') + '日'
    # publish 形如 "2026-06-28 21:46" -> "2026年6月28日"
    if args.date is None:
        d = (art.get('publish') or '')[:10]
        y, m, dd = d.split('-')
        date = f'{int(y)}年{int(m)}月{int(dd)}日'
    print('标题:', title)
    print('期号:', issue, '| 日期:', date)

    # ---- 1. 解析 blocks -> 内容流 ----
    blocks = art['blocks']
    # 去掉文末署名块（"文图丨" / "编辑丨" / 含"投稿邮箱"等）
    if blocks and blocks[-1][0] == 'text':
        tail = blocks[-1][1]
        if any(k in tail for k in ('文图丨', '文丨', '编辑丨', '投稿邮箱')):
            blocks = blocks[:-1]
    # 装饰图过滤：只保留"最后一个正文 text 块"之前的 img 块为正文图。
    # 微信文章文末常附 gif 横幅 / 表情 / 小图标等装饰图，必须剔除。
    last_text_pos = max(i for i, (k, _c) in enumerate(blocks) if k == 'text')

    flow = []  # ('pre'|'heading'|'body'|'img'|'caption', 内容)
    last_was_img = False
    last_was_cap = False
    for i, (kind, content) in enumerate(blocks):
        if kind == 'img':
            if i < last_text_pos:
                flow.append(('img', content))
                last_was_img = True
                last_was_cap = False
            else:
                print(f'跳过文末装饰图块 #{i}')
            continue
        # text 块：先剥离图注（首个 &nbsp; 前为非空且非数字开头的说明文字）
        text = content
        parts = text.split('&nbsp;', 1)
        cap = None
        if (len(parts) == 2 and parts[0].strip()
                and not parts[0].strip()[0].isdigit()):
            cap = parts[0].strip()
            text = parts[1]
        elif len(parts) == 1 and (last_was_img or last_was_cap) and text.strip():
            # 独立图注块：紧跟图片/图注之后、文本较短且非数字开头 -> 视为图注
            t0 = text.strip()
            if not t0[0].isdigit() and len(t0) <= 40:
                cap = t0
                text = ''
        cap_detected = False
        if cap and (last_was_img or last_was_cap):
            flow.append(('caption', cap))
            cap_detected = True
            last_was_cap = True
            last_was_img = False
            if text.strip():
                # &nbsp; 连接式"图注&nbsp;正文"：图注后紧跟正文，连续图注机会到此为止
                last_was_cap = False
        # 独立小标题块：整块形如 "一、AI现状认知与工具搭建" -> heading
        mh = re.fullmatch(r'[一二三四五六七八九十]+、(\S{1,20})', text.strip())
        if mh and not last_was_cap:
            flow.append(('heading', mh.group(1)))
            last_was_img = False
            last_was_cap = False
            continue
        # 再拆 引言/小标题/正文
        for kind2, c2 in split_sections(text):
            flow.append((kind2, c2))
        last_was_img = False
        # 仅当本块未被识别为图注时才重置 last_was_cap，以支持"连续图注"
        # （一张图后跟两条图注，如 "漫剧创作实操" + "部分作品展示"）
        if not cap_detected:
            last_was_cap = False
    print('内容流元素数:', len(flow))

    # ---- 2. 读模板 ----
    zin = zipfile.ZipFile(args.template)
    items = {}
    for n in zin.namelist():
        if not n.endswith('/'):
            items[n] = zin.read(n)
    zin.close()

    root = ET.fromstring(items['word/document.xml'])
    body = root.find(W + 'body')

    # 原型提取（深拷贝，保留全部格式）
    def proto(i):
        return ET.fromstring(ET.tostring(body[i], encoding='unicode'))

    p_header = proto(0)   # 报头（含期号）
    p_date = proto(1)     # 编号/日期行
    p_blank2 = proto(2)   # 空行
    p_t1 = proto(3)       # 标题段样式
    p_blank5 = proto(5)   # 标题后空行
    p_body = proto(6)     # 正文段样式
    p_head = proto(7)     # 小标题段样式（numPr 自动编号 + 加粗）
    p_img = proto(9)      # 图片段样式（居中）
    p_cap = proto(10)     # 图注段样式（sz=28 居中）
    p_tbl = proto(21)     # 落款表
    sectpr = body.find(W + 'sectPr')

    # ---- 3. 期号 / 日期 ----
    # 期号在报头 [0] 内（如 （2026年第1期））
    hdr_ts = p_header.findall('.//' + W + 't')
    ok_issue = False
    for i, t in enumerate(hdr_ts):
        if t.text and '第' in t.text and '期' in t.text:
            new = '（' + issue + '）' if not issue.startswith('（') else issue
            t.text = new
            t.set(XML_SPACE, 'preserve')
            ok_issue = True
            break
    if not ok_issue:
        print('!! 报头未找到期号文本')
    # 日期：编号行 + 落款表（旧日期 "2026年6月28日"）
    old_date = '2026年6月28日'
    c1 = replace_text_in([p_date], old_date, date)
    c2 = replace_text_in([p_tbl], old_date, date)
    print(f'日期替换: 编号行{c1}处 落款表{c2}处')

    # ---- 4. 标题 ----
    lines = split_title(title)
    p_t1 = ET.fromstring(ET.tostring(p_t1, encoding='unicode'))
    set_text(p_t1, lines[0])
    p_t2 = None
    if len(lines) > 1:
        p_t2 = proto(4)
        set_text(p_t2, lines[1])

    # ---- 5. 组装段落 ----
    paras = []
    paras.append(p_header)
    paras.append(p_date)
    paras.append(p_blank2)
    paras.append(p_t1)
    if p_t2 is not None:
        paras.append(p_t2)
    paras.append(p_blank5)

    # 内容流：pre/body -> 正文段；heading -> 小标题段；img -> 图片段；caption -> 图注段
    img_seq = 0
    for kind, c in flow:
        if kind in ('pre', 'body'):
            p = ET.fromstring(ET.tostring(p_body, encoding='unicode'))
            set_text(p, c.replace('&nbsp;', ' '))
            paras.append(p)
        elif kind == 'heading':
            p = ET.fromstring(ET.tostring(p_head, encoding='unicode'))
            set_text(p, c)
            paras.append(p)
        elif kind == 'img':
            p = ET.fromstring(ET.tostring(p_img, encoding='unicode'))
            # 图片路径：目录下按 imgN 顺序找（img0.png/img1.png/...）
            fname = f'img{img_seq}.png'
            fpath = os.path.join(args.imgs_dir, fname)
            if not os.path.exists(fpath):
                # 兼容 .jpg/.jpeg/.webp
                for ext in ('.jpg', '.jpeg', '.webp', '.gif'):
                    alt = os.path.join(args.imgs_dir, f'img{img_seq}{ext}')
                    if os.path.exists(alt):
                        fpath = alt
                        break
            if not os.path.exists(fpath):
                print(f'!! 缺少图片 {fname}，跳过')
                img_seq += 1
                continue
            # 兜底：gif / 极小图视为装饰，跳过
            if fpath.lower().endswith('.gif'):
                print(f'!! 跳过 gif 图 {fname}')
                img_seq += 1
                continue
            w_px, h_px = img_size_px(fpath)
            if min(w_px, h_px) < 120:
                print(f'!! 跳过过小图 {fname} {w_px}x{h_px}')
                img_seq += 1
                continue
            cy = calc_cy(w_px, h_px)
            # 确定 rId/media 槽位
            if img_seq < len(SLOT_RIDS):
                rid, target = SLOT_RIDS[img_seq], SLOT_FILES[img_seq]
            else:
                n = img_seq - len(SLOT_RIDS)
                rid = f'rId{15 + n}'
                target = f'word/media/image{5 + n}.png'
            # 改 drawing
            inline = p.find(WP + 'inline')
            if inline is None:
                inline = p.find('.//' + WP + 'inline')
            ext = inline.find(WP + 'extent')
            ext.set('cx', str(IMG_W_EMU))
            ext.set('cy', str(cy))
            blip = p.find('.//' + A + 'blip')
            blip.set(RNS_OFF + 'embed', rid)
            for xext in p.findall('.//' + A + 'ext'):
                if 'cx' in xext.attrib and 'cy' in xext.attrib:
                    xext.set('cx', str(IMG_W_EMU))
                    xext.set('cy', str(cy))
            # 图片转 PNG 字节（覆盖槽位文件 或 新文件）
            im = Image.open(fpath)
            im = im.convert('RGB') if im.mode in ('P', 'RGBA', 'LA') else im
            if im.width > MAX_PX_W:
                new_h = max(1, round(im.height * MAX_PX_W / im.width))
                im = im.resize((MAX_PX_W, new_h), Image.LANCZOS)
                print(f'图片{img_seq}: {fname} 已缩放至 {MAX_PX_W}x{new_h}')
            if not args.no_enhance:
                im = enhance_image(im)
                print(f'图片{img_seq}: {fname} 已轻度调色(饱和x{ENHANCE_COLOR}, 对比x{ENHANCE_CONTRAST})')
            bio = BytesIO()
            im.convert('RGB').save(bio, format='PNG')
            items[target] = bio.getvalue()
            paras.append(p)
            print(f'图片{img_seq}: {fname} {w_px}x{h_px} -> {rid}/{target} cy={cy}')
            img_seq += 1
        elif kind == 'caption':
            p = ET.fromstring(ET.tostring(p_cap, encoding='unicode'))
            set_text(p, c)
            paras.append(p)

    paras.append(p_tbl)
    paras.append(proto(22))  # 表后空行

    # ---- 6. 重建 body（保留 sectPr 及其前序必需元素）----
    for child in list(body):
        body.remove(child)
    for p in paras:
        body.append(p)
    if sectpr is not None:
        body.append(sectpr)

    items['word/document.xml'] = ET.tostring(
        root, encoding='UTF-8', xml_declaration=True, standalone=True)

    # ---- 7. rels：若新增了超出 3 张的图片关系 ----
    if img_seq > len(SLOT_RIDS):
        rroot = ET.fromstring(items['word/_rels/document.xml.rels'])
        for k in range(len(SLOT_RIDS), img_seq):
            n = k - len(SLOT_RIDS)
            rid = f'rId{15 + n}'
            # ⚠️ rels 的 Target 相对 word/ 解析，必须写 media/imageN.png，
            #    不能带 word/ 前缀（zip 内条目路径才需要 word/ 前缀）。
            el = ET.SubElement(rroot, RNS_PKG + 'Relationship')
            el.set('Id', rid)
            el.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image')
            el.set('Target', f'media/image{5 + n}.png')
        items['word/_rels/document.xml.rels'] = ET.tostring(
            rroot, encoding='UTF-8', xml_declaration=True)

    # ---- 8. 写出 ----
    with zipfile.ZipFile(args.out, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n, data in items.items():
            zout.writestr(n, data)
    print('已生成:', args.out)


if __name__ == '__main__':
    main()

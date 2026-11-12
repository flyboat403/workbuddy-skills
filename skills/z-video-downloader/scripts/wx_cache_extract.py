# -*- coding: utf-8 -*-
"""wx_cache_extract.py — 微信 PC 客户端本地缓存提取（视频号兜底方案）。

背景：z-video-downloader 的视频号在线解析服务（sph.litao.workers.dev）已要求授权
且 *.workers.dev 在大陆直连不稳，分享链接在线解析多数情况失败。

本脚本从本机微信（Weixin 4.x / WeChat 3.x）已接收、已播放的媒体缓存中提取真实视频
文件（文件头校验 mp4/mov），适用于：
  1. 视频号分享链接在线解析失败时，作为兜底；
  2. 用户已在微信 PC 端播放/接收过该视频，想把它另存出来。

注意：只能提取「本机微信里已经存在缓存」的视频；没播放过、没接收过的视频不在
缓存里，请改用 ltaoo/wx_channels_download 桌面工具（见 SKILL.md 视频号章节）。

用法：
  python wx_cache_extract.py                       # 列出候选（默认近 30 天）
  python wx_cache_extract.py --days 7 --min-mb 1
  python wx_cache_extract.py --pick 1              # 把第 1 个候选复制到输出目录
  python wx_cache_extract.py --pick 2 --name "我的视频"
  python wx_cache_extract.py --root "E:\\WinXin"   # 手动指定微信数据根

只读取与复制，绝不移动/删除微信原始缓存。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

VIDEO_MAGIC = {  # offset 4 处的 brand
    b"ftyp": "mp4",
    b"moov": "mov",
    b"wide": "mov",
    b"skip": "mp4",
}
EXCLUDED_ACCOUNT_DIRS = {"all users", "applet", "backup", "wmpf", "all_users"}
SCAN_SKIP_DIRS = {"db_storage", "config", "temp", "log"}
DEFAULT_DAYS = 30
DEFAULT_MIN_MB = 0.5
DEFAULT_OUT_SUBDIR = "wx-cache-extract"


def detect_data_roots(explicit_root: str = "") -> list[Path]:
    """按优先级返回可能的 xwechat_files 根目录列表。"""
    roots: list[Path] = []
    if explicit_root:
        p = Path(explicit_root)
        roots.append(p if p.name == "xwechat_files" else p / "xwechat_files")
        roots.append(p)  # 也允许直接指向 xwechat_files 本身

    # 微信 4.x：存储路径写在 %APPDATA%\Tencent\xwechat\config\*.ini 的首个非空行
    appdata = os.environ.get("APPDATA")
    if appdata:
        cfg_dir = Path(appdata) / "Tencent" / "xwechat" / "config"
        if cfg_dir.is_dir():
            for ini in sorted(cfg_dir.glob("*.ini")):
                try:
                    for line in ini.read_text(encoding="utf-8", errors="ignore").splitlines():
                        line = line.strip()
                        if line:
                            roots.append(Path(line) / "xwechat_files")
                            break
                except OSError:
                    continue

    # 经典默认位置
    home = Path.home()
    roots.append(home / "Documents" / "xwechat_files")
    roots.append(home / "Documents" / "WeChat Files")

    seen, out = set(), []
    for r in roots:
        key = str(r).lower()
        if key not in seen and r.is_dir():
            seen.add(key)
            out.append(r)
    return out


def sniff_video(path: Path) -> str | None:
    """读文件头判断是否 mp4/mov，返回容器类型或 None。"""
    try:
        with path.open("rb") as h:
            head = h.read(12)
    except OSError:
        return None
    if len(head) >= 8 and head[4:8] in VIDEO_MAGIC:
        return VIDEO_MAGIC[head[4:8]]
    return None


def collect_candidates(roots: list[Path], days: int, min_mb: float) -> tuple[list[dict], list[str]]:
    """扫描所有账号目录，返回候选列表（mtime 倒序）与扫描说明。"""
    cutoff = time.time() - days * 86400
    min_bytes = int(min_mb * 1024 * 1024)
    candidates: list[dict] = []
    notes: list[str] = []

    for root in roots:
        for account in sorted(root.iterdir()):
            if not account.is_dir():
                continue
            if account.name.lower() in EXCLUDED_ACCOUNT_DIRS:
                continue
            for dp, dns, fns in os.walk(account):
                rel = dp[len(str(account)):].count(os.sep)
                if rel > 4:
                    dns[:] = []
                    continue
                dns[:] = [d for d in dns if d.lower() not in SCAN_SKIP_DIRS]
                for fn in fns:
                    p = Path(dp) / fn
                    try:
                        st = p.stat()
                    except OSError:
                        continue
                    if st.st_size < min_bytes or st.st_mtime < cutoff:
                        continue
                    kind = sniff_video(p)
                    if not kind:
                        continue
                    candidates.append(
                        {
                            "mtime": st.st_mtime,
                            "time": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                            "size": st.st_size,
                            "size_mb": round(st.st_size / 1048576, 2),
                            "container": kind,
                            "account": account.name,
                            "path": str(p),
                        }
                    )

    candidates.sort(key=lambda c: c["mtime"], reverse=True)
    for i, c in enumerate(candidates, 1):
        c["index"] = i
    return candidates, notes


def unique_path(target: Path) -> Path:
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    for i in range(1, 1000):
        cand = target.with_name(f"{stem}_{i}{suffix}")
        if not cand.exists():
            return cand
    return target.with_name(f"{stem}_{int(time.time())}{suffix}")


def main() -> int:
    ap = argparse.ArgumentParser(description="从微信 PC 客户端本地缓存提取视频（视频号兜底）")
    ap.add_argument("--list", action="store_true", help="列出候选（默认行为，可省略）")
    ap.add_argument("--root", default="", help="微信数据根目录（如 E:\\WinXin），默认自动探测")
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS, help="只列最近 N 天（默认 30）")
    ap.add_argument("--min-mb", type=float, default=DEFAULT_MIN_MB, help="最小体积 MB（默认 0.5）")
    ap.add_argument("--pick", type=int, default=0, help="复制列表中第 N 个候选（1 起）")
    ap.add_argument("--out-dir", default="", help="复制目标目录（默认 Video/Downloads/wx-cache-extract-日期）")
    ap.add_argument("--name", default="", help="复制后的文件名（不含扩展名）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出候选列表")
    args = ap.parse_args()

    roots = detect_data_roots(args.root)
    if not roots:
        print("未找到微信数据目录。请确认微信 PC 端已登录使用过，或用 --root 指定数据根。")
        return 2

    candidates, _ = collect_candidates(roots, args.days, args.min_mb)

    if args.json:
        print(json.dumps({"count": len(candidates), "roots": [str(r) for r in roots],
                          "candidates": candidates}, ensure_ascii=False, indent=2))
        return 0

    print(f"微信数据根：{', '.join(str(r) for r in roots)}")
    print(f"候选视频 {len(candidates)} 个（近 {args.days} 天，≥{args.min_mb}MB，按时间倒序）：")
    for c in candidates[:40]:
        print(f"  [{c['index']:>3}] {c['time']}  {c['size_mb']:>8.2f}MB  {c['container']:3}  {c['path']}")
    if len(candidates) > 40:
        print(f"  ... 其余 {len(candidates) - 40} 个见 --json 输出")
    if not candidates:
        print("没有候选。请先在微信 PC 端播放/接收该视频（缓存才会生成），再运行本脚本。")
        return 1

    if args.pick <= 0:
        print("\n用 --pick <编号> 把对应文件复制到输出目录（原始缓存不会被移动或删除）。")
        return 0

    chosen = next((c for c in candidates if c["index"] == args.pick), None)
    if not chosen:
        print(f"编号 {args.pick} 不在候选列表中。")
        return 2

    out_dir = Path(args.out_dir) if args.out_dir else (
        Path.cwd() / "Video" / "Downloads" / f"{DEFAULT_OUT_SUBDIR}-{datetime.now():%Y%m%d}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    src = Path(chosen["path"])
    ext = src.suffix.lower() or f".{chosen['container']}"
    base = args.name.strip() or f"wx-cache-{datetime.now():%Y%m%d-%H%M%S}"
    target = unique_path(out_dir / (base + ext))
    shutil.copy2(src, target)

    print(f"\n已提取：{src}")
    print(f"      → {target}  ({chosen['size_mb']:.2f}MB)")
    print("提示：提取自本机微信缓存，原文件仍在微信数据目录中。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

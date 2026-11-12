#!/usr/bin/env python3
"""抖音视频下载：Playwright 拦截 aweme/detail API → 提取 douyinvod CDN 直链 → requests 下载。

核心模式（可复用于任意抖音视频）：
  1. 用 Playwright（Chromium）无头加载抖音视频页 `https://www.douyin.com/video/<aweme_id>`。
  2. 监听页面所有响应，拦截 `aweme/v1/web/aweme/detail` 这个内部 API：
        - 抖音 Web 端打开视频页时会向后端请求该 API 获取视频详情 JSON；
        - 响应体里的 `aweme_detail.video` 含 `bit_rate[].play_api` / `play_addr.url_list` /
          `download_addr.url_list`，这些就是带签名的 `*.douyinvod.com` CDN 直链。
  3. 从中挑出最清晰且真实可达的 CDN 直链（优先 `douyinvod.com`，按码率降序）。
  4. 用 `requests` + `Referer: https://www.douyin.com/` + 桌面 UA 直接流式下载，
     保留 `.part` 临时文件并支持 HTTP Range 断点续传、超大文件拦截。

既可作为独立 CLI 使用，也可被 `download_video.py` import 后统一调度：

    # 独立：提取并打印直链（不下载，便于验证/手动下载）
    python douyin_playwright.py --url "https://www.douyin.com/video/734...x" --extract-only

    # 独立：提取并下载
    python douyin_playwright.py --url "https://www.douyin.com/video/734...x" --out-dir ./out

依赖（WorkBuddy managed Python venv 已具备）：
    - playwright 1.64.1（Chromium 内核：chromium-1248 + chromium_headless_shell-1248，
      2026-11-09 经 npmmirror 镜像补装；本机另有 chromium-1228 供 3.13.12 用户级 playwright 1.61 使用）
    - requests

注意：中国大陆网络下 `playwright install` 默认 CDN（cdn.playwright.dev）几乎不可达，
    需设置镜像：PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import requests
except ImportError:  # pragma: no cover
    print("ERROR: requests 未安装", file=sys.stderr)
    raise

try:
    from playwright.sync_api import sync_playwright

    _PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover - 被 download_video.py import 时不应致命
    _PLAYWRIGHT_AVAILABLE = False

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
DOUYIN_REFERER = "https://www.douyin.com/"
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".mkv", ".flv", ".ogv"}


# ── 工具函数 ──────────────────────────────────────────────────────────────
def is_douyin_url(url: str) -> bool:
    """判断是否为抖音域名链接（含 v.douyin.com 短链）。"""
    host = urlparse(url).netloc.lower()
    return host == "douyin.com" or host.endswith(".douyin.com")


def safe_filename(text: str, max_len: int = 60) -> str:
    """把视频描述清洗为合法文件名。"""
    name = re.sub(r'[\\/*?:"<>|]', "_", (text or "").strip())
    name = re.sub(r"\s+", "_", name)
    return (name[:max_len] or "douyin_video").strip("_") or "douyin_video"


# ── 步骤 1+2：Playwright 加载并拦截 API ────────────────────────────────────
def _make_response_handler() -> tuple[Any, dict]:
    """返回一个 (handler, state)。handler 在每次响应时调用，捕获 aweme/detail。"""
    state: dict[str, Any] = {"aweme": None, "raw": None}

    def handler(response) -> None:
        if "aweme/v1/web/aweme/detail" not in response.url:
            return
        try:
            body = response.json()
        except Exception:
            return
        if not isinstance(body, dict):
            return
        detail = body.get("aweme_detail")
        if isinstance(detail, dict) and detail:
            state["aweme"] = detail
            state["raw"] = body

    return handler, state


def _extract_from_html(page) -> dict | None:
    """兜底：API 未捕获时，从页面初始 HTML 中正则提取 douyinvod 直链。"""
    try:
        html = page.content()
    except Exception:
        return None
    urls = re.findall(r'https?://[^\s"\'\\]+douyinvod\.com[^\s"\'\\]*', html)
    seen: set[str] = set()
    uniq: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    if not uniq:
        return None
    return {"video": {"play_addr": {"url_list": uniq}}}


def extract_aweme_detail(page_url: str, *, timeout: int = 60, headless: bool = True):
    """加载抖音页并拦截 aweme/detail，返回 (aweme_detail, raw_body)。

    返回 (None, None) 表示既没拦截到 API，也没从 HTML 兜底提取到直链。
    """
    if not _PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("playwright 未安装：pip install playwright && playwright install chromium")

    handler, state = _make_response_handler()
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport={"width": 1280, "height": 720},
            locale="zh-CN",
            extra_http_headers={"Referer": DOUYIN_REFERER},
        )
        # 抹掉 webdriver 特征，降低被风控的概率
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        page = context.new_page()
        page.on("response", handler)

        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=timeout * 1000)
        except Exception:
            # 导航超时/被拦截也先继续——API 请求很可能已经在后台发出并被捕获
            pass

        # 轮询等待 API 响应被捕获；期间滚动页面尝试触发播放
        deadline = time.time() + timeout
        while time.time() < deadline:
            if state["aweme"] is not None:
                break
            try:
                page.mouse.wheel(0, 400)
            except Exception:
                pass
            time.sleep(0.5)

        # 兜底：API 没拿到，尝试从页面 HTML 提取直链
        if state["aweme"] is None:
            fallback = _extract_from_html(page)
            if fallback is not None:
                state["aweme"] = fallback

        browser.close()

    return state["aweme"], state["raw"]


# ── 步骤 3：从 JSON 提取并排序 CDN 直链 ───────────────────────────────────
def extract_cdn_candidates(aweme_detail: dict) -> list[tuple[str, dict]]:
    """从 aweme_detail 抽出所有候选直链，返回 [(url, meta), ...]。"""
    if not aweme_detail:
        return []
    video = aweme_detail.get("video", {}) or {}
    candidates: list[tuple[str, dict]] = []

    # 1) bit_rate 中的 play_api / play_addr.url_list（按码率降序，最清晰）
    #    注：抖音 video.bit_rate 元素可能同时含 `play_api` 字段与 `play_addr.url_list`，
    #    两种路径都覆盖，提升不同版本接口下的兼容性。
    for br in sorted(
        video.get("bit_rate", []) or [],
        key=lambda b: (b or {}).get("bit_rate", 0) or 0,
        reverse=True,
    ):
        br = br or {}
        api = br.get("play_api")
        if api:
            candidates.append(
                (api, {"source": "bit_rate_api", "bit_rate": br.get("bit_rate", 0) or 0})
            )
        for u in (br.get("play_addr", {}) or {}).get("url_list", []) or []:
            if u:
                candidates.append(
                    (u, {"source": "bit_rate_play_addr", "bit_rate": br.get("bit_rate", 0) or 0})
                )

    # 2) play_addr / 3) download_addr
    for key in ("play_addr", "download_addr"):
        for u in (video.get(key, {}) or {}).get("url_list", []) or []:
            if u:
                candidates.append((u, {"source": key}))

    return candidates


def order_candidates(candidates: list[tuple[str, dict]]) -> list[tuple[str, dict]]:
    """排序：真实 CDN（douyinvod.com）优先，同组内按码率降序；其余（短链等）置后。"""
    douyin = [(u, m) for u, m in candidates if "douyinvod.com" in u]
    other = [(u, m) for u, m in candidates if "douyinvod.com" not in u]
    douyin.sort(key=lambda x: x[1].get("bit_rate", 0) or 0, reverse=True)
    return douyin + other


# ── 步骤 4：requests 带 Referer 流式下载（续传 / .part / 大小限制）──────────
def download_cdn_video(
    session: requests.Session,
    url: str,
    out_dir: Path,
    *,
    filename: str,
    max_video_mb: float = 2000.0,
    timeout: int = 30,
    chunk_size: int = 16 * 1024,
) -> dict[str, Any]:
    """下载单个 CDN 直链，复用 .part 临时文件与 Range 续传。"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / filename
    partial = Path(str(target) + ".part")
    limit = int(max_video_mb * 1024 * 1024)
    headers = {"User-Agent": DEFAULT_USER_AGENT, "Referer": DOUYIN_REFERER}
    record: dict[str, Any] = {"status": "failed", "files": [], "bytes": 0, "note": ""}

    try:
        resp = session.get(url, headers=headers, stream=True, timeout=timeout)
        resp.raise_for_status()

        # 首包大小校验
        length = resp.headers.get("Content-Length")
        if length:
            try:
                if int(length) > limit:
                    record["note"] = f"video-larger-than-{max_video_mb:g}MB"
                    return record
            except ValueError:
                pass

        # 断点续传
        resume_from = partial.stat().st_size if partial.exists() else 0
        mode = "wb"
        expected_total = 0
        if resume_from:
            resp.close()
            range_headers = dict(headers)
            range_headers["Range"] = f"bytes={resume_from}-"
            resp = session.get(url, headers=range_headers, stream=True, timeout=timeout)
            resp.raise_for_status()
            if resp.status_code == 206:
                m = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", resp.headers.get("Content-Range", ""))
                if not m or int(m.group(1)) != resume_from:
                    resume_from = 0
                else:
                    expected_total = int(m.group(3))
                    mode = "ab"
            else:
                resume_from = 0

        length = resp.headers.get("Content-Length")
        if not expected_total and length:
            try:
                expected_total = resume_from + int(length)
            except ValueError:
                expected_total = 0
        if expected_total and expected_total > limit:
            record["note"] = f"video-larger-than-{max_video_mb:g}MB"
            return record

        size = resume_from
        with open(partial, mode) as fh:
            for chunk in resp.iter_content(chunk_size):
                if not chunk:
                    continue
                size += len(chunk)
                if size > limit:
                    fh.close()
                    partial.unlink(missing_ok=True)
                    record["note"] = f"video-larger-than-{max_video_mb:g}MB"
                    return record
                fh.write(chunk)

        if expected_total and size != expected_total:
            record["note"] = f"incomplete-download:{size}!={expected_total} | partial={partial}"
            return record

        partial.replace(target)
        record["status"] = "ok"
        record["files"] = [str(target)]
        record["bytes"] = size
        return record
    except Exception as exc:  # noqa: BLE001
        note = str(exc)
        if partial.exists():
            note += f" | partial={partial}"
        record["note"] = note[:300]
        return record


# ── 组合：提取 + 下载 ─────────────────────────────────────────────────────
def download_douyin(
    page_url: str,
    out_dir: str | Path,
    *,
    max_video_mb: float = 2000.0,
    timeout: int = 60,
    extract_only: bool = False,
    quality: str = "best",
    title: str | None = None,
) -> dict[str, Any]:
    """抖音视频一站式下载，返回与 download_video.py 兼容的 record。

    record 关键字段：status(ok/failed)、platform、files、bytes、cdn_url、candidates、note。
    """
    record: dict[str, Any] = {
        "url": page_url,
        "status": "failed",
        "platform": "Douyin (Playwright API)",
        "files": [],
        "bytes": 0,
        "note": "",
    }
    if not is_douyin_url(page_url):
        record["note"] = "not-a-douyin-url"
        return record
    if not _PLAYWRIGHT_AVAILABLE:
        record["note"] = "playwright-not-installed"
        return record

    try:
        aweme, _ = extract_aweme_detail(page_url, timeout=timeout)
    except Exception as exc:
        record["note"] = f"extract-error: {str(exc)[:240]}"
        return record
    if not aweme:
        record["note"] = "aweme-detail-not-captured"
        return record

    desc = (aweme.get("desc") or "").strip() or "douyin_video"
    candidates = order_candidates(extract_cdn_candidates(aweme))
    if not candidates:
        record["note"] = "no-cdn-url-found"
        return record

    record["candidates"] = [u for u, _ in candidates]
    record["cdn_url"] = candidates[0][0]
    record["desc"] = desc

    if extract_only:
        record["status"] = "ok"
        record["note"] = "extract-only"
        return record

    stem = safe_filename(title or desc)[:60] or "douyin_video"
    filename = f"{stem}.mp4"
    out_dir = Path(out_dir)
    session = requests.Session()

    # 按优先级逐个尝试候选直链；不同 URL 内容不同，每次尝试前清理上次 .part
    ordered = candidates if quality != "worst" else list(reversed(candidates))
    for url, meta in ordered:
        part = out_dir / f"{filename}.part"
        if part.exists():
            part.unlink(missing_ok=True)
        rec = download_cdn_video(
            session,
            url,
            out_dir,
            filename=filename,
            max_video_mb=max_video_mb,
            timeout=timeout,
        )
        if rec["status"] == "ok":
            record.update(rec)
            record["status"] = "ok"
            record["cdn_url"] = url
            record["cdn_meta"] = meta
            return record

    record["note"] = "all-cdn-candidates-failed"
    return record


# ── CLI ────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="抖音视频下载：Playwright 拦截 aweme/detail API 提取 douyinvod CDN 直链后下载"
    )
    ap.add_argument("--url", required=True, help="抖音视频页 URL（douyin.com/video/...）")
    ap.add_argument("--out-dir", default=".", help="输出目录（默认当前目录）")
    ap.add_argument("--title", default="", help="文件名标题（默认用视频描述）")
    ap.add_argument("--extract-only", action="store_true", help="仅提取并打印直链，不下载")
    ap.add_argument("--max-video-mb", type=float, default=2000.0, help="单文件大小上限(MB)")
    ap.add_argument("--quality", choices=["best", "worst"], default="best")
    ap.add_argument("--timeout", type=int, default=60, help="Playwright 等待 API 的超时(秒)")
    ap.add_argument("--visible", action="store_true", help="显示浏览器窗口（非无头）")
    args = ap.parse_args(argv)

    if args.extract_only:
        if not _PLAYWRIGHT_AVAILABLE:
            print("ERROR: playwright 未安装", file=sys.stderr)
            return 2
        aweme, _ = extract_aweme_detail(args.url, timeout=args.timeout, headless=not args.visible)
        if not aweme:
            print("ERROR: 未能捕获 aweme/detail 响应，也未从页面提取到直链", file=sys.stderr)
            return 2
        cands = order_candidates(extract_cdn_candidates(aweme))
        print(
            json.dumps(
                {
                    "desc": aweme.get("desc"),
                    "candidates": [u for u, _ in cands],
                    "selected": cands[0][0] if cands else None,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    record = download_douyin(
        args.url,
        args.out_dir,
        max_video_mb=args.max_video_mb,
        timeout=args.timeout,
        quality=args.quality,
        title=args.title or None,
    )
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0 if record["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

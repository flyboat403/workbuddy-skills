---
name: z-video-downloader
description: 当用户给出视频链接、链接清单或 z-web-pack 的
  04-media-inventory.md，并要求"下载视频""视频下载""帮我把这个视频下下来""下载
  B站/哔哩哔哩视频""下载 m3u8/mp4 直链""把视频保存到本地""批量下载这些视频""下载字幕""下载视频号""视频号下载"时必须使用。本
  skill 支持单个、多个、文本清单和媒体清单输入，覆盖
  YouTube、Bilibili、Vimeo、X/Twitter、TikTok、抖音、Instagram、Facebook、微信视频号等 yt-dlp
  平台及常见视频直链；支持断点续传、重试、字幕、封面和下载历史，保存到 Video/Downloads 并生成报告。
agent_created: true
---

# 视频下载器

把用户给的视频链接下载成本地视频文件。网页素材采集只记录视频链接，真正下载统一交给本 skill。直链视频支持 `.part` 文件和 HTTP Range 续传，平台视频和 m3u8 使用 `yt-dlp` 的续传、分片并发与重试能力；遇到平台风控时优先使用导出的 `cookies.txt` 文件重试。微信视频号（`weixin.qq.com/sph/` 分享链接）通过在线解析服务直接获取视频地址下载，无需本地安装额外工具。

## 依赖

| 依赖 | 路径 |
|------|------|
| Python | `~/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe` |
| yt-dlp | `C:\Python314\Scripts\yt-dlp` |
| ffmpeg | `C:/Program Files/ffmpeg/bin/ffmpeg.exe` |

## 默认输出

所有文件默认保存到当前工作区的 `Video/Downloads`：

```text
Video/Downloads/YYYY-MM-DD-主题/
├── 下载的视频文件.mp4
├── 下载的视频文件.info.json
├── download-report.md
└── download-report.json
```

## 常用命令

单个链接：

```bash
~/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe ~/.workbuddy-ai/skills/z-video-downloader/scripts/download_video.py \
  --title "主题名" \
  "https://www.bilibili.com/video/BV..."
```

多个链接：

```bash
~/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe ~/.workbuddy-ai/skills/z-video-downloader/scripts/download_video.py \
  --title "主题名" \
  "https://www.youtube.com/watch?v=..." \
  "https://www.bilibili.com/video/BV..."
```

直接读取 `z-web-pack` 的媒体清单：

```bash
~/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe ~/.workbuddy-ai/skills/z-video-downloader/scripts/download_video.py \
  --title "主题名" \
  --inventory "Clippings/Reading/本次资料包/04-media-inventory.md"
```

从文本批量下载，每行一个链接，空行和 `#` 注释会自动跳过：

```bash
~/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe ~/.workbuddy-ai/skills/z-video-downloader/scripts/download_video.py \
  --title "主题名" \
  --url-file "video-urls.txt"
```

遇到 YouTube bot 验证、B 站 412、登录可见内容：

```bash
~/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe ~/.workbuddy-ai/skills/z-video-downloader/scripts/download_video.py \
  --cookies-file "cookies/cookies.txt" \
  --title "主题名" \
  "视频链接"
```

微信视频号分享链接：

```bash
~/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe ~/.workbuddy-ai/skills/z-video-downloader/scripts/download_video.py \
  --title "视频号主题" \
  "https://weixin.qq.com/sph/Axv548mzBF"
```

视频号链接会自动识别并通过在线解析服务下载，默认保存 H.264 和 H.265 两个版本。

抖音视频（Playwright 拦截 API 提取直链，优先于 yt-dlp）：

```bash
~/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe ~/.workbuddy-ai/skills/z-video-downloader/scripts/download_video.py \
  --title "抖音主题" \
  "https://www.douyin.com/video/7xxxxxxxxxx"
```

只提取直链不下载（验证 / 手动下载用）：

```bash
~/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe ~/.workbuddy-ai/skills/z-video-downloader/scripts/douyin_playwright.py \
  --url "https://www.douyin.com/video/7xxxxxxxxxx" --extract-only
```

命令行临时调试仍支持 `--browser-cookies chrome`，但网页服务应使用 `--cookies-file`，避免服务进程反复唤起 Chrome/Safari。

YouTube 无 cookie 时若 `yt-dlp` 被登录校验拦截，脚本默认会再尝试 Invidious `local=true` 代理 fallback，优先保存 360p progressive MP4。若明确只允许官方 `yt-dlp` 路线，可加：

```bash
--no-invidious-fallback
```

已提供 cookie 时不会把链接转给第三方代理。

下载播放列表、合集、频道列表时，用户必须明确要整组下载，再加：

```bash
--playlist
```

下载更高清时：

```bash
--quality best
```

默认限制为 1080p，避免无意下载超大文件。用户明确要最高画质时才使用 `--quality best`。

下载中英文字幕并嵌入封面：

```bash
--subtitles --sub-langs "zh.*,en.*" --embed-thumbnail
```

直链中断后复用原目录继续下载：

```bash
~/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe ~/.workbuddy-ai/skills/z-video-downloader/scripts/download_video.py \
  --run-dir "Video/Downloads/原任务目录" \
  "原链接"
```

长期批量任务用下载历史避免重复：

```bash
--download-archive "Video/Downloads/download-archive.txt"
```

## 执行流程

1. 先确认用户给的是视频链接或视频直链；如果是网页素材采集、正文和图片也要保存，改用 `z-web-pack`。
2. 如果链接来自 `z-web-pack` 的 `04-media-inventory.md`，直接传 `--inventory`，无需手工复制 Source URL。
3. 运行 `scripts/download_video.py`。没有特殊要求时使用默认 1080p、单视频模式。抖音链接会自动走 Playwright 抓 API 直链模式；若该模式提取失败且存在 `yt-dlp`，脚本自动回退到 `yt-dlp`。
4. 如果 YouTube 失败原因包含登录、bot 验证、cookies、captcha，脚本会自动尝试 Invidious 代理 fallback；若用户需要更高清或官方登录态，再使用 `--cookies-file cookies/cookies.txt` 重试。
5. 如果 B 站或其他平台失败原因包含 HTTP 412、403、登录或 cookies，使用 `--cookies-file cookies/cookies.txt` 重试一次。
6. 如果用户给的是合集、播放列表、UP 主空间、频道页，先确认用户确实要批量下载，再使用 `--playlist`。
7. 完成后读取 `download-report.md`，最终回复给用户：
   - skill 路径
   - 输出目录
   - 成功/失败数量
   - 下载历史已跳过数量
   - 成功文件名和大小
   - 失败链接的原因与 cookie 重试提示
   - 如果存在 `.part`，说明可以用同一输出目录继续下载

## 平台策略

- mp4/webm/mov/m4v/mkv/flv/ogv 直链：脚本直接流式下载，保留 Referer 和 User-Agent。
- m3u8、YouTube、Bilibili、Vimeo、X/Twitter、TikTok、抖音等：交给 `yt-dlp`。
- **微信视频号**（`https://weixin.qq.com/sph/xxx`）：通过 `sph.litao.workers.dev` 在线解析服务获取 H.264/H.265 视频直链后下载，默认同时保存两个编码版本。无需微信登录态、无需安装证书。感谢 [ltaoo/wx_channels_download](https://github.com/ltaoo/wx_channels_download) 提供解析服务。
- **抖音**（douyin.com / v.douyin.com）：优先用内置 `douyin_playwright.py` —— Playwright 加载视频页并拦截 `aweme/v1/web/aweme/detail` API 响应，从 `aweme_detail.video` 提取带签名的 `douyinvod.com` CDN 直链（优先高码率 `bit_rate[].play_api`，其次 `play_addr`/`download_addr`），再用 `Referer: https://www.douyin.com/` 流式下载（支持 `.part` 断点续传、`--max-video-mb` 限制）。当 Playwright 不可用、API 未捕获或直链下载失败时，自动回退到 `yt-dlp`。直链提取可用 `--extract-only` 单独验证。脚本名建议 `douyin_playwright.py` 的"Playwright 抓 API 直链 → requests 下载"模式可复用于后续任意抖音视频。
- YouTube 直连被登录校验拦截时：尝试 Invidious `local=true` 代理端点，使用 Range 小块续传保存 360p MP4。
- 默认 `--no-playlist`，避免一个链接意外下载整套列表。
- 默认 `--max-video-mb 2000`，超出时失败并记录到报告。
- 默认 `--write-info-json`，保留视频元数据，方便后续追溯来源。
- 平台下载显式启用续传、临时文件、10 次下载重试、10 次分片重试和 4 路分片并发。
- 直链中断时保留 `.part`；使用 `--run-dir` 复用原任务目录会从已保存位置继续，完成后才改成正式视频文件。
- 输入必须是有效的 HTTP/HTTPS 地址；空清单、空白字符、内嵌账号密码、无效地址、缺失 cookie 文件会在创建输出目录前停止。
- `--download-archive` 负责平台视频的历史去重；已在历史中的项目会记为"已跳过"，任务仍算正常完成。

## 收尾检查

下载后至少运行：

```bash
find "Video/Downloads/本次目录" -maxdepth 1 -type f | sort
head -160 "Video/Downloads/本次目录/download-report.md"
find "Video/Downloads/本次目录" -maxdepth 1 -name '*.part' -print
```

## Windows 环境说明

本技能已适配 Windows（WorkBuddy 环境）：
- Python 路径使用 managed Python 3.13，路径在 `~/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe`
- 该 venv 内含 playwright 1.64.1，Chromium 内核（chromium-1248 / chromium_headless_shell-1248）于
  2026-11-09 补装。大陆网络下默认 CDN（cdn.playwright.dev）不可达，装内核必须走镜像：
  `PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright`
- yt-dlp **不在**该 venv 中，实际位于 `C:\Python314\Scripts\yt-dlp.exe`；脚本经 PATH
  （`shutil.which`）与显式候选列表解析，无需重复安装
- ffmpeg 位于 `C:/Program Files/ffmpeg/bin/ffmpeg.exe`
- 脚本中硬编码的 macOS 路径已替换为 Windows 实际路径（本地改动记录见 `LOCAL-PATCHES.md`）

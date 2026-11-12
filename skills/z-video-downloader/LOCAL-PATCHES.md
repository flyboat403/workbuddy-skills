# 本机本地改动记录

本目录是视频下载技能 z-video-downloader 的本地副本。2026-11-09 修复了一组环境漂移问题。
**发布方更新、重装或覆盖安装会丢失这些改动**，届时按下面说明重做。

## 背景

2026-11-02 起陆续发现两处"文档/代码写的路径"与本机实际不符：

1. `scripts/download_video.py` 里 WorkBuddy managed env 路径写的是 `~\.workbuddy\binaries\...`，
   本机实际是 `~\.workbuddy-ai\binaries\...`（带 `-ai` 后缀），导致其中的 yt-dlp 候选路径永远失效，
   全靠 `shutil.which("yt-dlp")` 命中 PATH 才工作。
2. managed env（playwright 1.64.1）缺 Chromium 内核 chromium-1248 / chromium_headless_shell-1248，
   `douyin_playwright.py` 一跑即报 `Executable doesn't exist`；而系统 Python 3.13.12
   （用户级 playwright 1.61.0）用 chromium-1228 反而能跑——两个环境内核版本错位。

## 1. 内核补装（不改文件，本机状态）

- `playwright install chromium`（playwright 1.64.1，managed env），补装：
  `chromium-1248`（437 MB）、`chromium_headless_shell-1248`（278 MB）、`ffmpeg-1013`。
- **大陆网络必须走镜像**：默认 `cdn.playwright.dev` 0% 卡死（197.5 MiB 停 9 分钟），
  设 `PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright` 后 46 秒装完。
- 原 chromium-1228 组保留，供 3.13.12 用户级 playwright 1.61.0 继续使用。

## 2. scripts/download_video.py（2 处）

- `_MANAGED_PYTHON_ENV`：`~\.workbuddy\binaries\python\envs\default` →
  `~\.workbuddy-ai\binaries\python\envs\default`，并加一行注释说明 `-ai` 后缀。
- `YTDLP_CANDIDATES` 末尾追加 `C:\Python314\Scripts\yt-dlp.exe` 显式候选
  （managed env 未装 yt-dlp，本机 yt-dlp 实际在 Python314）。

## 3. scripts/douyin_playwright.py（1 处）

- 模块 docstring「依赖」段：内核号 chromium-1228 → chromium-1248 + headless-shell-1248，
  并注明镜像环境变量（大陆网络下默认 CDN 不可达）。

## 4. SKILL.md（1 处）

- 「Windows 环境说明」：删除「yt-dlp 通过 pip 安装在同一 venv」的错误说法（实际在
  `C:\Python314\Scripts`），补充 playwright 内核版本与镜像安装方法，并指向本文件。

## 重做顺序

先跑内核补装（注意设镜像变量），再依次改 `download_video.py`、`douyin_playwright.py`、`SKILL.md`。

## 附带发现（未入库，备查）

- 抖音 web API 每会话随机分配画质档：同一视频（BV 7706169277024109690）先取到 960×720/293 kbps，
  复测命中 1440×1080/355 kbps。**要最高画质就多解析几次挑最大的**；脚本默认按当次会话的
  bit_rate 降序取最高，不保证跨会话最优。

- **图文作品（note，`aweme_type=68`）无真视频**（2026-11-11，BV 7706496502814107556）：
  detail 接口对 note 返回的 `video.play_addr` 是**纯音轨 mp4**（30s AAC、无视频轨），
  `douyin_playwright.py` 会把它当"视频"成功下载——实为背景音乐。`/note/<id>` 路径触发不了
  detail 接口，**改用 `/video/<id>` 即可**。完整内容在 `aweme_detail.images[].url_list`
  （douyinpic 直链，带签名有时效；webp/jpeg 双格式，`curl -e https://www.douyin.com/` 可下）。
  要还原 App 内播放形态：原图 + 音轨用 ffmpeg `-loop 1 -tune stillimage` 合成即可。
  脚本如需支持 note，应在拿到 detail 后检查 `images` 字段分流处理。

- **知乎视频 yt-dlp 不可用，需有头真浏览器管线**（2026-11-11，zhuanlan p/2103833893174523205）：
  - curl / yt-dlp（generic）/ Edge cookie 导出（app-bound 加密 DPAPI 失败）全部被反爬拦截；
  - Playwright 无头即使抹掉 `navigator.webdriver` 也只过 HTML 挑战，正文 API 仍弹验证码
    （`anticrawl/new_captcha_appeal`）；
  - **可行解：`channel='msedge'` 有头模式** + webdriver 抹除，正文渲染后随滚动触发
    `lens.zhihu.com/api/v4/videos/<id>`，JSON 内含 FHD/HD/SD × avc/hevc 六档
    `vdn3.vzuu.com` 直链，`curl -e https://www.zhihu.com/` 直接下载（auth_key 约 40 分钟有效）。
  - SKILL.md「平台策略」写知乎交给 yt-dlp，实际不可用——遇知乎链接走上述管线。



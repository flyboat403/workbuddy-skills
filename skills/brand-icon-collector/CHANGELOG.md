# 更新日志

## 1.0.0 (2026-11-12)

首个公开版本。

- 三源探测（LobeHub Icons / Simple Icons / svgl）+ 批量抓取，统一导出 512px 透明 PNG 与矢量 SVG（单色 / 官方配色）
- `iconkit.py` 五子命令：probe / fetch / wordmark / sheet / matrix
- 源外搜索升级路径（配套 multi-search-engine 技能），含百度反爬会话与搜狗微信要点
- 官网内联 SVG 提取（`extract_inline_svg.py`）：扫描打分 → 彩色/单色/白色三版派生 → apple-touch-icon → 预览 → manifest
- 自绘文字标识（fontTools 转矢量路径），用于无官方矢量源的产品，规范标注非官方复刻
- 40 组 slug 对照表、版式规范（一览图 / 总览页 / 厂商×模态矩阵）与已验证的坑位清单

# 国内搜索引擎深度搜索指南

本指南覆盖技能内置的 8 个国内搜索引擎，说明各自可用的高级语法、URL 参数与使用示例。
不同引擎对操作符的支持程度不同，标注「部分支持」的语法可能随引擎改版而变化。

## 1. 百度（Baidu）

基础地址：`https://www.baidu.com/s?wd={keyword}`

### 1.1 高级搜索操作符

| 操作符 | 功能 | 示例 |
|--------|------|------|
| `""` | 精确匹配 | `"人工智能"` |
| `-` | 排除关键词 | `苹果 -手机` |
| `\|` | 或运算 | `考研 \| 考公` |
| `site:` | 站内搜索 | `site:zhihu.com 深度学习` |
| `intitle:` | 标题包含 | `intitle:教程 Python` |
| `inurl:` | URL 包含 | `inurl:download 报告` |
| `filetype:` | 限定文件类型 | `filetype:pdf 行业报告` |

> 百度对 `filetype:` 的支持不稳定，常用类型为 `pdf`、`doc`、`xls`、`ppt`、`txt`。
> 组合示例：`site:gov.cn filetype:pdf 十四五 规划`。

### 1.2 时间筛选与分页

| 参数 | 含义 | 示例 |
|------|------|------|
| `gpc=stf=<开始时间戳>,<结束时间戳>\|stftype=2` | 自定义时间范围（Unix 秒） | 见下方示例 |
| `pn=` | 结果页码，每页 10 条 | `pn=10` 表示第 2 页 |
| `rn=` | 每页结果数（最大 50） | `rn=50` |

```text
# 2024 年全年范围
https://www.baidu.com/s?wd=新能源汽车&gpc=stf%3D1704067200%2C1735689600%7Cstftype%3D2

# 第 2 页，每页 50 条
https://www.baidu.com/s?wd=新能源汽车&pn=10&rn=50
```

时间筛选也可在结果页顶部手动选择（一天内 / 一周内 / 一月内 / 一年内）。

### 1.3 高级搜索入口

- 高级搜索页：`https://www.baidu.com/gaoji/advanced.html`
- 图片搜索：`https://image.baidu.com/search/index?tn=baiduimage&word={keyword}`
- 新闻搜索：`https://news.baidu.com/ns?word={keyword}`
- 学术搜索：`https://xueshu.baidu.com/s?wd={keyword}`

## 2. 必应中国（Bing CN）

基础地址：`https://cn.bing.com/search?q={keyword}&ensearch=0`

### 2.1 高级搜索操作符

| 操作符 | 功能 | 示例 |
|--------|------|------|
| `""` | 精确匹配 | `"large language model"` |
| `-` | 排除关键词 | `python -snake` |
| `OR` / `\|` | 或运算 | `cat OR dog` |
| `site:` | 站内搜索 | `site:github.com react` |
| `filetype:` | 文件类型 | `filetype:pdf annual report` |
| `intitle:` | 标题包含 | `intitle:release notes` |
| `inurl:` | URL 包含 | `inurl:login admin` |

### 2.2 时间筛选参数

| 参数 | 含义 |
|------|------|
| `qft=+filterui:age-lt1440` | 过去 24 小时 |
| `qft=+filterui:age-lt10080` | 过去 7 天 |
| `qft=+filterui:age-lt43200` | 过去 30 天 |
| `qft=+filterui:age-lt525600` | 过去 1 年 |

```text
https://cn.bing.com/search?q=AI+news&qft=+filterui:age-lt10080&ensearch=0
```

### 2.3 地区与语言

| 参数 | 含义 | 示例 |
|------|------|------|
| `ensearch=0` | 中国版结果 | 默认 |
| `ensearch=1` | 国际版结果 | `ensearch=1` |
| `setlang=zh-Hans` | 界面语言 | `setlang=zh-Hans` |
| `cc=cn` | 国家/地区 | `cc=cn` |

### 2.4 其他搜索类型

| 类型 | URL |
|------|-----|
| 图片 | `https://cn.bing.com/images/search?q={keyword}` |
| 新闻 | `https://cn.bing.com/news/search?q={keyword}` |
| 视频 | `https://cn.bing.com/videos/search?q={keyword}` |
| 学术 | `https://cn.bing.com/academic/search?q={keyword}` |

## 3. 360 搜索（So.com）

基础地址：`https://www.so.com/s?q={keyword}`

### 3.1 高级搜索操作符

| 操作符 | 功能 | 示例 |
|--------|------|------|
| `""` | 精确匹配 | `"量化交易"` |
| `-` | 排除关键词 | `Python -蛇` |
| `site:` | 站内搜索 | `site:csdn.net 微服务` |
| `filetype:` | 文件类型 | `filetype:pdf 白皮书` |
| `intitle:` | 标题包含 | `intitle:教程 Docker` |
| `inurl:` | URL 包含 | `inurl:api 文档` |

### 3.2 常用参数

| 参数 | 含义 | 示例 |
|------|------|------|
| `pn=` | 结果页码（每页 10 条） | `pn=2` |
| `src=` | 来源标识 | `src=srp` |

```text
https://www.so.com/s?q=site%3Acsdn.net+%E5%BE%AE%E6%9C%8D%E5%8A%A1&pn=2
```

> 360 的时间筛选主要在结果页交互完成，URL 参数随版本调整，建议需要时间过滤时改用 Bing 或百度。

## 4. 搜狗（Sogou）

基础地址：`https://sogou.com/web?query={keyword}`

### 4.1 高级搜索操作符（部分支持）

| 操作符 | 功能 | 示例 |
|--------|------|------|
| `""` | 精确匹配 | `"碳中和"` |
| `-` | 排除关键词 | `芯片 -股票` |
| `site:` | 站内搜索 | `site:mp.weixin.qq.com 大模型` |
| `filetype:` | 文件类型 | `filetype:pdf 研究报告` |

### 4.2 常用参数

| 参数 | 含义 | 示例 |
|------|------|------|
| `page=` | 结果页码 | `page=2` |
| `ie=utf8` | 输入编码 | `ie=utf8` |

> 搜狗对 `intitle:`、`inurl:` 的支持较弱，站点限定优先使用 `site:`。

## 5. 微信搜索（搜狗微信）

基础地址：`https://wx.sogou.com/weixin?type=2&query={keyword}`

| 参数 | 含义 |
|------|------|
| `type=2` | 搜索文章 |
| `type=1` | 搜索公众号 |

### 使用示例

```text
# 搜索公众号文章
https://wx.sogou.com/weixin?type=2&query=大模型+应用

# 搜索公众号
https://wx.sogou.com/weixin?type=1&query=机器之心

# 限定时间（部分版本可用）
https://wx.sogou.com/weixin?type=2&query=AI&tsn=1
```

> `tsn` 取值通常为 1=一天内、2=一周内、3=一月内，但可能随版本失效；失效时请在结果页手动筛选。

## 6. 头条搜索（Toutiao）

基础地址：`https://so.toutiao.com/search?keyword={keyword}`

| 参数 | 含义 | 示例 |
|------|------|------|
| `pd=synthesis` | 综合搜索 | 默认 |
| `pd=information` | 资讯搜索 | `pd=information` |
| `pd=video` | 视频搜索 | `pd=video` |
| `dvpf=pc` | PC 端结果页 | 默认 |

> 头条搜索对 `site:`、`filetype:` 等传统操作符支持有限，更适合按内容类型（资讯 / 视频 / 问答）检索。

## 7. 集思录（Jisilu）

基础地址：`https://www.jisilu.cn/explore/?keyword={keyword}`

- 面向可转债、债券、基金等投资数据的垂直社区。
- 适合检索：可转债条款、溢价率讨论、套利策略、打新与配债经验。
- 站内搜索对通用操作符支持有限，建议使用精确关键词，例如：
  - `可转债 强赎`
  - `套利 溢价率`
  - `REITs 分红`

```text
https://www.jisilu.cn/explore/?keyword=%E5%8F%AF%E8%BD%AC%E5%80%BA%20%E5%BC%BA%E8%B5%8E
```

## 8. 跨引擎使用建议

| 场景 | 推荐引擎 | 理由 |
|------|----------|------|
| 中文资料、政策文件 | 百度 / 必应中国 | 中文索引全，支持 `site:`、`filetype:` |
| 技术文档、开源项目 | 必应国际版 / Google | 英文索引质量高 |
| 微信公众号文章 | 搜狗微信 | 唯一可检索公众号内容的入口 |
| 热点资讯 | 头条搜索 / 百度资讯 | 时效性强 |
| 投资与可转债 | 集思录 | 垂直数据与社区讨论 |
| 结果交叉验证 | 至少 2 个引擎 | 降低单一引擎的排序偏差 |

### 编码与拼接

- 中文关键词建议 URL 编码（UTF-8），例如 `大模型` → `%E5%A4%A7%E6%A8%A1%E5%9E%8B`。
- 空格可用 `+` 或 `%20`；`site:` 等操作符中的冒号建议编码为 `%3A`，避免被部分引擎截断。
- 多引擎检索时先去重（按 URL 归一化），再按来源可信度排序。

### 批量检索示例

```javascript
// 同一关键词并行检索三个引擎
web_fetch({"url": "https://www.baidu.com/s?wd=%E5%A4%A7%E6%A8%A1%E5%9E%8B"})
web_fetch({"url": "https://cn.bing.com/search?q=%E5%A4%A7%E6%A8%A1%E5%9E%8B&ensearch=0"})
web_fetch({"url": "https://www.so.com/s?q=%E5%A4%A7%E6%A8%A1%E5%9E%8B"})

// 站内 + 文件类型
web_fetch({"url": "https://cn.bing.com/search?q=site%3Agov.cn+filetype%3Apdf+%E5%8F%8C%E7%A2%B3"})
```

## 9. 已知限制

- 各引擎可能对高频请求返回验证码或空结果，建议控制频率并在失败时切换引擎。
- `filetype:`、`intitle:`、`inurl:` 属于「部分支持」，结果可能被放宽。
- 时间筛选参数随引擎改版变化，文档给出的是当前常用形式。
- 本指南只覆盖国内引擎；国际引擎见 `references/international-search.md`。

# CNKI 浏览器搜索参考

通过 Camofox 浏览器向 CNKI 页面注入 JavaScript，完成搜索和数据提取。

## 核心设计原则

### 1. 单次 eval 完成搜索+提取

所有操作通过单次异步 JS 脚本（`browser_console` 注入）完成，取代多步的 navigate→snapshot→click→wait_for：

```
1. 导航到 CNKI 搜索页（navigate）
2. 注入 JS（browser_console）：等待输入框 → 检测验证码 → 填写关键词 → 提交 → 等待结果 → 提取
3. 返回结构化数据
```

### 2. 导航替代点击

CNKI 的链接打开新标签页。直接用 `navigate_page(URL)` 跳转，而不是 `click()`，避免标签页管理。

### 3. 批量导出

从搜索结果页直接选多篇导出到 Zotero，不逐篇进详情页。

---

## 基础搜索（kns8s 新界面）

**搜索 URL**：`https://kns.cnki.net/kns8s/search`

### 已验证的 CSS 选择器

| 元素 | 选择器 | 备注 |
|------|--------|------|
| 搜索输入框 | `input.search-input` | id=`txt_search`，placeholder "中文文献、外文文献" |
| 搜索按钮 | `input.search-btn` | type="button" |
| 结果总数 | `.pagerTitleCell` | 文本 "共找到 X 条结果" |
| 页码指示 | `.countPageMark` | 文本 "1/300" |
| 结果行 | `.result-table-list tbody tr` | 每行一篇论文 |
| 标题链接 | `td.name a.fz14` | 含 href（论文详情页 URL） |
| 作者 | `td.author a.KnowledgeNetLink` | 作者名链接，可能有多个 |
| 期刊 | `td.source a` | 来源期刊链接 |
| 日期 | `td.date` | 发表日期文本 |
| 引用数 | `td.quote` | 被引次数 |
| 下载数 | `td.download` | 下载次数 |
| 导出 ID | `input.cbItem` | checkbox 的 value（用于批量导出到 Zotero） |

### JS 搜索脚本

完整实现见 `scripts/cnki-search.js`。核心逻辑：

```javascript
async () => {
  const query = "YOUR_KEYWORDS";

  // 1. 等待搜索输入框加载
  await new Promise((r, j) => {
    let n = 0;
    const c = () => {
      if (document.querySelector('input.search-input')) r();
      else if (++n > 30) j('timeout');
      else setTimeout(c, 500);
    };
    c();
  });

  // 2. 检测验证码
  const cap = document.querySelector('#tcaptcha_transform_dy');
  if (cap && cap.getBoundingClientRect().top >= 0) return { error: 'captcha' };

  // 3. 填写并提交
  const input = document.querySelector('input.search-input');
  input.value = query;
  input.dispatchEvent(new Event('input', { bubbles: true }));
  document.querySelector('input.search-btn')?.click();

  // 4. 等待结果加载
  await new Promise((r, j) => {
    let n = 0;
    const c = () => {
      if (document.body.innerText.includes('条结果')) r();
      else if (++n > 30) j('timeout');
      else setTimeout(c, 500);
    };
    c();
  });

  // 5. 再次检测验证码
  const cap2 = document.querySelector('#tcaptcha_transform_dy');
  if (cap2 && cap2.getBoundingClientRect().top >= 0) return { error: 'captcha' };

  // 6. 提取结构化数据
  const rows = document.querySelectorAll('.result-table-list tbody tr');
  const results = Array.from(rows).map((row, i) => ({
    n: i + 1,
    title: row.querySelector('td.name a.fz14')?.innerText?.trim() || '',
    href: row.querySelector('td.name a.fz14')?.href || '',
    authors: Array.from(row.querySelectorAll('td.author a.KnowledgeNetLink'))
      .map(a => a.innerText?.trim()).join('; '),
    journal: row.querySelector('td.source a')?.innerText?.trim() || '',
    date: row.querySelector('td.date')?.innerText?.trim() || '',
    citations: row.querySelector('td.quote')?.innerText?.trim() || '',
    downloads: row.querySelector('td.download')?.innerText?.trim() || '',
    exportId: document.querySelectorAll('input.cbItem')[i]?.value || ''
  }));

  return {
    query,
    total: document.querySelector('.pagerTitleCell')
      ?.innerText?.match(/([\d,]+)/)?.[1] || '0',
    page: document.querySelector('.countPageMark')?.innerText || '1/1',
    results
  };
}
```

---

## 高级检索（kns 旧界面）

**重要**：高级检索中的来源类型复选框（SCI、EI、北大核心、CSSCI、CSCD）只在**旧版搜索界面**存在。新版 kns8s 无此功能。

**URL**：`https://kns.cnki.net/kns/AdvSearch?classid=7NS01R8M`

### 表单字段映射

| 字段 | 选择器/索引 | 值/备注 |
|------|-------------|---------|
| 行1 字段类型 | `selects[0]` | SU=主题, TI=篇名, KY=关键词, TKA=篇关摘, AB=摘要 |
| 行1 关键词 | `#txt_1_value1` | 主关键词输入框 |
| 行1 行内第二词 | `#txt_1_value2` | 同一行第二个关键词 |
| 行1 行内逻辑 | `selects[2]` | AND=并含, OR=或含, NOT=不含 |
| 行间逻辑 | `selects[5]` | AND=并且, OR=或者, NOT=不含 |
| 行2 字段类型 | `selects[6]` | 同上 |
| 行2 关键词 | `#txt_2_value1` | 第二行关键词 |
| 作者 | `#au_1_value1` | placeholder "中文名/英文名/拼音" |
| 作者单位 | `#au_1_value2` | |
| 文献来源 | `#magazine_value1` | placeholder "期刊名称/ISSN/CN" |
| 基金 | `#base_value1` | |
| 起始年 | `selects[14]` / `#startYear` | `<select>` 1915-2026 |
| 结束年 | `selects[15]` / `#endYear` | |
| 检索按钮 | `div.search` | 不是 input/button |

### 来源类型复选框

| 来源 | 复选框 ID | 说明 |
|------|-----------|------|
| 全部期刊 | `#gjAll` | 默认勾选，选其他前需取消 |
| SCI 来源期刊 | `#SCI` | |
| EI 来源期刊 | `#EI` | |
| 北大核心期刊 | `#hx` | |
| CSSCI | `#CSSCI` | **最常用** |
| CSCD | `#CSCD` | |

多个来源可同时勾选（OR 逻辑）。

### 高级检索 JS 脚本

```javascript
async () => {
  const query = "KEYWORDS";            // 主题关键词
  const sourceTypes = ["CSSCI"];       // 来源类型：SCI, EI, hx, CSSCI, CSCD
  const startYear = "2020";            // 起始年
  const endYear = "2025";              // 结束年
  const author = "";                   // 作者（可选）
  const journal = "";                  // 期刊（可选）

  // 1. 等待表单加载
  await new Promise((r, j) => {
    let n = 0;
    const c = () => {
      if (document.querySelector('#txt_1_value1')) r();
      else if (++n > 30) j('timeout');
      else setTimeout(c, 500);
    };
    c();
  });

  // 2. 检测验证码
  const cap = document.querySelector('#tcaptcha_transform_dy');
  if (cap && cap.getBoundingClientRect().top >= 0) return { error: 'captcha' };

  const selects = Array.from(document.querySelectorAll('select'))
    .filter(s => s.offsetParent !== null);

  // 3. 设置来源类型
  if (sourceTypes.length > 0) {
    const gjAll = document.querySelector('#gjAll');
    if (gjAll && gjAll.checked) gjAll.click();
    for (const st of sourceTypes) {
      const cb = document.querySelector('#' + st);
      if (cb && !cb.checked) cb.click();
    }
  }

  // 4. 设置检索条件
  selects[0].value = "SU";
  selects[0].dispatchEvent(new Event('change', { bubbles: true }));
  document.querySelector('#txt_1_value1').value = query;

  // 5. 作者（可选）
  if (author) {
    const auInput = document.querySelector('#au_1_value1');
    if (auInput) { auInput.value = author; }
  }

  // 6. 期刊（可选）
  if (journal) {
    const magInput = document.querySelector('#magazine_value1');
    if (magInput) { magInput.value = journal; }
  }

  // 7. 时间范围（可选）
  if (startYear) { selects[14].value = startYear; selects[14].dispatchEvent(new Event('change', { bubbles: true })); }
  if (endYear) { selects[15].value = endYear; selects[15].dispatchEvent(new Event('change', { bubbles: true })); }

  // 8. 提交检索
  document.querySelector('div.search')?.click();

  // 9. 等待结果
  await new Promise((r, j) => {
    let n = 0;
    const c = () => {
      if (document.body.innerText.includes('条结果')) r();
      else if (++n > 40) j('timeout');
      else setTimeout(c, 500);
    };
    setTimeout(c, 2000);
  });

  const cap2 = document.querySelector('#tcaptcha_transform_dy');
  if (cap2 && cap2.getBoundingClientRect().top >= 0) return { error: 'captcha' };

  return {
    query, sourceTypes, startYear, endYear, author, journal,
    total: document.querySelector('.pagerTitleCell')
      ?.innerText?.match(/([\d,]+)/)?.[1] || '0',
    page: document.querySelector('.countPageMark')?.innerText || '1/1',
    url: location.href
  };
}
```

---

## 论文详情页提取

**URL**：搜索结果中的 `href` 字段

### 字段选择器

| 字段 | 选择器 |
|------|--------|
| 标题 | `h1#title` |
| 作者 | `.author > span > a` |
| 机构 | `.author > p` |
| 摘要 | `#abstractContent > p` |
| 关键词 | `#catalog_KEYWORD > p > span > a` |
| 基金 | `#fundProjectContent` |
| 分类号 | `#catalog_CLC > p` |
| DOI | `#doiNumber` |

### 提取 JS

```javascript
async () => {
  await new Promise((r, j) => {
    let n = 0;
    const c = () => {
      if (document.querySelector('h1#title')) r();
      else if (++n > 20) j('timeout');
      else setTimeout(c, 500);
    };
    c();
  });

  return {
    title: document.querySelector('h1#title')?.innerText?.trim() || '',
    authors: Array.from(document.querySelectorAll('.author > span > a'))
      .map(a => a.innerText?.trim()).join('; '),
    affiliations: Array.from(document.querySelectorAll('.author > p'))
      .map(p => p.innerText?.trim()).join('; '),
    abstract: document.querySelector('#abstractContent > p')?.innerText?.trim() || '',
    keywords: Array.from(document.querySelectorAll('#catalog_KEYWORD > p > span > a'))
      .map(a => a.innerText?.trim()).join('; '),
    fund: document.querySelector('#fundProjectContent')?.innerText?.trim() || '',
    doi: document.querySelector('#doiNumber')?.innerText?.trim() || '',
    clc: Array.from(document.querySelectorAll('#catalog_CLC > p'))
      .map(p => p.innerText?.trim()).join('; ')
  };
}
```

---

## 验证码检测（关键）

CNKI 使用腾讯滑块验证码（`#tcaptcha_transform_dy`），**不可编程解决**。

```javascript
// 检测验证码是否真正挡住用户
function isCaptchaActive() {
  const cap = document.querySelector('#tcaptcha_transform_dy');
  // SDK 预加载时 DOM 在屏幕外 (top: -1000000px)
  // 只有 getBoundingClientRect().top >= 0 才表示真正可见
  return cap && cap.getBoundingClientRect().top >= 0;
}
```

**策略**：检测到 → 暂停 → 输出消息"CNKI 正在显示滑块验证码，请在 Chrome 中手动完成拼图验证，完成后告诉我继续" → 等用户确认 → 重试。

---

## 分页导航

搜索结果页的分页和排序：

```javascript
// 翻页
document.querySelector('.page-next')?.click();       // 下一页
document.querySelector('.page-prev')?.click();       // 上一页
document.querySelector('.page-skip')?.click();       // 跳转到输入框中的页码

// 排序
// 选项：发表时间、相关度、被引、下载
document.querySelector('select.sort-select')?.value = 'date';  // 按时间排序
document.querySelector('select.sort-select')?.dispatchEvent(new Event('change', { bubbles: true }));
```

---

## Zotero 批量导出

从搜索结果页直接导出，不逐篇进详情页：

1. 选中要导出的论文（勾选 `input.cbItem`）
2. 点击页面上的「导出/参考文献」按钮
3. 选择 RIS 格式
4. 下载 .ris 文件
5. 导入 Zotero

```javascript
// 选中前 N 篇
document.querySelectorAll('input.cbItem').forEach((cb, i) => {
  if (i < 10) cb.checked = true;
});
// 点击导出按钮
document.querySelector('a.export-btn')?.click();
```

---

## 来源

本参考的 CSS 选择器和搜索逻辑来自 cookjohn/cnki-skills（MIT 协议），经 Hermes Agent 环境适配。

// CNKI 浏览器搜索 JS 注入脚本
// 使用方式：通过 browser_console(expression=...) 注入
// 使用时替换 YOUR_KEYWORDS 为实际搜索词

const cnkiSearch = async (query) => {
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

  // 2. 检测验证码（腾讯滑块）
  const cap = document.querySelector('#tcaptcha_transform_dy');
  if (cap && cap.getBoundingClientRect().top >= 0) {
    return { error: 'captcha' };
  }

  // 3. 填写搜索关键词
  const input = document.querySelector('input.search-input');
  input.value = query;
  input.dispatchEvent(new Event('input', { bubbles: true }));

  // 4. 点击搜索按钮
  document.querySelector('input.search-btn')?.click();

  // 5. 等待搜索结果加载（最多 15 秒）
  await new Promise((r, j) => {
    let n = 0;
    const c = () => {
      if (document.body.innerText.includes('条结果')) r();
      else if (++n > 30) j('timeout');
      else setTimeout(c, 500);
    };
    c();
  });

  // 6. 再次检测验证码
  const cap2 = document.querySelector('#tcaptcha_transform_dy');
  if (cap2 && cap2.getBoundingClientRect().top >= 0) {
    return { error: 'captcha' };
  }

  // 7. 提取结构化结果
  const rows = document.querySelectorAll('.result-table-list tbody tr');
  const checkboxes = document.querySelectorAll('.result-table-list tbody input.cbItem');
  const results = Array.from(rows).map((row, i) => {
    const titleLink = row.querySelector('td.name a.fz14');
    const authors = Array.from(
      row.querySelectorAll('td.author a.KnowledgeNetLink') || []
    ).map(a => a.innerText?.trim());
    return {
      n: i + 1,
      title: titleLink?.innerText?.trim() || '',
      href: titleLink?.href || '',
      exportId: checkboxes[i]?.value || '',
      authors: authors.join('; '),
      journal: row.querySelector('td.source a')?.innerText?.trim() || '',
      date: row.querySelector('td.date')?.innerText?.trim() || '',
      citations: row.querySelector('td.quote')?.innerText?.trim() || '',
      downloads: row.querySelector('td.download')?.innerText?.trim() || ''
    };
  });

  return {
    query,
    total: document.querySelector('.pagerTitleCell')
      ?.innerText?.match(/([\d,]+)/)?.[1] || '0',
    page: document.querySelector('.countPageMark')?.innerText || '1/1',
    results
  };
};

// 使用示例（在 browser_console 中调用）：
// await cnkiSearch('数字经济');

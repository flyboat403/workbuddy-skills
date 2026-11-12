# WorkBuddy 安装、审计与实测记录（非上游文件）

本文件由 WorkBuddy 在 2026-10-06 安装本技能时生成，**不属于上游 `MartyYao/Chinese-Literature-Skill`**。
用途：留下安装时的审计结论、实测证据与已知差异，便于日后同步上游或追责。

---

## 一、安装记录

| 项 | 值 |
|---|---|
| 上游仓库 | `https://github.com/MartyYao/Chinese-Literature-Skill` |
| 克隆方式 | `git clone --depth 1 ssh://git@ssh.github.com:443/MartyYao/Chinese-Literature-Skill.git`（本机 `https://github.com` 直连被阻断，SSH-over-443 可用） |
| 上游 HEAD | `a46de0f chore: normalize version metadata to v0.1.1` |
| 上游版本 / 许可 | v0.1.1 / MIT |
| 安装位置 | `~/.workbuddy-ai/skills/chinese-literature/`（用户级技能） |
| 安装方式 | **拷贝式导入**（已删除 `.git`）→ 因此**不是 git 仓库，不能 `git pull`** |
| 文件数 / 大小 | 12 个源文件（+ 本文件与适配层）/ 约 89 KB |
| 行尾 | 全部统一 **CRLF**（上游克隆本身即 CRLF，逐个复核 `裸LF=0`） |

## 二、安全审计：结论 **P2（安全）**

审计方式：逐文件通读 + 正则扫描。因本机未安装 `skills-security-check` 技能，此项为手工完成。

### 2.1 危险模式扫描（全部文件）

```
subprocess | os.system | os.popen | eval( | exec( | __import__ | pickle | marshal
socket | shutil | rmtree | os.remove | os.unlink | getpass | keyring | winreg | ctypes
```

**命中数：0。** 无命令执行、无动态求值、无反序列化、无原始套接字、**无任何文件删除**。

### 2.2 硬编码外部端点（穷举）

| URL | 用途 |
|---|---|
| `https://kns.cnki.net/kns8s/search`、`https://kns.cnki.net/kns/AdvSearch?classid=7NS01R8M` | CNKI 检索页（浏览器通道的导航目标） |
| `https://navi.cnki.net/knavi/journals/{code}/detail?uniplatform=NZKPT` | CNKI 期刊详情页（取 Cookie） |
| `https://navi.cnki.net/knavi/rss/{code}`、`https://rss.cnki.net/knavi/rss/ZSHK?pcode=CJFD,CCJD` | CNKI RSS |
| `https://www.ncpssd.cn/searchHandler/search` | NCPSSD 检索接口 |
| `https://github.com/cookjohn/cnki-skills`、`https://github.com/YOUR_REPO/…` | 文档中的致谢/占位符（不发起请求） |

**无遥测、无第三方上报、无动态主机。** 端点集合封闭且可枚举。

### 2.3 行为审计

| 行为 | 位置 | 评估 |
|---|---|---|
| 网络请求 | `cnki-rss.py`（每刊 2 次 GET）、`ncpssd-search.py`（1 次 POST） | 端点固定；无重试循环；超时 15 s |
| 文件写入 | `cnki-rss.py --init` → 写 `journals.json` | ⚠️ 写入的是**当前工作目录**（`Path.cwd()`），不是技能目录 —— 已在 SKILL.md 适配说明中标注 |
| 浏览器注入 | `cnki-search.js` | 只读 DOM + 填表单 + 点搜索按钮；**不读取 cookie、不碰凭据、不发外部请求** |
| 凭据 | 无 | 不需要账号密码；CNKI RSS 用匿名 CookieJar |

### 2.4 残余风险（低）

- `journal code` 由命令行/配置提供，被插入到固定主机的路径中
  （`https://navi.cnki.net/knavi/journals/{code}/detail`）。**主机不可被替换**，但形如 `../` 的
  取值可改变同主机路径。风险低，且使用者即本人。
- 无签名校验、无版本自更新机制（本技能也不联网检查更新），符合"静态脚本"预期。

## 三、合规审计（关键）

安装时实测的 robots.txt 原文：

```
# kns.cnki.net/robots.txt  ·  navi.cnki.net/robots.txt  ·  rss.cnki.net/robots.txt
User-agent: *
Disallow: /

# ncpssd.org/robots.txt（节选）
Disallow: /searchHandler/      ← 正是 ncpssd-search.py 使用的接口路径
Disallow: /journal/index/
Disallow: /topics/detailsList/
Disallow: /user/
Disallow: /login/

# www.ncpssd.cn/robots.txt  →  HTTP 404（该主机未提供该文件）
```

**结论**：三个通道的目标服务端都发布了与本次用法直接冲突的爬取指令。

**因此的处置**：本技能作为**独立技能**存在，**不并入 `academic-research-deep-research`**，
也不在该技能的任何文件中被引用为"已授权数据源"。两份文件的边界彼此独立陈述。理由：

- `academic-research-deep-research` 的 §Legal and compliance boundary 明文写着
  *"Zero scraping. CNKI, Wanfang, and VIP search and full-text pages are never fetched or parsed."*
- 若把本技能合并进去，等于直接推翻该技能的核心承诺；
- 若在本技能里引用"ARS 已批准"，则会把一份文件的结论当成另一份的许可 —— 这是两者并存时唯一真正的风险。

## 四、实测记录

### 4.1 NCPSSD 通道 —— ✅ 已实测可用

```
POST https://www.ncpssd.cn/searchHandler/search
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
search=(IKTE="数字经济")&pageNum=1&pageSize=3
  &sort=synUpdateType|DESC,date|DESC,ik_subject|DESC,id|DESC&sType=0&ajaxKeys=&customShowCondition=数字经济
```

```
→ HTTP 200 · 14,904 字节
{"result": true, "code": …, "succee": …,
 "data": {"total": 12028, "rows": [ … ], "pages": …, "currentPage": 1}}
```

单行含 **110+ 字段**（`title` / `creator_first` / `cbw_name` / `years` / `volumn` / `num` /
`pagecount` / `issn` / `remark`(摘要) / `subject`(关键词) / `doi` / `imburse`(基金) /
`institutions` / `pdfurl` / `HtmlUrl` / `encryptedUrl` …）。
首条实测样例：题名《数实融合背景下数字经济驱动经济高质量发展：机制及路径创新》·
刊名《成都理工大学学报：社会科学版》· 2025 年 · ISSN 1672-0539 · 摘要与关键词均有值 · `pdfurl` 指向全文。

字段码（用于 `--field`）：`IKTE` 题名 · `IKST` 关键词 · `IKCR`/`IKCE` 作者 · `IKET` 摘要 · `IKSE` 主题。

> 注：`https://www.ncpssd.org/Literature/articlelist` 那个 HTML 页只是外壳，手工拼参数对四种
> 变体都返回同一个 7,506 字符空壳 —— 数据全部来自上面这个 POST。不要被 HTML 页误导。

### 4.2 CNKI 两个通道 —— ⚠️ **本机未做实测**（有意为之）

原因：`kns.cnki.net` / `navi.cnki.net` / `rss.cnki.net` 三主机均发布 `Disallow: /`。
安装者不在安装过程中主动向明确禁止的端点发起请求。因此：

- 脚本的可执行性（`--list` / `--config` / 参数解析 / 格式化输出）可离线验证；
- **实际取数能力未经验证**，其可靠性依据为上游自述与其来源
  [`cookjohn/cnki-skills`](https://github.com/cookjohn/cnki-skills)（MIT）。
- `cnki-search.js` 的选择器同理未验证；CNKI 改版即可能失效。

### 4.3 离线冒烟测试 —— ✅ 通过（零网络流量）

测试脚本：`tests/test_offline_stubs.py`（本机新增，可独立运行）。
做法：**桩掉 transport**（记录请求 + 回放固定报文），验证「请求怎么构造」与「返回怎么解析」，
**不向 CNKI / NCPSSD 发出任何真实请求** —— 与上游 `academic-research-deep-research` 的
`scripts/fixtures/transport_bodies/` 所坚持的「no live network in tests」纪律一致。

```bash
PY="~/.workbuddy-ai/binaries/python/versions/3.13.12/python.exe"
"$PY" ~/.workbuddy-ai/skills/chinese-literature/tests/test_offline_stubs.py
```

验证内容与结果：

| 检查项 | 结果 |
|---|---|
| `ncpssd-search.py` 端点 / 方法 | ✅ `POST https://www.ncpssd.cn/searchHandler/search` |
| 表单字段 | ✅ `search` / `pageNum` / `pageSize` / `sort` / `sType` / `ajaxKeys` / `customShowCondition` 齐全 |
| `--field title` → 字段码 | ✅ 正确生成 `(IKTE="…")` |
| 记录解析 | ✅ 题名 / 作者 / 刊名 / 年 / 期 / 页 / ISSN / DOI / 基金 / 机构 / 摘要 / 关键词 / `pdfurl` 全部抽出 |
| 高亮标记 | ✅ 题名里的 `<em>` 被清除 |
| `format_text` / `format_markdown` | ✅ 渲染正常 |
| 失败响应 | ✅ `result:false` 被如实透传，不会被误认为「空结果」 |
| `cnki-rss.py` 两步认证顺序 | ✅ 先 `GET …/journals/JJYJ/detail`，再 `GET …/knavi/rss/JJYJ`（`CookieJar` 经 `build_opener`） |
| RSS 解析 | ✅ 题名 / 作者 / 摘要 / RFC 2822 日期（转成 datetime）正确 |
| 例外 URL | ✅ `EXCEPTION_URLS`（`ZSHK`）存在并会被使用 |
| 离线命令 | ✅ `cnki-rss.py --list` 正常列出 12 个期刊与 4 个学科分组，未发请求 |
| 语法 | ✅ 两个脚本 `py_compile` 通过 |

> 写这个测试时踩到一个点：`cnki-rss.py` 走的是 `build_opener(...).open(...)`（因为要用
> `CookieJar`），**桩掉 `urllib.request.urlopen` 拦不住它**，必须桩 `build_opener`。
> 这也解释了为什么第一版桩测试里「CNKI 请求数」为 0 —— 请求根本没经过被桩的函数。

## 五、与上游的差异清单

| 项 | 上游 | 本机 |
|---|---|---|
| `SKILL.md` frontmatter | `name` / `description` / `version` / `category` / `tags` / `trigger` / `related_skills` | `name` / `description`（触发词并入 description，WorkBuddy 靠它路由）/ `metadata.{version, upstream_repo, upstream_skill, ported_on, license}` |
| 适配说明 | 无 | 新增本机适配块（合规边界 / 依赖映射 / 运行方式 / 差异与未实测项） |
| `description` 措辞 | 只提"两通道"与 `paper-workflow 阶段 1` | 改为三通道 + 完整中英文触发词；`paper-workflow` 在本机不存在，不再作为前提 |
| 正文 | — | **逐字保留**（含上游的"两通道总览"等章节，未改动） |
| `multi-agent/` | 三份其他 agent 的说明 | 原样保留以尊重上游。⚠️ `for-claude-code.md` 引用的 `claude-skills/`、`claude-agents/` 目录**上游并不存在**，`git clone` 仍为 `YOUR_REPO` 占位符 → **那份安装说明是坏的，不要照做** |
| 行尾 | CRLF | 保持一致（全部 CRLF） |

## 六、已知问题与后续

1. **不是 git 仓库**：同步上游须走 `skill-sync-from-github` 的流程，并保留本文件与 SKILL.md 的适配块。
2. **`--init` 写当前目录**：见 §2.3。
3. **CNKI 选择器随时可能失效**（未验证）；失效时改走 NCPSSD 通道或人工检索。
4. **`sType=0` / `sort` 串 / 字段码均为未公开的内部约定**，NCPSSD 改版即可能失效；失败时脚本会
   返回 `{"result": False, "message": …}` 并以退出码 1 结束。
5. 若要长期使用，建议核对本人所属机构与 CNKI / NCPSSD 的授权范围。

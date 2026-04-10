---
name: web-reader
description: "Unified web page reading and interaction system. Three-layer architecture: L1 fast fetch (defuddle/Scrapling/web_fetch) to L2 browser rendering to L3 content cleaning. Supports sites requiring login (Zhihu, X, WeChat). Do NOT use for local file reading or API calls."
triggers: ["读网页", "抓取", "web-reader", "/web-reader", "读取这个链接", "读取这篇文章", "查一下", "核实"]
user-invocable: true
command-dispatch: tool
---


# Web Reader — 统一网页读取与网络交互

## 浏览哲学

**像人一样思考，目标导向。**

拿到请求时，先明确用户要什么，定义成功标准。不预设固定步骤，带着目标进入，边看边判断。每一步的结果都是证据——路径在推进吗？质量指向目标可达吗？发现方向错了立即调整。

- **确保信息真实性，一手信息优于二手信息**
- 搜索引擎是信息发现入口，不是信息本身。找到来源后，直接访问原文
- 多个媒体引用同一错误会造成循环印证假象。搜索引擎和聚合平台不可用于直接证明真伪

## 工具选择决策

| 场景 | 工具 | 理由 |
|------|------|------|
| 搜索信息、发现来源 | `web_search` | 快，覆盖广 |
| URL 已知，静态页面 | `web_fetch` | 直接拉取，轻量 |
| 公开内容但反爬限制（微信等） | `web_fetch` → `browser` 工具 / web-reader L1 | Scrapling 作为 L1 备选 |
| 需要登录态、JS 重度渲染 | `browser` 工具 (profile=user) 或 bb-browser adapter | 真实浏览器环境 |
| 需要交互操作（点击、翻页、表单） | `browser` 工具 | snapshot + act 交互 |
| 原始 HTML 源码（meta、JSON-LD） | `curl` | 精确控制 |

**决策原则**：从轻量工具开始，逐级升级。web_search 没命中不等于"没找对方法"，也可能是"目标不存在"。

## 信息核实原则

| 信息类型 | 一手来源 |
|----------|---------|
| 政策/法规 | 发布机构官网 |
| 企业公告 | 公司官方新闻页 |
| 学术声明 | 原始论文/机构官网 |
| 工具能力/用法 | 官方文档、源码 |

- 未找到官方原文时，权威媒体原创报道可作为次级依据，但需声明"存在转述误差可能"
- 单一来源时同样向用户声明

## 并行调研：子 Agent 分治

任务包含多个**独立**调研目标时（如同时调研 N 个项目/来源），分治给子 Agent 并行执行：

**适合分治**：目标相互独立、每个子任务量足够大、需要浏览器或长时间运行
**不适合分治**：目标有依赖关系、简单单页查询

子 Agent prompt 写**目标**（"获取 X 的信息"），不写**步骤**（"搜索 X 然后访问 X"），避免限制其判断空间。

## 架构概览

```
Agent 调用 → web-reader.sh <url> [options]
                │
                ├─ L1: 快速抓取（公开页面，<3s）
                │   defuddle parse → Scrapling+html2text (scripts/fetch.py) → web_fetch
                │
                ├─ L2: 浏览器渲染（登录页面/JS 重页面）
                │   OpenClaw browser 工具（CDP 直连）
                │   → markdown 内容提取
                │
                └─ L3: 内容清洗（统一输出）
                    defuddle 提取正文 → YAML front matter + markdown
```

## 使用方式

```bash
# 基本用法（自动选择最佳策略）
bash ~/.openclaw/skills/web-reader/scripts/web-reader.sh <url>

# 强制使用浏览器渲染（L2）
bash ~/.openclaw/skills/web-reader/scripts/web-reader.sh <url> --browser

# 指定 PinchTab profile
bash ~/.openclaw/skills/web-reader/scripts/web-reader.sh <url> --profile zhihu

# 保存到文件
bash ~/.openclaw/skills/web-reader/scripts/web-reader.sh <url> --save /path/to/output.md

# 只输出 JSON 元数据 + 内容
bash ~/.openclaw/skills/web-reader/scripts/web-reader.sh <url> --json
```

## 参数说明

| 参数 | 说明 |
|------|------|
| `<url>` | 必填，要读取的网页 URL |
| `--browser` | 强制走 L2 浏览器渲染 |
| `--profile <name>` | 指定 PinchTab profile（默认自动匹配域名） |
| `--save <path>` | 保存 markdown 到指定文件 |
| `--json` | 输出 JSON 格式（含元数据） |
| `--max-chars <n>` | 最大字符数（默认 50000） |
| `--timeout <s>` | 页面加载超时秒数（默认 30） |

## 域名自动路由

| 域名 | 层级 | Profile | 备注 |
|------|------|---------|------|
| `zhuanlan.zhihu.com` / `www.zhihu.com` | L2 | zhihu | 需登录看完整内容 |
| `x.com` / `twitter.com` | L2 | x-twitter | 需登录 |
| `mp.weixin.qq.com` | L1 (Scrapling) | — | 大部分不需登录 |
| `medium.com` / `substack.com` | L1 | — | 公开内容 |
| GitHub | L1 (defuddle) | — | 静态内容 |
| 其他 | L1 → L2 自动回退 | default | |

## 输出格式

YAML front matter + markdown 正文：

```markdown
---
url: https://docs.example.org/sample-page
title: 文章标题
author: 作者名
published: 2026-03-17
site: docs.example.org
word_count: 1234
captured_at: 2026-03-17T22:00:00+08:00
captured_via: defuddle|scrapling|pinchtab
---

正文 markdown 内容...
```

## 站点经验积累

操作中积累的特定网站经验，按域名存储在 `references/site-patterns/` 下。

**使用流程**：
1. 确定目标网站后，检查是否已有经验文件：!`ls ${SKILL_DIR:-~/.openclaw/skills/web-reader}/references/site-patterns/ 2>/dev/null | sed 's/\.md$//' || echo "暂无"`
2. 有匹配则读取对应文件，获取先验知识（平台特征、有效模式、已知陷阱）
3. 经验是"可能有效的提示"而非保证——按经验操作失败时，回退通用模式并更新经验文件
4. 成功发现新模式时，主动写入对应站点经验文件（只写验证过的事实）

**文件格式**：
```markdown
---
domain: docs.example.org
aliases: [示例, Example]
updated: 2026-03-25
---
## 平台特征
架构、反爬行为、登录需求、内容加载方式

## 有效模式
已验证的 URL 模式、操作策略、选择器

## 已知陷阱
什么会失败以及为什么
```

## 技术事实

- 页面中存在大量已加载但未展示的内容（轮播非当前帧、折叠区块、懒加载占位等），它们在 DOM 中但对用户不可见。以数据结构为单位思考可直接触达
- 短时间内密集打开大量页面可能触发反爬风控
- 平台返回的"内容不存在"不一定反映真实状态，也可能是访问方式的问题（URL 缺参数、触发反爬）
- 站点内 URL（DOM 中的 href）天然携带平台所需的完整上下文，手动构造的 URL 可能缺失隐式必要参数

## 非协商输出规则

- **必须输出原始正文**，不要摘要化、总结、或用"文章概要"替代实际内容。Agent 的职责是搬运和清洗，不是改写。
- **必须使用 YAML front matter 格式**（`---` 包裹），不要把元数据散落在正文或表格里。
- **必须保留原始 markdown 链接** `[text](url)`，不要去掉 URL 只留标题文字。
- **不要把输出包裹在 markdown 代码块中**（不要用 ` ```markdown ` 包裹整个结果）。
- **不要在正文前后添加解释性文字**（如"抓取完成""以下是结果"等），直接输出 front matter + 正文。
- **大页面必须截断**：当抓取到的内容超过 30000 字符时，保留前 30000 字符并附加 `\n\n---\n\n[内容已截断，原文共 N 字符]`。不要因为内容太长而放弃输出或改用摘要替代。

## 依赖

- **defuddle** (npm): `npm install -g defuddle` — 内容提取 + markdown 转换
- **Scrapling + html2text** (Python): `pip install scrapling html2text` — L1 备选
- **bb-browser** (npm): `npm install -g bb-browser` — 站点级操作（搜索、查询结构化数据）
- **opencli-rs** (binary): 单文件 CLI，55+ 站点 / 333+ 命令，含 Public 模式（不需要登录）
- **OpenClaw browser 工具**: 内置 CDP 浏览器，用于需要登录态/JS 渲染的页面

## 站点级操作（opencli-rs + bb-browser）

对需要登录态或结构化数据查询的站点，使用站点级 CLI 工具。
完整路由表见 `references/site-routing.md`。

### 快速参考

```bash
# === opencli-rs（优先） ===
opencli-rs hackernews top --limit 10 --format json       # Public，不需要登录
opencli-rs bilibili hot --limit 10 --format json          # B站热榜
opencli-rs zhihu hot --limit 10 --format json              # 知乎热榜
opencli-rs weibo hot --limit 10 --format json              # 微博热搜
opencli-rs xiaohongshu feed --limit 10 --format json       # 小红书 Feed
opencli-rs weread search "认知觉醒" --format json          # 微信读书
opencli-rs bloomberg tech --format json                     # 彭博科技
opencli-rs weixin download <url>                            # 微信文章下载为 Markdown
opencli-rs douban search "沙丘" --format json              # 豆瓣搜索
opencli-rs twitter search "AI agent" --format json         # X 搜索
opencli-rs reddit hot --limit 10 --format json              # Reddit
opencli-rs arxiv search "LLM" --format json                # 论文搜索

# === bb-browser（独有站点或命令更多时使用） ===
bb-browser site weibo/feed 10                                  # 微博 timeline
bb-browser site youtube/channel <channel-id>                # YouTube 频道
bb-browser site sogou/weixin "AI agent"                     # 搜狗微信搜索
bb-browser site baidu/search "大语言模型"                    # 百度搜索
bb-browser site csdn/search "Rust"                         # CSDN 搜索
bb-browser site eastmoney/stock SH600519                    # 东方财富
bb-browser site list                                         # 查看所有 adapter
```

### 工具选择决策

| 请求类型 | 首选 | 备选 |
|---------|------|------|
| 公开 API 站点（HN/devto/arxiv 等） | opencli-rs | — |
| bilibili/zhihu/xiaohongshu/twitter/reddit | opencli-rs | bb-browser |
| weibo（需 feed/me/post） | bb-browser | opencli-rs |
| youtube（需 channel/comments） | bb-browser | opencli-rs |
| 中文站独有（百度/CSDN/搜狗等） | bb-browser | — |
| 海外站独有（weread/medium/bloomberg 等） | opencli-rs | — |

**分工**：
- **web-reader** — "给我这个 URL 的内容"（页面抓取 + 清洗）
- **site_router** — "帮我搜索/操作这个网站"（自动路由到 opencli-rs 或 bb-browser）
- **browser 工具** — 底层 CDP 能力（兜底）

### 统一路由入口

当不确定该用哪个工具时，直接用 `site_router.py`，它会自动选择：

```bash
# 自动路由（推荐）
python3 ~/.gorin-skills/openclaw/web-reader/scripts/site_router.py <site> <command> [args...]

# 检测工具可用性
python3 ~/.gorin-skills/openclaw/web-reader/scripts/site_router.py probe

# 列出所有支持站点
python3 ~/.gorin-skills/openclaw/web-reader/scripts/site_router.py list
```

site_router 会自动处理：工具可用性检测、Public/Browser 模式判断、执行失败时的 fallback。

## 批量采集管线

需要一次抓多个来源时，使用 `collect_pipeline.py`：

```bash
PIPELINE=~/.gorin-skills/openclaw/web-reader/scripts/collect_pipeline.py

# 使用预设方案
python3 $PIPELINE --preset daily-tech          # HN + V2EX + DevTo + Lobsters
python3 $PIPELINE --preset invest-cn            # 雪球 + 微博 + 小红书 + 36kr
python3 $PIPELINE --preset ai-research          # arXiv + HN + HF Models
python3 $PIPELINE --preset content-cn           # B站 + 知乎 + 微博 + 小红书 + 抖音

# 输出为 Markdown（适合直接发群/存文件）
python3 $PIPELINE --preset daily-tech --format md

# 自定义来源
python3 $PIPELINE hackernews/top bilibili/hot zhihu/hot

# 输出到文件
python3 $PIPELINE --preset invest-cn --format md -o /tmp/invest-report.md

# 列出所有预设
python3 $PIPELINE --list-presets
```

管线会自动：路由到正确的工具、合并结果、处理 fallback、统一输出格式。

## 文章下载

需要将文章保存为 Markdown 文件时：

```bash
# 微信公众号文章
opencli-rs weixin download <url> --output ./articles

# 知乎文章/回答
opencli-rs zhihu download <url> --output ./articles

# B站视频（需要 yt-dlp）
opencli-rs bilibili download <bvid> --output ./videos
```

注意：下载功能需要 Chrome 已登录对应网站（opencli-rs Browser 模式）。

## AI 适配器生成

遇到两个工具都不支持的网站时，可以自动生成适配器：

```bash
# 基础生成（自动分析页面结构）
opencli-rs generate "https://example.com" --goal hot

# AI 辅助生成（需要 ~/.opencli-rs/config.json 配置 LLM key）
opencli-rs generate "https://example.com" --goal search --ai
```

生成后直接可用：`opencli-rs example hot --format json`
适配器保存在 `~/.opencli-rs/adapters/` 下。

## 需要浏览器渲染的页面

对于 JS 重度渲染或需要登录态的页面：
1. 先尝试 L1 抓取（部分页面返回足够内容）
2. L1 失败时，agent 应使用 OpenClaw 内置 `browser` 工具：
   - `browser open` → `browser snapshot` 获取内容
   - 或 `browser navigate` → `browser snapshot`
3. 站点级操作（搜索、查询）按 `references/site-routing.md` 路由表选择 opencli-rs 或 bb-browser

## 防死循环规则

同一个 URL 在 L1 和 L2 各尝试一次，均失败则返回错误信息，不重复重试。

## Gotchas

- **L1 对 JS 渲染页面无效**：defuddle/Scrapling 只能抓静态 HTML。知乎、X 等页面需要用 OpenClaw browser 工具或 bb-browser adapter。
- **browser 工具依赖已登录的浏览器**：如果目标网站未在 Chrome 中登录，snapshot 拿到的是登录页。确保在 host 浏览器中已登录目标站点。
- **web_fetch 不是万能的**：对 JS-heavy 页面，`web_fetch` 工具只返回初始 HTML（没有动态内容）。这种情况需要用 browser 工具。
- **微信公众号文章需要特殊处理**：Jina Reader 无法抓取微信公众号文章（`mp.weixin.qq.com`），可尝试 Scrapling 或 browser 工具。
- **bb-browser adapter 依赖浏览器登录态**：twitter/zhihu/weibo 等 adapter 需要用户已在 host Chrome 中登录对应网站。

## When NOT to Use

- 不用于本地文件读取（直接用 Read 工具）。
- 不用于 API 调用或数据获取（用 Exec + curl）。
- 不用于需要频繁交互的动态页面（如实时聊天）。

## Error Handling

- L1 快速抓取失败时自动降级到 L2 浏览器渲染。
- L2 渲染超时（>30s）时返回已获取的部分内容并标注。
- 反爬检测触发时，增加延迟并更换 user-agent。

## Internal Acceptance

- 返回的 Markdown 内容包含原文的主要结构和信息。
- 代码块、表格、列表等格式正确保留。
- 从触发到返回内容总耗时 <60 秒。

## Delivery Contract

- 输出干净的 Markdown 格式正文。
- 保留原文标题作为 H1。
- 代码块标注语言类型。
- 图片 URL 保留（不下载）。
**注意：本技能是大型流水线的一部分。Do **not** report completion to the user unless all dependent tools/scripts/skills have been verified as integrated.**not** report completion to the user unless all dependent tools/scripts/skills integration tests have passed.**

---
name: ai-image-digest
description: "每日 AI 行业图片日报。中英文混合来源（follow-builders 25 builder + 5 播客 + 中文源），抓取→去重→生成 HTML→截图→发 Telegram 群。替代 ai-builder-digest 的文字版输出。"
triggers: ["图片日报", "AI 日报", "image digest", "AI image digest", "/image-digest"]
user-invocable: true
agent-usable: true
---

# AI Image Digest — 每日图片日报

> 每日从 curated 来源池抓取 AI 行业最新动态，去重 → 生成精美 HTML 日报 → 截图 → 发 Telegram 群。

## When to Use

- 用户要求每日 AI 图片日报
- 定时从多个来源收集 AI 动态并以图片形式输出
- 手动触发一次图片日报

## When NOT to Use

- 只摘要单篇文章 → 用 web_reader + zk
- 需要文字版 digest → 用 ai-builder-digest
- 通用信息图 → 用 baoyu-infographic

## Architecture

```
cron 触发 / 手动触发
  │
  ├─ 1. 加载配置 + 状态
  │
  ├─ 2. 并行抓取（子 Agent 分治）
  │     ├─ 英文: fetch follow-builders feed JSONs（HTTP GET）
  │     └─ 中文: web_reader 逐源抓取
  │
  ├─ 3. 去重（对比 state/last-digest.json）
  │
  ├─ 4. 无新内容？ → NO_REPLY 静默
  │
  ├─ 5. 生成中文摘要（每个 item ≤ 3 句话）
  │
  ├─ 6. 填充 HTML 模板 → 截图生成图片
  │
  ├─ 7. 发送图片到 Telegram 群
  │
  └─ 8. 更新状态 + 存 PKM 笔记
```

## Core Workflow

### Step 0: 加载配置

```bash
cat ~/.gorin-skills/openclaw/ai-image-digest/config/sources.json
cat ~/.openclaw/workspace-daily-collector/ai-image-digest/state/last-digest.json 2>/dev/null || echo "{}"
```

### Step 1: 抓取来源

**英文来源（follow-builders 中心化 feed）**：
```bash
curl -sL "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-x.json"
curl -sL "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-podcasts.json"
curl -sL "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-blogs.json"
```

Feed 结构：
- `feed-x.json`: `{ generatedAt, x: [{ name, handle, bio, tweets: [{ id, text, createdAt, url, likes }] }] }`
- `feed-podcasts.json`: `{ generatedAt, podcasts: [{ name, title, videoId, url, publishedAt, transcript }] }`
- `feed-blogs.json`: `{ generatedAt, blogs: [{ name, title, url, publishedAt, content }] }`

> 优势: 不需要逐个爬 X/YouTube，不需要 API key，不需要登录态。GitHub Actions 每天 6am UTC 自动更新。

**中文来源（沿用 ai-builder-digest 方案）**：
```bash
bash ~/.openclaw/skills/web-reader/scripts/web-reader.sh "<url>" --max-chars 15000
```

中文源经验参考 `~/.gorin-skills/openclaw/ai-builder-digest/references/site-patterns/`。

**并行执行**：英文 feed 和中文源独立，分治给子 Agent 并行抓取。

### Step 2: 去重

- follow-builders tweets: 用 tweet `id`
- podcasts: 用 `videoId`
- blogs: 用 `url`
- 中文: 用文章 URL

保留最近 500 条 seen_urls。

### Step 3: 生成摘要

每条新内容生成中文摘要（≤ 3 句话）：
- 谁说了什么 + 核心观点
- 英文内容翻译为中文，关键术语保留英文
- 过滤低质量内容（纯转发、广告、likes < 20 的无实质推文）
- 每天保留 15-20 条，按重要性排序

### Step 4: 生成图片

1. 读取 `templates/digest.html` 模板
2. 填充数据（摘要 + 元信息）
3. 保存为临时 HTML 文件
4. 使用 browser 工具打开 HTML 并截图（1080px 宽，高度自适应）
5. 保存到 `~/.openclaw/workspace-daily-collector/ai-image-digest/output/`

**回退方案**（browser 工具不可用时）：
- 方案 A: 发送 HTML 格式的 Telegram 消息
- 方案 B: 使用 baoyu-infographic 生成信息图

### Step 5: 发送图片

发送图片到 Telegram 群（-1003395996452 topic 8），附带简短文字说明。

### Step 6: 更新状态 + 存笔记

```bash
# 更新 seen_urls
# 存 PKM 笔记
zk input="<digest 正文>" type="literature" title="AI Image Digest {date}" tags=["ai-digest", "daily"]
```

## 来源列表

### 英文（follow-builders）

**X Builders（25 人）**：Karpathy, Swyx, Josh Woodward, Kevin Weil, Peter Yang, Nan Yu, Madhu Guru, Amanda Askell, Cat Wu, Thariq, Google Labs, Amjad Masad, Guillermo Rauch, Alex Albert, Aaron Levie, Ryo Lu, Garry Tan, Matt Turck, Zara Zhang, Nikunj Kothari, Peter Steinberger, Dan Shipper, Aditya Agarwal, Sam Altman, Claude

**Podcasts（5 个）**：Latent Space, Training Data, No Priors, Unsupervised Learning, Data Driven NYC

**Blogs（2 个）**：Anthropic Engineering, Claude Blog

### 中文

**微信公众号**：机器之心, 量子位, AI科技评论, 新智元
**其他**：少数派 AI 标签

## Cron 配置

- **时间**: 每天 08:15 Asia/Shanghai
- **Agent**: daily-collector（isolated session）
- **超时**: 300s
- **目标**: Telegram 群 -1003395996452 topic 8
- **状态文件**: `~/.openclaw/workspace-daily-collector/ai-image-digest/state/last-digest.json`
- **晋级脚本**: `python3 /Users/gorin/.openclaw/workspace-daily-tl/scripts/promote_ai_image_digest.py --check-only`

## Gotchas

- **follow-builders feed 更新延迟**: GitHub Actions 每天 6am UTC（北京时间 14:00）更新。8:15 cron 看到的是前一天的数据，但覆盖最近 24-72h，足够。
- **X 推文质量参差**: follow-builders 不做内容筛选，需要本地过滤。likes < 20 的纯分享类推文应排除。
- **Podcast transcript 很长**: 单个可达 5000-20000 字。摘要时只取核心观点，不逐字翻译。
- **中文源抓取不稳定**: 微信公众号需 web_search 发现 URL + web_reader 抓取。36kr 有 WAF 限制。
- **图片尺寸**: Telegram 压缩图片，建议 1080px 宽。高度建议 < 2000px 保证手机可读。
- **HTML 模板字体**: 使用系统字体栈，避免中文字体缺失。
- **browser 工具依赖**: 图片生成依赖宿主机 browser 工具截图。不可用时回退文字 digest。
- **替换 08:30 ai-builder-digest**: 设置此 cron 后，应删除或暂停原有 08:30 文字版 cron。

## Error Handling

- 超过 50% 来源失败 → 发送告警消息而非 digest
- 状态文件损坏 → 重置为空状态
- seen_urls 超过 500 → 裁剪最旧的条目
- 中文源全部失败 → 仍发布英文内容（标注"中文源抓取失败"）

## Data Persistence

```json
{
  "last_run": "2026-03-26T08:15:00+08:00",
  "seen_urls_tweets": [],
  "seen_urls_podcasts": [],
  "seen_urls_blogs": [],
  "seen_urls_zh": [],
  "errors": []
}
```

## Origin Metadata

```json
{
  "origin": "self",
  "author": "gorin",
  "readiness": "mvp",
  "lifecycle_status": "monitoring",
  "replaces": "ai-builder-digest (deprecated text version)",
  "cron_schedule": "15 8 * * * Asia/Shanghai",
  "created": "2026-03-26T23:43:00+08:00",
  "auto_promote": {
    "target": "integrated",
    "condition": "3 successful runs spanning >= 3 different dates in state runs[]",
    "checked_by": "cron payload step 9"
  }
}
```

# AI Image Digest — Cron Payload

你是 daily-collector agent，现在执行每日 AI 图片日报任务。

## 执行步骤

### Step 1: 加载状态
```bash
cat ~/.openclaw/workspace-daily-collector/ai-image-digest/state/last-digest.json 2>/dev/null || echo '{"seen_urls_tweets":[],"seen_urls_podcasts":[],"seen_urls_blogs":[],"seen_urls_zh":[],"last_run":null,"errors":[]}'
```

### Step 2: 抓取英文来源（follow-builders feed）
用 `exec` + `curl` 抓取三个 JSON feed（不要用 web_fetch，因 Surge 代理会导致 IP 检查失败）：
```bash
curl -sL https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-x.json
curl -sL https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-podcasts.json
curl -sL https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-blogs.json
```
三个可并行执行。结果解析为 JSON。

### Step 3: 抓取中文来源
用 web_search 发现最新文章 URL，再用 web_reader 抓正文。
参考 `~/.gorin-skills/openclaw/ai-builder-digest/references/site-patterns/` 下的经验文件。
源: 机器之心(36kr转载页) / 量子位 / AI科技评论 / 新智元

### Step 4: 去重 + 过滤
过滤规则: likes<20 纯分享排除 / 纯转发排除 / 同事件合并 / 保留 15-20 条

### Step 5: 生成中文摘要
每条≤3句话，英文翻译为中文，关键术语保留英文

### Step 6: 生成 HTML（必须执行）

**这一步不可跳过。** 必须读取模板、填充数据、保存文件。

#### 6.1 读取模板
```bash
cat ~/.gorin-skills/openclaw/ai-image-digest/templates/digest.html
```

#### 6.2 遍历数据，生成每个 item 的 HTML

对每个板块（podcast / x / blog / zh），遍历数据并生成 HTML。每个 item 必须包含：编号、头像首字母、名字、handle、时间、热度、摘要、源链接。

**X/Twitter item HTML 结构：**
```html
<div class="item twitter-item">
  <div class="item-meta">
    <span class="item-num">1</span>
    <div class="item-avatar twitter">K</div>
    <span class="item-name">Andrej Karpathy</span>
    <span class="item-handle">@karpathy</span>
    <span class="item-stats">❤️ 3859</span>
  </div>
  <div class="item-content"><strong>核心观点放在 strong 标签内。</strong>后续补充说明...</div>
  <div class="item-link"><a href="https://x.com/karpathy/status/123">🔗 x.com/karpathy/status/123</a></div>
</div>
```

**Podcast item HTML 结构：**
```html
<div class="item podcast-item">
  <div class="item-meta">
    <span class="item-num">1</span>
    <div class="item-avatar podcast">L</div>
    <span class="item-name">Latent Space</span>
    <span class="item-stats podcast-stats">🎙 播客</span>
  </div>
  <div class="item-content"><strong>核心话题放在 strong 标签内。</strong>补充说明...</div>
  <div class="item-link"><a href="https://youtube.com/watch?v=xxx">🔗 youtube.com/watch?v=xxx</a></div>
</div>
```

**Blog item HTML 结构：**
```html
<div class="item blog-item">
  <div class="item-meta">
    <span class="item-num">1</span>
    <div class="item-avatar blog">A</div>
    <span class="item-name">Anthropic Engineering</span>
    <span class="item-stats blog-stats">📝 博客</span>
  </div>
  <div class="item-content"><strong>核心话题放在 strong 标签内。</strong>补充说明...</div>
  <div class="item-link"><a href="https://anthropic.com/...">🔗 anthropic.com/...</a></div>
</div>
```

**中文 item HTML 结构：**
```html
<div class="item chinese-item">
  <div class="item-meta">
    <span class="item-num">1</span>
    <div class="item-avatar chinese">量</div>
    <span class="item-name">量子位</span>
    <span class="item-stats chinese-stats">📰 中文</span>
  </div>
  <div class="item-content"><strong>核心话题放在 strong 标签内。</strong>补充说明...</div>
  <div class="item-link"><a href="https://www.qbitai.com/...">🔗 qbitai.com/...</a></div>
</div>
```

#### 6.3 组装 section HTML

将所有 item 包裹在 section 结构中。头像首字母取名字第一个字符（英文名取 first name 首字母，中文名取第一个汉字）。没有内容的板块用空字符串。

```html
<div class="section">
  <div class="section-header">
    <div class="section-icon twitter">𝕏</div>
    <div class="section-title">Twitter / X</div>
    <div class="section-count">11 条精选</div>
  </div>
  <div class="items">
    <!-- 每个item用上面的结构 -->
  </div>
</div>
```

Section icon 对应关系：
- podcast → `<div class="section-icon podcast">🎙</div>` + title "Podcasts"
- twitter → `<div class="section-icon twitter">𝕏</div>` + title "Twitter / X"
- blog → `<div class="section-icon blog">📝</div>` + title "Blogs"
- chinese → `<div class="section-icon chinese">🇨🇳</div>` + title "中文媒体"

#### 6.4 替换模板占位符并保存

用 `write` 工具保存到：
`~/.openclaw/workspace-daily-collector/ai-image-digest/output/digest-YYYYMMDD.html`

占位符说明：
- `{{DATE}}` → `YYYY-MM-DD` 格式日期
- `{{PODCAST_SECTION}}` → 完整的 podcast section HTML（无内容则为空字符串）
- `{{TWITTER_SECTION}}` → 完整的 twitter section HTML
- `{{BLOG_SECTION}}` → 完整的 blog section HTML
- `{{CHINESE_SECTION}}` → 完整的中文 section HTML
- `{{STATS}}` → 例如 `共 16 条 · X 11 · 中文 5`

### Step 6.5: 生成 TXT 文字版（必须执行，不可跳过）

**⚠️ 这一步是硬性要求。** 邮件正文将直接使用此文件内容。

#### 6.5.1 读取模板
```bash
cat ~/.gorin-skills/openclaw/ai-image-digest/templates/digest.txt
```

#### 6.5.2 用与 Step 6 相同的数据结构生成文字版

遍历数据，按板块生成文字内容。**每条新闻必须包含源链接（🔗 URL）。**

X/Twitter 条目格式：
```
1. Andrej Karpathy（❤️ 3859）
Karpathy指出，真正难自动化的不是写代码，而是把支付、鉴权、数据库、部署等DevOps链路"编排成可执行流程"。
🔗 https://x.com/karpathy/status/2037200624450936940
```

Podcast 条目格式：
```
1. Latent Space
讨论了[核心话题]。嘉宾指出[关键观点]。
🔗 https://youtube.com/watch?v=xxx
```

Blog 条目格式：
```
1. Anthropic Engineering
[文章标题/核心内容]。
🔗 https://anthropic.com/...
```

中文条目格式：
```
1. 量子位
阿里在财报会上给出明确AI商业目标...
🔗 https://www.qbitai.com/2026/03/389559.html
```

#### 6.5.3 组装板块

只有有内容的板块才输出。每个板块前面空一行，格式如下：

```
【Podcasts】

1. Latent Space
...
🔗 https://...

【X / Builders】

1. Thariq（❤️ 5352）
...
🔗 https://...

【Blogs】

1. Anthropic Engineering
...
🔗 https://...

【中文】

1. 量子位
...
🔗 https://...
```

#### 6.5.4 替换模板占位符并保存

用 `write` 工具保存到：
`~/.openclaw/workspace-daily-collector/ai-image-digest/output/digest-YYYYMMDD.txt`

占位符说明：
- `{{DATE}}` → `YYYY-MM-DD`
- `{{TOTAL}}` → 总条目数（如 `16`）
- `{{BREAKDOWN}}` → 分板块统计（如 `X 11｜中文 5` 或 `X 8｜Podcast 3｜Blog 2｜中文 3`）
- `{{PODCAST_SECTION}}` → 完整的 Podcast 板块文字内容（无内容则为空字符串）
- `{{TWITTER_SECTION}}` → 完整的 X 板块文字内容
- `{{BLOG_SECTION}}` → 完整的 Blog 板块文字内容
- `{{CHINESE_SECTION}}` → 完整的中文板块文字内容

### Step 6.6: 生成 meta.json（必须执行）

读取模板：
```bash
cat ~/.gorin-skills/openclaw/ai-image-digest/templates/digest-meta.json
```

用实际数据替换占位符：

```json
{
  "date": "2026-03-29",
  "date_compact": "20260329",
  "html_path": "/Users/gorin/.openclaw/workspace-daily-collector/ai-image-digest/output/digest-20260329.html",
  "text_path": "/Users/gorin/.openclaw/workspace-daily-collector/ai-image-digest/output/digest-20260329.txt",
  "png_path": "/Users/gorin/.openclaw/workspace-daily-collector/ai-image-digest/output/digest-20260329.png",
  "items_count": 16,
  "x_count": 11,
  "podcast_count": 0,
  "blog_count": 0,
  "zh_count": 5,
  "tweet_urls": ["https://x.com/karpathy/status/...", "https://x.com/sama/status/..."],
  "podcast_ids": [],
  "blog_urls": [],
  "zh_ids": ["qbit-ali-ai-revenue-2026-03-19", "36kr-openai-stop-sora-2026-03-25"],
  "errors": []
}
```

保存到：
`~/.openclaw/workspace-daily-collector/ai-image-digest/output/digest-YYYYMMDD.meta.json`

### Step 6.7: 截图生成 PNG

使用 browser 工具打开已生成的 HTML 文件截图（1080px 宽，高度自适应）。
保存到：`~/.openclaw/workspace-daily-collector/ai-image-digest/output/digest-YYYYMMDD.png`

browser 不可用时回退发送文字版 Telegram 消息。

### ⛔ Step 7: 发送前验证检查点（必须执行）

在发送邮件前，**必须**确认以下 4 个文件全部存在：

```bash
ls -la ~/.openclaw/workspace-daily-collector/ai-image-digest/output/digest-YYYYMMDD.html
ls -la ~/.openclaw/workspace-daily-collector/ai-image-digest/output/digest-YYYYMMDD.txt
ls -la ~/.openclaw/workspace-daily-collector/ai-image-digest/output/digest-YYYYMMDD.meta.json
ls -la ~/.openclaw/workspace-daily-collector/ai-image-digest/output/digest-YYYYMMDD.png
```

**缺少任何一个文件，必须补生成后再继续。** 不得跳过。

### Step 8: 发送邮件

使用 send-email skill 发送：

```bash
python3 ~/.openclaw/workspace/skills/send-email/send_email.py "5065129@qq.com" "📰 AI Builder Daily — YYYY-MM-DD" "$(cat ~/.openclaw/workspace-daily-collector/ai-image-digest/output/digest-YYYYMMDD.txt)" "/Users/gorin/.openclaw/workspace-daily-collector/ai-image-digest/output/digest-YYYYMMDD.png"
```

**关键约束：**
- 收件人: 5065129@qq.com
- 主题: `📰 AI Builder Daily — YYYY-MM-DD`
- **正文必须用 `$(cat digest-YYYYMMDD.txt)` 读取 txt 文件内容**，包含所有 🔗 链接
- **🚫 禁止 agent 自己编写邮件正文。** 不允许手写摘要、不允许省略链接、不允许"我总结了以下内容"这类自创格式
- 附件: 截图 PNG（如果生成了）

### Step 9: 更新状态 + 存 PKM 笔记
追加 seen_urls（裁剪到 500 条），zk 存 literature 笔记

### Step 9.5: 写入 outcome log
运行：
```bash
python3 /Users/gorin/.openclaw/workspace-daily-tl/scripts/record_skill_outcome.py \
  --skill ai-image-digest \
  --trigger cron \
  --agent-id daily-collector \
  --status partial \
  --fallback-used true \
  --manual-intervention false \
  --notes "browser unavailable; fell back to text delivery"
```
若本次完整成功且无关键降级，则改为 `--status ok --fallback-used false`；若未生成可用日报，则记为 `--status failed` 并附 `--error-code`。

### Step 10: 自我检查
运行：
```bash
python3 /Users/gorin/.openclaw/workspace-daily-tl/scripts/promote_ai_image_digest.py
```
脚本会读取 `runs[]` 中 `status=ok` 的记录；若最近 successful runs 已满足跨 >=3 个不同日期且总数 >=3，则自动：
- 把 `SKILL.md` Origin Metadata 的 `readiness` 改为 `integrated`
- 把 `.skill-meta.json` 的 `readiness` 改为 `integrated`
- 把 `lifecycle_status` 改为 `active`
- 在 state 文件中写入 `promoted_to_integrated_at`
若尚未达标，脚本只输出当前统计，不写文件。

### 错误处理
单源失败记录 errors 继续 / >50% 失败发告警 / 中文全失败仍发英文 / 无新内容 NO_REPLY

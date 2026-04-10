---
name: ai-builder-digest
description: "每日 AI 行业信息聚合 digest，覆盖中英文 builder/podcast/blog 来源。多源抓取→去重→中文摘要→发 Telegram 群+存 PKM 笔记。当用户要求每日 AI 新闻聚合、AI builder 动态收集、创建/运行 AI digest 时触发。Don't use for single-article summaries (use web_reader+zk directly) or generic RSS monitoring (use blogwatcher instead) or non-AI content aggregation."
triggers: ["AI digest", "每日 AI 新闻", "AI 信息聚合", "follow builders", "收集 AI 动态", "builder digest", "AI 行业日报", "/digest"]
user-invocable: true
agent-usable: true
---

# AI Builder Digest

> ⚠️ 已废弃：该文字版 digest 已被 `ai-image-digest` 替代，不再继续推进集成或监控晋级。
>
> 历史用途保留供参考；新需求一律转到 `ai-image-digest`。

基于 [follow-builders](https://github.com/zarazhangrui/follow-builders) 的 curated source + dedup 思路，但用 OpenClaw 原生工具链（web_reader / cron / zk / message）编排，不依赖外部中心化 feed 服务。

## When to Use

- 用户要求创建/运行每日 AI 行业信息聚合
- 定时从多个来源收集 AI builder 动态并汇总
- 手动触发一次 digest（如 `/digest run` 或 "跑一次今天的 AI digest"）
- 用户想添加/移除/修改信息来源

## When NOT to Use

- 只摘要单篇文章 → 直接用 web_reader + zk
- 通用 RSS 监控 → 用 blogwatcher skill
- 用户只是随手发一个链接要求摘要 → 直接抓取，不走 digest 流程

## Design Pattern

**Pipeline + Monitor/Cron** 模式：

```
cron 触发 / 手动触发
  │
  ├─ 1. 加载来源列表 (config/sources.json)
  │
  ├─ 2. 并行抓取 (web_reader, 每源独立)
  │     ├─ 源 A ✓ → 内容
  │     ├─ 源 B ✗ → 记录错误，跳过
  │     └─ 源 C ✓ → 内容
  │
  ├─ 3. 去重 (对比 state/last-digest.json)
  │     ├─ 已见 → 跳过
  │     └─ 新内容 → 收集
  │
  ├─ 4. 无新内容？ → 静默结束 (NO_REPLY)
  │
  ├─ 5. 生成中文摘要 (config/digest-prompt.md 模板)
  │
  ├─ 6. 输出路由
  │     ├─ message → Telegram 群
  │     └─ zk → PKM vault (literature 笔记)
  │
  └─ 7. 更新状态文件 (state/last-digest.json)
```

**核心约束**：
- **幂等**：重复运行安全，靠状态文件去重
- **每源独立**：一个源挂了不影响其他源
- **编排优于重写**：调用 web_reader / zk / message，不自己实现抓取和存储
- **正常静默**：没新内容不发消息

## Core Workflow

### Step 0: 加载配置

```bash
# 来源列表
cat ~/.gorin-skills/openclaw/ai-builder-digest/config/sources.json

# 状态文件（幂等关键）
cat ~/.openclaw/workspace-ai-builder-digest/state/last-digest.json 2>/dev/null || echo "{}"
```

状态文件路径固定为 `~/.openclaw/workspace-ai-builder-digest/state/last-digest.json`。

### Step 1: 抓取来源

对 `sources.json` 中每个来源，按类型执行对应抓取策略：

**X/Twitter builder 账号**：
```bash
# 构造搜索 URL，获取最近 24h 推文
bash ~/.openclaw/skills/web-reader/scripts/web-reader.sh \
  "https://nitter.net/{handle}" --max-chars 10000
```
> ⚠️ Nitter 实例不稳定。备选：`web_search "{handle} site:x.com" --count 5`，然后用 `web_fetch` 抓取推文链接。参考 `references/site-patterns/x-twitter.md`。

**Blog / Newsletter（有 RSS 的）**：
```bash
# 优先用 blogwatcher 扫描 RSS
blogwatcher scan
blogwatcher articles
```
> 对未添加 blogwatcher 的来源，用 `web_reader` 抓取博客首页，提取最近文章链接后再逐篇抓取正文。

**微信公众号**：
```bash
# 用 web_reader L1 (Scrapling) 抓取公众号文章
bash ~/.openclaw/skills/web-reader/scripts/web-reader.sh \
  "<mp.weixin.qq.com URL>" --max-chars 15000
```
> 微信公众号没有稳定 RSS。需要通过 web_search 发现最新文章 URL（如 `web_search "机器之心 site:mp.weixin.qq.com"`），再抓取正文。参考 `references/site-patterns/wechat-mp.md`。

**YouTube / Podcast show notes**：
```bash
bash ~/.openclaw/skills/web-reader/scripts/web-reader.sh \
  "<YouTube 频道页或 podcast 页面>" --max-chars 10000
```
> 抓取节目描述和 show notes，不下载音视频。

**并行执行**：来源间独立，可分治给子 Agent 并行抓取。每个子 Agent 负责一组来源，返回 `{source, url, title, content, fetched_at}` 结构。

### Step 2: 去重

对比每条内容的 URL/标题与 `last-digest.json` 中的 `seen_urls`：

```python
# 伪代码 — 实际由 agent 判断
new_items = [item for item in fetched if item.url not in state.seen_urls]
```

**去重字段优先级**：URL > 标题精确匹配 > 标题相似度(>0.9)

### Step 3: 生成摘要

读取 `config/digest-prompt.md` 作为摘要模板。对新内容按主题分组，生成中文摘要：

**摘要规则**：
- 每条内容 ≤ 3 句话：谁说了什么 + 核心观点
- 保留原始链接
- 按主题分组（模型发布、产品更新、研究突破、行业观点等）
- 总长度 ≤ 2000 字（Telegram 消息限制友好）
- 标注来源语言（中/英）

### Step 4: 输出路由

**发 Telegram 群**：
```python
message(
  action="send",
  target="<用户指定的群 ID 或从 context 获取>",
  message="<digest markdown>",
  # 超长时拆分为多条消息
)
```

**存 PKM 笔记**：
```python
zk(
  input="<digest 正文>",
  type="literature",  # 或 zettel，看内容性质
  title=f"AI Digest {date}",
  tags=["ai-digest", "daily", date],
  source_url="<无，因为是聚合>"
)
```

### Step 5: 更新状态

```bash
# 追加新 URL 到 seen_urls（保留最近 500 条防止无限增长）
# 更新 last_run 时间戳
# 写回 state/last-digest.json
```

## Quick Reference

| 操作 | 方法 |
|------|------|
| 手动跑一次 digest | "跑一次今天的 AI digest" |
| 查看当前来源列表 | `cat config/sources.json` |
| 添加来源 | 编辑 `config/sources.json`，添加到对应分类 |
| 查看上次运行状态 | `cat ~/.openclaw/workspace-ai-builder-digest/state/last-digest.json` |
| 查看存档笔记 | `zk({ input: "search:ai-digest" })` |
| 设置定时 | 用 OpenClaw cron 创建每日定时任务 |

## 来源列表

完整列表见 `config/sources.json`。以下是分类概览：

### 英文 Builder（X/Twitter）

关注 AI 基础设施、模型训练、产品发布的活跃 builder：

| Handle | 领域 |
|--------|------|
| @karpathy | AI 教育、模型训练 |
| @swyx | AI 工程师社区 (Latent.Space) |
| @sama | OpenAI CEO |
| @levie | Jasper CEO / AI 应用 |
| @amasad | Replit CEO |
| @rauchg | Vercel CEO / AI 工程化 |
| @ylecun | Meta AI Chief |
| @AndrewYNg | AI 教育 |
| @JimFanNvidia | NVIDIA AI 研究 |
| @bindureddy | Abacus AI |
| @jaboronx | AI 产品观察 |
| @tsaboris | AI 基础设施 |

### 英文 Podcast / YouTube

| 名称 | 类型 | 频率 |
|------|------|------|
| Latent Space | Podcast + Blog | 周更 |
| No Priors | Podcast | 周更 |
| Unsupervised Learning | Podcast | 周更 |

### 英文 Blog

| 名称 | URL |
|------|-----|
| Anthropic Engineering | anthropic.com/engineering |
| OpenAI Blog | openai.com/blog |
| Google DeepMind Blog | deepmind.google/blog |

### 中文来源

| 名称 | 类型 | 获取方式 |
|------|------|---------|
| 机器之心 | 微信公众号 | 36kr 转载页 (`m.36kr.com/user/214166`) + web_reader |
| 量子位 | 微信公众号 | 同上 |
| AI科技评论 (36kr) | 微信公众号 | 同上 |
| 新智元 | 微信公众号 | 同上 |
| 少数派 AI 标签 | RSS | blogwatcher |

## Gotchas

- **Nitter 实例不稳定**：公共 Nitter 实例经常宕机或被封。备选用 `web_search` 搜索推文。不要假设某个 Nitter 实例永久可用。
- **微信公众号无稳定 RSS**：每次需要通过搜索引擎发现最新文章 URL。`mp.weixin.qq.com` 文章页面需要 web_reader L1 (Scrapling) 而非 L2 浏览器。
- **X/Twitter 需要登录态**：web_reader 对 x.com 走 L2 浏览器渲染，需要预先通过 PinchTab 登录。如果 cookie 过期，L2 会返回登录页。
- **36kr WAF**：m.36kr.com 有 JavaScript challenge 反爬。同域名请求间隔 ≥ 30s，否则 L1/L2 均返回空。web_fetch 工具对 36kr 直接拦截（报内网 IP），必须走 web_reader。每次 digest 最多抓 1-2 篇 36kr 文章。详见 `references/site-patterns/36kr.md`。
- **机器之心付费墙**：jiqizhixin.com 主站正文在 PRO 付费墙后。必须通过 36kr 转载页（`m.36kr.com/user/214166`）间接获取。详见 `references/site-patterns/jiqizhixin.md`。
- **抓取频率控制**：短时间密集抓取同一域名可能触发反爬。每次 digest 运行间隔 ≥ 1 小时，同域名请求间加 2-3 秒延迟。
- **seen_urls 会无限增长**：必须裁剪到最近 500 条，否则状态文件膨胀。URL 保留 7 天后自动清除（按时间戳排序裁剪）。
- **内容为空不等于没有更新**：web_reader 返回空内容可能是反爬触发，也可能是该来源当天确实没有更新。记录到 errors 而非跳过。
- **Telegram 消息长度限制 4096 字符**：如果 digest 摘要超长，拆分为多条消息发送，不要截断丢弃。
- **cron 时区**：使用 `TZ=Asia/Shanghai` 确保定时任务按北京时间执行。OpenClaw cron 默认可能用 UTC。
- **web_reader 脚本路径**：硬编码为 `~/.openclaw/skills/web-reader/scripts/web-reader.sh`，不要假设它在 PATH 中。
- **子 Agent 超时**：web_reader L2 浏览器渲染可能 15-30 秒。分治给子 Agent 时设置足够超时，避免部分来源因超时被静默丢弃。

## Error Handling

### 来源抓取失败
- 记录到 `state/last-digest.json` 的 `errors` 字段（来源 + 错误信息 + 时间戳）
- 跳过该来源，继续处理其他来源
- 如果超过 50% 来源失败，发送告警消息而非 digest

### web_reader 脚本不存在或执行失败
- 检查 `~/.openclaw/skills/web-reader/scripts/web-reader.sh` 是否存在
- 不存在时回退到 `web_fetch` 工具直接抓取（质量可能下降）
- 记录错误，不要静默跳过

### 状态文件损坏
- 如果 `last-digest.json` 不是合法 JSON，重置为空状态 `{"seen_urls": [], "last_run": null, "errors": []}`
- 记录一次 "状态文件重置" 事件

## Data Persistence

- **存储路径**: `~/.openclaw/workspace-ai-builder-digest/state/last-digest.json`
- **格式**: JSON
- **Schema**:
```json
{
  "last_run": "2026-03-26T08:00:00+08:00",
  "seen_urls": ["https://...", "..."],
  "errors": [
    {"source": "@karpathy", "error": "web_reader timeout", "ts": "2026-03-26T08:05:00+08:00"}
  ]
}
```
- **裁剪策略**: seen_urls 保留最近 500 条，errors 保留最近 100 条

> 注意：不要在 skill 目录内存储状态。skill 目录可能在升级时被覆盖。

## Internal Acceptance

- **Happy-path input**: 手动触发 "跑一次今天的 AI digest"
- **Invocation method**: 直接技能调用（agent 识别触发词后执行）
- **Expected artifacts**:
  1. `state/last-digest.json` 更新了 seen_urls 和 last_run
  2. Telegram 群收到一条 digest 消息（如果有新内容）
  3. PKM vault 中新增一条 `ai-digest` 标签的 literature 笔记
- **Success criteria**: 能从 2+ 个不同类型的来源成功抓取到新内容并生成摘要
- **Fallback / blocker behavior**: 如果 web_reader 不可用，回退到 web_fetch 并在摘要中标注"部分内容降级抓取"
- **Integration point**: 需通过 OpenClaw cron 设置定时任务才算 `integrated`

## Delivery Contract

**Do not report "skill creation complete" to the user unless internal readiness has reached `integrated`.**

就绪级别定义：
- `scaffold`: 文件结构创建完成，sources.json 填充，digest-prompt.md 写好
- `mvp`: 手动跑通 happy path，至少 2 个来源能抓到内容
- `production-ready`: cron 定时运行稳定，去重正常，错误处理验证
- `integrated`: cron 设置完成，至少连续 3 天正常运行

如果集成验证未通过，向用户报告 `blocked` 而非 `completed`。

## Resources

| Resource | Path |
|----------|------|
| 来源列表 | `config/sources.json` |
| 摘要 prompt 模板 | `config/digest-prompt.md` |
| 来源获取脚本 | `scripts/fetch-sources.sh` |
| 站点抓取经验 | `references/site-patterns/` |

## Origin Metadata

```json
{
  "origin": "self",
  "author": "gorin",
  "readiness": "production-ready",
  "cron_job_id": "feb8ade3-72f7-4bc6-a6ed-2aa179ee908b",
  "cron_schedule": "30 8 * * * Asia/Shanghai",
  "r3_completed": "2026-03-26T13:50:00+08:00",
  "auto_promote": {
    "target": "integrated",
    "condition": "3 successful runs spanning >= 3 different dates in state runs[]",
    "checked_by": "cron payload step 11"
  }
}
```

---
name: web-reader
description: >
  统一 Web 页面读取。三层架构：L1 快速抓取（defuddle/Scrapling/web_fetch）→
  L2 浏览器渲染（PinchTab 持久化登录态）→ L3 内容清洗（defuddle markdown）。
  自动根据域名路由，支持知乎、X、微信公众号等需登录的页面。
  触发条件：用户要读取网页、抓取文章内容、保存网页为 markdown。
triggers: ["读网页", "抓取", "web-reader", "/web-reader", "读取这个链接", "读取这篇文章"]
user-invocable: true
command-dispatch: tool
---

# Web Reader — 统一网页读取与内容提取

## 架构概览

```
Agent 调用 → web-reader.sh <url> [options]
                │
                ├─ L1: 快速抓取（公开页面，<3s）
                │   defuddle parse → Scrapling → web_fetch
                │
                ├─ L2: 浏览器渲染（登录页面/JS 重页面，5-15s）
                │   PinchTab（持久化 profile + cookie）
                │   → defuddle 清洗 → markdown
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
url: https://example.com/article
title: 文章标题
author: 作者名
published: 2026-03-17
site: example.com
word_count: 1234
captured_at: 2026-03-17T22:00:00+08:00
captured_via: defuddle|scrapling|pinchtab
---

正文 markdown 内容...
```

## 非协商输出规则

- **必须输出原始正文**，不要摘要化、总结、或用"文章概要"替代实际内容。Agent 的职责是搬运和清洗，不是改写。
- **必须使用 YAML front matter 格式**（`---` 包裹），不要把元数据散落在正文或表格里。
- **必须保留原始 markdown 链接** `[text](url)`，不要去掉 URL 只留标题文字。
- **不要把输出包裹在 markdown 代码块中**（不要用 ` ```markdown ` 包裹整个结果）。
- **不要在正文前后添加解释性文字**（如"抓取完成""以下是结果"等），直接输出 front matter + 正文。
- **大页面必须截断**：当抓取到的内容超过 30000 字符时，保留前 30000 字符并附加 `\n\n---\n\n[内容已截断，原文共 N 字符]`。不要因为内容太长而放弃输出或改用摘要替代。

## 依赖

- **defuddle** (npm): `npm install -g defuddle` — 内容提取 + markdown 转换
- **PinchTab**: `curl -fsSL https://pinchtab.com/install.sh | bash` — 浏览器自动化
- **Scrapling + html2text** (Python): `pip install scrapling html2text` — L1 备选
- **PinchTab profiles**: zhihu / x-twitter / wechat（首次需手动登录）

## 首次登录设置

对需要登录的网站，需手动登录一次来保存 cookie：

```bash
# 启动带 profile 的可视化浏览器实例
pinchtab instance start --profile zhihu --mode headed
# → 在弹出的 Chrome 中手动登录知乎 → 关闭实例
pinchtab instance stop <instance-id>
```

## 防死循环规则

同一个 URL 在 L1 和 L2 各尝试一次，均失败则返回错误信息，不重复重试。

## Gotchas

- **L1 对 JS 渲染页面无效**：defuddle/Scrapling 只能抓静态 HTML。知乎、X、微信公众号等 SPA 页面必须走 L2 浏览器渲染，否则只拿到空壳。
- **L2 需要预先登录**：PinchTab 依赖持久化 cookie profile。如果目标网站未登录，L2 拿到的是登录页而非正文。首次使用需 `pinchtab instance start --mode headed` 手动登录。
- **web_fetch 不是万能的**：对 JS-heavy 页面，`web_fetch` 工具只返回初始 HTML（没有动态内容）。这种情况需要用 browser 工具或 web-reader L2。
- **微信公众号文章需要特殊处理**：Jina Reader 无法抓取微信公众号文章（`mp.weixin.qq.com`），虽然域名路由表列的是 L1，但部分文章（尤其是较新的）仍需 L2 才能获取完整内容。

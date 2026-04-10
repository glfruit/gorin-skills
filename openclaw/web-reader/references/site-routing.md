# 站点级操作路由表

> web-reader 的 URL 正文抓取不受此表影响，仅限"搜索/热榜/feed"类站点级操作。
> 最后更新：2026-04-02

## 路由规则

1. **Public 模式站点**（不需要登录）→ `opencli-rs`
2. **bb-browser 独有站点** → `bb-browser`
3. **opencli-rs 独有站点** → `opencli-rs`
4. **重叠站点** → 按下表优先级选择
5. **兜底** → OpenClaw `browser` 工具

## opencli-rs Public 模式（不需要登录，首选）

| 站点 | 示例命令 | 说明 |
|------|---------|------|
| hackernews | `opencli-rs hackernews top --limit 10 --format json` | 技术热榜 |
| devto | `opencli-rs devto top --limit 10 --format json` | 开发社区 |
| lobsters | `opencli-rs lobsters hot --limit 10 --format json` | 技术讨论 |
| stackoverflow | `opencli-rs stackoverflow hot --limit 10 --format json` | 技术问答 |
| steam | `opencli-rs steam top-sellers --format json` | 游戏商店 |
| linux-do | `opencli-rs linux-do hot --format json` | 社区 |
| arxiv | `opencli-rs arxiv search "large language model" --format json` | 论文 |
| wikipedia | `opencli-rs wikipedia search "量子计算" --format json` | 百科 |
| apple-podcasts | `opencli-rs apple-podcasts search "AI" --format json` | 播客 |
| xiaoyuzhou | `opencli-rs xiaoyuzhou podcast --format json` | 播客 |
| bbc | `opencli-rs bbc news --format json` | 新闻 |
| hf | `opencli-rs hf top --format json` | AI 模型 |
| sinafinance | `opencli-rs sinafinance news --format json` | 财经 |

## 重叠站点路由

| 站点 | 优先用 | 理由 |
|------|--------|------|
| bilibili | **opencli-rs** | 更快，有下载能力 |
| zhihu | **opencli-rs** | 更快，有下载能力 |
| weibo | **bb-browser** | 命令更多（7 vs 2），有 feed/me/post |
| twitter/x | **opencli-rs** | 命令 3x+，有写操作 |
| xiaohongshu | **opencli-rs** | 命令 2x+，有下载/创作 |
| reddit | **opencli-rs** | 命令 2x+，有写操作 |
| youtube | **bb-browser** | 有 channel/comments/feed |
| douban | **opencli-rs** | 有 book 等多维覆盖 |
| xueqiu | **opencli-rs** | 命令略多 |
| boss | **opencli-rs** | 命令 7x（14 vs 2） |
| v2ex | **opencli-rs** | 命令 3x+ |
| linkedin | **opencli-rs** | 更快 |
| reuters | **opencli-rs** | 更快 |
| smzdm | **opencli-rs** | 更快 |
| ctrip | **opencli-rs** | 更快 |

## bb-browser 独有站点

36kr、baidu、cnblogs、csdn、eastmoney、genius、gsmarena、hupu、npm、openlibrary、producthunt、pypi、qidian、sogou（含微信文章搜索）、toutiao、youdao

```bash
# 示例
bb-browser site baidu/search "大语言模型"
bb-browser site sogou/weixin "AI agent"
bb-browser site csdn/search "Rust 异步"
bb-browser site eastmoney/stock SH600519
```

## opencli-rs 独有高价值站点

| 站点 | 说明 | 示例命令 |
|------|------|---------|
| weread | 微信读书 | `opencli-rs weread search "认知觉醒"` |
| bloomberg | 财经新闻（13 命令） | `opencli-rs bloomberg tech --format json` |
| medium | 博客 | `opencli-rs medium search "AI agent"` |
| substack | Newsletter | `opencli-rs substack feed --format json` |
| facebook | 社交 | `opencli-rs facebook search "AI" --format json` |
| instagram | 社交 | `opencli-rs instagram explore --format json` |
| tiktok | 短视频 | `opencli-rs tiktok search "AI" --format json` |
| weixin | 微信文章下载为 Markdown | `opencli-rs weixin download <url>` |
| cursor/codex/chatgpt | 桌面 App 控制 | `opencli-rs cursor status --format json` |
| notion | 桌面 App 控制 | `opencli-rs notion read <page-id>` |
| discord-app | 桌面 App 控制 | `opencli-rs discord-app status --format json` |
| doubao | 豆包 | `opencli-rs doubao search "AI"` |
| chaoxing | 超星 | `opencli-rs chaoxing search "机器学习"` |
| jimeng | 即梦 | `opencli-rs jimeng search "AI"` |
| grok | X.ai 搜索 | `opencli-rs grok search "AI"` |

## opencli-rs 特殊能力

- **文章下载**：`opencli-rs weixin download <url>` / `opencli-rs bilibili download <bvid>` / `opencli-rs zhihu download`
- **AI 生成适配器**：`opencli-rs generate <url> --ai` → 自动为新站点创建 YAML 适配器
- **云端适配器市场**：`opencli-rs search <url>` → 查找社区共享适配器
- **YAML Pipeline**：声明式数据流（fetch → evaluate → map → filter → sort → limit）

---
name: bearclaw-native
description: "Rock-solid Bear Blog publishing using OpenClaw's native browser (no Chrome extension needed). Do NOT use for reading Bear notes or non-Bear-Blog platforms."
version: 2.1.0
author: gorin
tagline: "Grip your content firmly with OpenClaw's native browser"
keywords:
  - bear blog
  - blogging
  - reliable
  - automation
  - openclaw-browser
  - native
  - retry
  - robust
  - markdown
  - publishing
---


# 🐻🦞 BearClaw Native

Rock-solid Bear Blog publishing using OpenClaw's native browser. Zero extension dependencies. 95-99% reliability.

## Key Features

- ✅ **Zero Extension Dependencies** — Uses OpenClaw's native browser
- ✅ **Managed Browser Profile** — Isolated `openclaw` instance
- ✅ **Same Reliability** — 95-99% success rate
- ✅ **All BearClaw Features** — Auto-retry, smart waiting, debug mode
- ✅ **Simpler Setup** — No Chrome extension needed

## Usage

### Create Post
```
Create a Bear Blog post using bearclaw:
- Title: "My First Post"
- Content: "Hello, world!"
- Tags: blogging, first-post
```

### Create with Options
```
Publish to Bear Blog with bearclaw-native:
- Title: "Getting Started"
- Content: |
  # Introduction
  This is my first blog post.
- Tags: blogging, tutorials
- Make discoverable: yes
- Link: getting-started
```

### Update Post
```
Update my Bear Blog post at https://myblog.bearblog.dev/my-post/:
- Title: "Updated Title"
- Content: "New content"
```

### Delete Post
```
Delete my Bear Blog post at https://myblog.bearblog.dev/old-post/
```

## Quick Setup

1. Enable browser: `openclaw browser status` → `openclaw config set browser.enabled true`
2. Login: `openclaw browser open https://bearblog.dev` → log in manually
3. Use: Just ask OpenClaw to create/update/delete posts

详见 `references/configuration-details.md`（环境变量、浏览器配置、Headless、远程浏览器、多 Profile）

## How It Works

Uses OpenClaw's browser tool: start browser → navigate to Bear Blog → snapshot page → act on elements (type/click) → smart waiting for network idle.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Browser disabled | `openclaw config set browser.enabled true` |
| Not logged in | `openclaw browser open https://bearblog.dev`, log in |
| Element not found | `BEARCLAW_DEBUG=true`, take snapshot |

详见 `references/configuration-details.md`（完整故障排除、浏览器命令、安全隐私、与 Chrome 扩展对比）

## Links

- **Bear Blog**: https://bearblog.dev
- **OpenClaw Browser Docs**: https://docs.openclaw.ai/tools/browser

---

**Version:** 2.1.0 | **License:** MIT
**"Once BearClaw grips your content, it never lets go - now with zero extension dependencies!"** 🐻🦞

## When NOT to Use

- 不用于读取 Bear 笔记（用 Bear 原生搜索或 Apple Script）。
- 不用于非 Bear Blog 平台的发布。
- 不用于需要大量自定义样式的博客（Bear Blog 主题有限）。

## Error Handling

- Bear URL scheme 失败时，检查 Bear app 是否运行。
- 博客发布 API 失败时，检查网络和认证 token。
- 图片上传失败时，检查图片大小和格式限制。

## Internal Acceptance

- 文章成功发布到 Bear Blog 并可公开访问。
- 本地 Bear 笔记同步到 XCallback URL 成功。
- 发布后 1 分钟内可在公开 URL 访问。

## Gotchas

- Bear 的 x-callback-url 对特殊字符敏感，标题含 `#` 或 `|` 会被截断。
- Bear Blog 不支持自定义域名（除非升级到付费计划）。
- 浏览器自动化的登录态可能过期，需要重新认证。

## Delivery Contract

- 发布后输出公开 URL。
- 本地 Bear 笔记的标题和标签展示。
- 失败时输出错误详情和替代方案。
**注意：本技能是大型流水线的一部分。Do **not** report completion to the user unless all dependent tools/scripts/skills have been verified as integrated.**not** report completion to the user unless all dependent tools/scripts/skills integration tests have passed.**

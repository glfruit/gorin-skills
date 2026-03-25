---
name: bearclaw-native
description: Rock-solid Bear Blog publishing using OpenClaw's native browser (no Chrome extension needed)
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

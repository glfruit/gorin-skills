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

# 🐻🦞 BearClaw Native - Native Browser Edition

**Grip your content firmly with OpenClaw's native browser - No Chrome Extension Required!**

BearClaw Native uses OpenClaw's built-in browser automation (openclaw-managed browser) for rock-solid Bear Blog publishing. Same 95-99% reliability, zero extension dependencies.

## ✨ What's New in Native Edition

- ✅ **Zero Extension Dependencies** - Uses OpenClaw's native browser
- ✅ **Managed Browser Profile** - Isolated `openclaw` browser instance
- ✅ **Same Reliability** - 95-99% success rate maintained
- ✅ **All BearClaw Features** - Auto-retry, smart waiting, debug mode
- ✅ **Simpler Setup** - No Chrome extension needed

## 📋 Prerequisites

1. **Bear Blog account** - Free at https://bearblog.dev
2. **OpenClaw with browser enabled** - Check with `openclaw browser status`
3. **Browser profile configured** - Default `openclaw` profile works out of the box

## 🚀 Quick Start

### Step 1: Verify Browser Support

```bash
# Check if browser is enabled
openclaw browser status

# If disabled, enable in config
openclaw config set browser.enabled true

# Start the browser
openclaw browser start
```

### Step 2: Login to Bear Blog

```bash
# Open Bear Blog in OpenClaw browser
openclaw browser open https://bearblog.dev

# Log in manually in the opened browser window
# Keep the browser window open
```

### Step 3: Use with OpenClaw

```
Create a Bear Blog post titled "Hello World" with content "My first post!"
```

BearClaw Native handles the rest!

## 🛠️ Configuration

### Browser Profile Setup

BearClaw Native uses OpenClaw's managed browser by default. You can customize:

```bash
# Use default openclaw profile (recommended)
openclaw config set browser.defaultProfile openclaw

# Or create a custom profile for BearClaw
openclaw browser create-profile \
  --name bearclaw \
  --cdp-port 18803 \
  --color "#FF6B35"
```

### Environment Variables

```bash
# BearClaw settings (same as Chrome version)
export BEARCLAW_TIMEOUT=30000
export BEARCLAW_DEBUG=true
export BEARCLAW_MAX_RETRIES=3
export BEARCLAW_RETRY_DELAY=2000

# Browser profile (optional, defaults to "openclaw")
export BEARCLAW_BROWSER_PROFILE=openclaw
```

## 📖 Usage

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

## 🔧 How It Works

BearClaw Native leverages OpenClaw's browser tool which provides:

### 1. **Browser Control**
```javascript
// Start browser
await openclaw.browser({
  action: 'start',
  profile: 'openclaw'
});

// Navigate to page
await openclaw.browser({
  action: 'navigate',
  url: 'https://bearblog.dev/dashboard/posts/new/',
  wait: 'networkidle'
});
```

### 2. **Page Snapshot**
```javascript
// Get AI-powered snapshot with refs
const snapshot = await openclaw.browser({
  action: 'snapshot',
  format: 'ai',  // Returns numeric refs like [12]
  interactive: true
});
```

### 3. **Element Actions**
```javascript
// Type in field using ref from snapshot
await openclaw.browser({
  action: 'act',
  kind: 'type',
  ref: 12,  // From snapshot
  text: 'My Title'
});

// Click button
await openclaw.browser({
  action: 'act',
  kind: 'click',
  ref: 23
});
```

### 4. **Smart Waiting**
```javascript
// Wait for element and network idle
await openclaw.browser({
  action: 'wait',
  selector: 'textarea[name="content"]',
  load: 'networkidle',
  timeout: 30000
});
```

## 🐛 Troubleshooting

### "Browser disabled" Error

**Solution:**
```bash
# Enable browser
openclaw config set browser.enabled true

# Restart gateway if needed
openclaw restart
```

### "NOT_LOGGED_IN" Error

**Solution:**
```bash
# Open Bear Blog in OpenClaw browser
openclaw browser open https://bearblog.dev

# Log in manually in the browser window
# Keep window open
```

### "Element not found" Error

**Enable debug mode:**
```bash
export BEARCLAW_DEBUG=true

# Take manual snapshot to see page state
openclaw browser snapshot --interactive

# Check screenshots
ls /tmp/bearclaw-*.png
```

### Browser Won't Start

**Check browser executable:**
```bash
# Verify browser configuration
openclaw config get browser

# Test browser manually
openclaw browser start
openclaw browser status
```

## 🎯 Advantages Over Chrome Extension

| Feature | Chrome Extension | Native Browser |
|---------|------------------|----------------|
| **Setup** | Extension + Chrome | Built-in |
| **Dependencies** | External | None |
| **Isolation** | Uses your Chrome | Dedicated instance |
| **Profiles** | Limited | Full control |
| **Headless** | No | Optional |
| **Remote** | Limited | Full support |

## ⚙️ Advanced Configuration

### Use Headless Mode

```bash
openclaw config set browser.headless true
openclaw browser restart
```

### Use Custom Browser

```bash
# macOS - Brave
openclaw config set browser.executablePath "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

# Linux - Brave
openclaw config set browser.executablePath "/usr/bin/brave-browser"

# Restart browser
openclaw browser restart
```

### Multiple Profiles

```json
{
  "browser": {
    "enabled": true,
    "defaultProfile": "openclaw",
    "profiles": {
      "openclaw": {
        "cdpPort": 18800,
        "color": "#FF4500"
      },
      "bearclaw": {
        "cdpPort": 18803,
        "color": "#FF6B35"
      }
    }
  }
}
```

### Remote Browser

```json
{
  "browser": {
    "profiles": {
      "remote": {
        "cdpUrl": "http://10.0.0.42:9222",
        "color": "#00AA00"
      }
    }
  }
}
```

## 📚 OpenClaw Browser Commands

Useful commands for debugging:

```bash
# Browser status
openclaw browser status

# List tabs
openclaw browser tabs

# Take snapshot
openclaw browser snapshot --interactive

# Take screenshot
openclaw browser screenshot --full-page

# Navigate
openclaw browser navigate https://bearblog.dev

# View console errors
openclaw browser errors

# View network requests
openclaw browser requests --filter api
```

## 🔒 Security & Privacy

- ✅ **Isolated profile** - Separate from personal browsing
- ✅ **Local control** - Loopback-only by default
- ✅ **Session isolation** - Each skill session is independent
- ✅ **No data leakage** - Dedicated user data directory

## 💡 Tips

1. **Keep browser running** - Start once, reuse for multiple operations
2. **Use debug mode** - `export BEARCLAW_DEBUG=true` for troubleshooting
3. **Take snapshots** - `openclaw browser snapshot` shows page state
4. **Check logs** - OpenClaw logs show detailed browser operations
5. **Test manually** - Use `openclaw browser` CLI to test operations

## 🆚 Comparison with Original

| Aspect | Chrome Extension | Native Browser |
|--------|------------------|----------------|
| **Setup complexity** | High | Low |
| **External dependencies** | Chrome Extension | None |
| **Browser isolation** | Shared Chrome | Dedicated |
| **Headless support** | No | Yes |
| **Remote support** | Limited | Full |
| **Multi-profile** | Manual | Built-in |
| **Reliability** | 95-99% | 95-99% |

## 🔗 Links

- **Bear Blog**: https://bearblog.dev
- **OpenClaw Browser Docs**: https://docs.openclaw.ai/tools/browser
- **OpenClaw**: https://openclaw.ai

## 📄 License

MIT License

## 🙏 Credits

Built on OpenClaw's powerful native browser automation. Special thanks to the OpenClaw team for the excellent browser API.

## 📝 Notes

- Requires OpenClaw with browser support enabled
- Uses Playwright under the hood for reliable automation
- Supports all Chromium-based browsers (Chrome, Brave, Edge, Chromium)
- Can run headless for server deployments
- Fully compatible with OpenClaw's remote browser features

---

**Version:** 2.1.0  
**Last Updated:** February 2026  
**Compatibility:** OpenClaw with native browser support

**"Once BearClaw grips your content, it never lets go - now with zero extension dependencies!"** 🐻🦞

# BearClaw Native Reference

## Prerequisites

1. Bear Blog account — Free at https://bearblog.dev
2. OpenClaw with browser enabled — `openclaw browser status`
3. Browser profile configured — Default `openclaw` profile works

## Quick Start

### Step 1: Verify Browser

```bash
openclaw browser status
openclaw config set browser.enabled true  # if disabled
openclaw browser start
```

### Step 2: Login

```bash
openclaw browser open https://bearblog.dev
# Log in manually in the opened browser window
```

### Step 3: Use with OpenClaw

```
Create a Bear Blog post titled "Hello World" with content "My first post!"
```

## Configuration

### Browser Profile

```bash
# Use default openclaw profile (recommended)
openclaw config set browser.defaultProfile openclaw

# Or create custom profile
openclaw browser create-profile --name bearclaw --cdp-port 18803 --color "#FF6B35"
```

### Environment Variables

```bash
export BEARCLAW_TIMEOUT=30000
export BEARCLAW_DEBUG=true
export BEARCLAW_MAX_RETRIES=3
export BEARCLAW_RETRY_DELAY=2000
export BEARCLAW_BROWSER_PROFILE=openclaw
```

## How It Works

BearClaw Native leverages OpenClaw's browser tool:

### 1. Browser Control
```javascript
await openclaw.browser({ action: 'start', profile: 'openclaw' });
await openclaw.browser({ action: 'navigate', url: 'https://bearblog.dev/dashboard/posts/new/', wait: 'networkidle' });
```

### 2. Page Snapshot
```javascript
const snapshot = await openclaw.browser({ action: 'snapshot', format: 'ai', interactive: true });
```

### 3. Element Actions
```javascript
await openclaw.browser({ action: 'act', kind: 'type', ref: 12, text: 'My Title' });
await openclaw.browser({ action: 'act', kind: 'click', ref: 23 });
```

### 4. Smart Waiting
```javascript
await openclaw.browser({ action: 'wait', selector: 'textarea[name="content"]', load: 'networkidle', timeout: 30000 });
```

## Advanced Configuration

### Headless Mode
```bash
openclaw config set browser.headless true
openclaw browser restart
```

### Custom Browser
```bash
openclaw config set browser.executablePath "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
openclaw browser restart
```

### Multiple Profiles
```json
{
  "browser": {
    "enabled": true,
    "defaultProfile": "openclaw",
    "profiles": {
      "openclaw": { "cdpPort": 18800, "color": "#FF4500" },
      "bearclaw": { "cdpPort": 18803, "color": "#FF6B35" }
    }
  }
}
```

### Remote Browser
```json
{
  "browser": {
    "profiles": {
      "remote": { "cdpUrl": "http://10.0.0.42:9222", "color": "#00AA00" }
    }
  }
}
```

## OpenClaw Browser Commands

```bash
openclaw browser status
openclaw browser tabs
openclaw browser snapshot --interactive
openclaw browser screenshot --full-page
openclaw browser navigate https://bearblog.dev
openclaw browser errors
openclaw browser requests --filter api
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Browser disabled" | `openclaw config set browser.enabled true` |
| "NOT_LOGGED_IN" | `openclaw browser open https://bearblog.dev`, log in manually |
| "Element not found" | Enable `BEARCLAW_DEBUG=true`, take manual snapshot |
| Browser won't start | `openclaw config get browser`, test manually |

## Security & Privacy

- ✅ Isolated profile — Separate from personal browsing
- ✅ Local control — Loopback-only by default
- ✅ Session isolation — Each skill session is independent
- ✅ No data leakage — Dedicated user data directory

## Advantages Over Chrome Extension

| Feature | Chrome Extension | Native Browser |
|---------|------------------|----------------|
| **Setup** | Extension + Chrome | Built-in |
| **Dependencies** | External | None |
| **Isolation** | Uses your Chrome | Dedicated instance |
| **Profiles** | Limited | Full control |
| **Headless** | No | Optional |
| **Remote** | Limited | Full support |

## Tips

1. Keep browser running — Start once, reuse
2. Use debug mode — `BEARCLAW_DEBUG=true`
3. Take snapshots — `openclaw browser snapshot`
4. Check logs — OpenClaw logs show detailed operations
5. Test manually — `openclaw browser` CLI

## Notes

- Requires OpenClaw with browser support enabled
- Uses Playwright under the hood
- Supports all Chromium-based browsers
- Can run headless for server deployments
- Fully compatible with remote browser features

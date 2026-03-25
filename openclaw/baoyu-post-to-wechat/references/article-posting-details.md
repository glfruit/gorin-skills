# Article Posting Details Reference

## Image-Text Posting (图文)

For short posts with multiple images (up to 9):

```bash
npx -y bun ${SKILL_DIR}/scripts/wechat-browser.ts --markdown article.md --images ./images/
npx -y bun ${SKILL_DIR}/scripts/wechat-browser.ts --title "标题" --content "内容" --image img.png --submit
```

## Article Workflow Steps Detail

### Step 0: Load Preferences

Resolve and store defaults:
- `default_theme` (default `default`)
- `default_color` (omit if not set)
- `default_author`
- `need_open_comment` (default `1`)
- `only_fans_can_comment` (default `0`)

### Step 1: Input Type Detection

| Input Type | Detection | Action |
|------------|-----------|--------|
| HTML file | Path ends with `.html` | Skip to Step 4 |
| Markdown file | Path ends with `.md` | Continue to Step 2 |
| Plain text | Not a file path | Save to markdown, then Step 2 |

**Slug Examples**: "Understanding AI Models" → `understanding-ai-models`, "人工智能的未来" → `ai-future`

### Step 2: Check Markdown-to-HTML Skill

```bash
test -f skills/baoyu-markdown-to-html/SKILL.md && echo "found"
```

If not found, suggest installation of `baoyu-markdown-to-html`.

### Step 3: Convert Markdown to HTML

Theme resolution priority: CLI `--theme` → EXTEND.md → `default`
Color resolution priority: CLI `--color` → EXTEND.md → omit

```bash
npx -y bun ${MD_TO_HTML_SKILL_DIR}/scripts/main.ts <markdown_file> --theme <theme> [--color <color>]
```

**CRITICAL**: Always include `--theme` parameter.

### Step 4: Metadata Validation

| Field | If Missing |
|-------|------------|
| Title | Prompt user or auto-generate from first H1/H2 |
| Summary | Prompt user or truncate first paragraph to 120 chars |
| Author | CLI → frontmatter → EXTEND.md `default_author` |

**Cover Image** (required for `article_type=news`): CLI → frontmatter → `imgs/cover.png` → first inline image → request.

### Step 5: Publishing Method & Credentials

**API** (Recommended): Fast, needs credentials.
**Browser**: Slow, needs Chrome login.

**API credential check**:
```bash
test -f .openclaw/skills-config/baoyu/.env && grep -q "WECHAT_APP_ID" .openclaw/skills-config/baoyu/.env && echo "project"
test -f "$HOME/.openclaw/skills-config/baoyu/.env" && grep -q "WECHAT_APP_ID" "$HOME/.openclaw/skills-config/baoyu/.env" && echo "user"
```

**If missing**: Guide user to https://mp.weixin.qq.com → 开发 → 基本配置 → copy AppID/AppSecret.

### Step 6: Publish Commands

**API**:
```bash
npx -y bun ${SKILL_DIR}/scripts/wechat-api.ts <html_file> [--title ...] [--summary ...] [--author ...] [--cover ...]
```

Payload: `POST https://api.weixin.qq.com/cgi-bin/draft/add?access_token=ACCESS_TOKEN`
- `article_type`: `news` (default) or `newspic`
- For `news`: include `thumb_media_id` (cover required)
- Always include: `need_open_comment`, `only_fans_can_comment`

**Browser**:
```bash
npx -y bun ${SKILL_DIR}/scripts/wechat-article.ts --html <html_file>
```

### Step 7: Completion Report

Include: input type, method, theme, title, summary, image count, comment settings, draft link, files created.

## Pre-flight Check

```bash
npx -y bun ${SKILL_DIR}/scripts/check-permissions.ts
```

Checks: Chrome, profile isolation, Bun, Accessibility, clipboard, paste keystroke, API credentials.

| Check | Fix |
|-------|-----|
| Chrome | Install or set `WECHAT_BROWSER_CHROME_PATH` |
| Profile dir | Ensure writable |
| Bun runtime | `curl -fsSL https://bun.sh/install \| bash` |
| Accessibility | System Settings → Privacy & Security → Accessibility |
| API credentials | Set in `.openclaw/skills-config/baoyu/.env` |

## Feature Comparison

| Feature | Image-Text | Article (API) | Article (Browser) |
|---------|------------|---------------|-------------------|
| Plain text input | ✗ | ✓ | ✓ |
| HTML input | ✗ | ✓ | ✓ |
| Markdown input | Title/content | ✓ (via skill) | ✓ (via skill) |
| Multiple images | ✓ (up to 9) | ✓ (inline) | ✓ (inline) |
| Themes | ✗ | ✓ | ✓ |
| Auto-generate metadata | ✗ | ✓ | ✓ |
| Comment control | ✗ | ✓ | ✗ |
| Requires Chrome | ✓ | ✗ | ✓ |
| Requires API credentials | ✗ | ✓ | ✗ |
| Speed | Medium | Fast | Slow |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No markdown-to-html skill | Install `baoyu-markdown-to-html` |
| Missing API credentials | Follow guided setup in Step 5 |
| Access token error | Check credentials validity |
| Not logged in (browser) | First run opens browser - scan QR |
| Chrome not found | Set `WECHAT_BROWSER_CHROME_PATH` |
| No cover image | Add frontmatter or place `imgs/cover.png` |
| Wrong comment defaults | Check EXTEND.md keys |
| Paste fails | Check clipboard permissions |

## Prerequisites

- **API method**: WeChat API credentials in `.openclaw/skills-config/baoyu/.env`
- **Browser method**: Google Chrome, logged in session
- **Markdown**: A markdown-to-html skill installed
- **Config priority**: env vars → `<cwd>/.openclaw/skills-config/baoyu/.env` → `~/.openclaw/skills-config/baoyu/.env`

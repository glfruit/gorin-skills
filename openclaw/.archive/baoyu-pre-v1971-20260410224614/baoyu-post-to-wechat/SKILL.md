---
name: baoyu-post-to-wechat
description: Posts content to WeChat Official Account (微信公众号) via API or Chrome CDP. Supports article posting (文章) with HTML, markdown, or plain text input, and image-text posting (贴图, formerly 图文) with multiple images. Use when user mentions "发布公众号", "post to wechat", "微信公众号", or "贴图/图文/文章".
---

# Post to WeChat Official Account

## Language

Match user's language. Chinese input → Chinese response. English input → English response.

## Script Directory

| Script | Purpose |
|--------|---------|
| `scripts/wechat-browser.ts` | Image-text posts (图文) |
| `scripts/wechat-article.ts` | Article posting via browser (文章) |
| `scripts/wechat-api.ts` | Article posting via API (文章) |
| `scripts/check-permissions.ts` | Verify environment & permissions |

## Preferences (EXTEND.md)

Check project-level first, then user-level:
```bash
test -f .openclaw/skills-config/baoyu/baoyu-post-to-wechat/EXTEND.md && echo "project"
test -f "$HOME/.openclaw/skills-config/baoyu/baoyu-post-to-wechat/EXTEND.md" && echo "user"
```

If not found → run first-time setup: `references/config/first-time-setup.md`

**Supports**: Default theme/color/publishing method/author/comment switches/Chrome profile

**Theme options**: default, grace, simple, modern
**Color presets**: blue, green, vermilion, yellow, purple, sky, rose, olive, black, gray, pink, red, orange (or hex)
**Value priority**: CLI → Frontmatter → EXTEND.md → Skill defaults

**Key defaults**: `need_open_comment: 1`, `only_fans_can_comment: 0`

## Image-Text Posting (图文)

```bash
npx -y bun ${SKILL_DIR}/scripts/wechat-browser.ts --markdown article.md --images ./images/
npx -y bun ${SKILL_DIR}/scripts/wechat-browser.ts --title "标题" --content "内容" --image img.png --submit
```

详见 `references/image-text-posting.md`

## Article Posting Workflow (文章)

```
Publishing Progress:
- [ ] Step 0: Load preferences (EXTEND.md)
- [ ] Step 1: Determine input type
- [ ] Step 2: Check markdown-to-html skill
- [ ] Step 3: Convert to HTML
- [ ] Step 4: Validate metadata (title, summary, cover)
- [ ] Step 5: Select method and configure credentials
- [ ] Step 6: Publish to WeChat
- [ ] Step 7: Report completion
```

### Step 0: Load Preferences

Check EXTEND.md. If not found, complete first-time setup BEFORE other steps.

### Step 1: Determine Input Type

HTML → skip to Step 4. Markdown → Step 2. Plain text → save to markdown → Step 2.

### Step 2: Check Markdown-to-HTML Skill

```bash
test -f skills/baoyu-markdown-to-html/SKILL.md && echo "found"
```

If not found, suggest installation.

### Step 3: Convert to HTML

Theme: CLI → EXTEND.md → `default`. Color: CLI → EXTEND.md → omit.
```bash
npx -y bun ${MD_TO_HTML_SKILL_DIR}/scripts/main.ts <file> --theme <theme> [--color <color>]
```

### Step 4: Validate Metadata

Title/summary/author. Cover image required for `news` type.

### Step 5: Publishing Method

API (recommended, fast) or Browser (slow, Chrome needed). Configure credentials if needed.

### Step 6: Publish

API: `scripts/wechat-api.ts` | Browser: `scripts/wechat-article.ts`

### Step 7: Report

Include method, theme, title, summary, images, comments, draft link.

详见 `references/article-posting-details.md`（完整步骤细节、凭证配置、API payload 规则）

## Pre-flight Check

```bash
npx -y bun ${SKILL_DIR}/scripts/check-permissions.ts
```

详见 `references/article-posting-details.md`（检查项和修复方案）

## References

| File | Content |
|------|---------|
| `references/image-text-posting.md` | Image-text parameters, auto-compression |
| `references/article-posting-details.md` | Article workflow steps, credentials, troubleshooting |
| `references/article-posting.md` | Article themes, image handling |
| `references/config/first-time-setup.md` | First-time setup flow |

## Extension Support

Custom configurations via EXTEND.md. See **Preferences** section for paths and supported options.

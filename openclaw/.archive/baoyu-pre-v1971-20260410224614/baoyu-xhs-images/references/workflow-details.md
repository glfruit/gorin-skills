# Workflow Details Reference

## Step 0: Load Preferences (EXTEND.md)

**CRITICAL**: If EXTEND.md not found, MUST complete first-time setup before ANY other steps.

Use Bash to check EXTEND.md existence (priority order):

```bash
# Check project-level first
test -f .openclaw/skills-config/baoyu/baoyu-xhs-images/EXTEND.md && echo "project"

# Then user-level
test -f "$HOME/.openclaw/skills-config/baoyu/baoyu-xhs-images/EXTEND.md" && echo "user"
```

| Path | Location |
|------|----------|
| `.openclaw/skills-config/baoyu/baoyu-xhs-images/EXTEND.md` | Project directory |
| `$HOME/.openclaw/skills-config/baoyu/baoyu-xhs-images/EXTEND.md` | User home |

**First-Time Setup**: See `references/config/first-time-setup.md`

**EXTEND.md Supports**: Watermark | Preferred style/layout | Custom style definitions | Language preference

## Step 2: Confirmation 1 - Content Understanding

**Use AskUserQuestion** for:
1. Core selling point (multiSelect: true)
2. Target audience
3. Style preference: Authentic sharing / Professional review / Aesthetic mood / Auto
4. Additional context (optional)

## Step 3: Outline Format

Each strategy outline uses YAML front matter + content:

```yaml
---
strategy: a  # a, b, or c
name: Story-Driven
style: warm
style_reason: "Warm tones enhance emotional storytelling"
elements:
  background: solid-pastel
  decorations: [clouds, stars-sparkles]
  emphasis: star-burst
  typography: highlight
layout: balanced
image_count: 5
---

## P1 Cover
**Type**: cover
**Hook**: "入冬后脸不干了🥹终于找到对的面霜"
**Visual**: Product hero shot with cozy winter atmosphere
**Layout**: sparse

## P2 Problem
**Type**: pain-point
**Message**: Previous struggles with dry skin
**Visual**: Before state, relatable scenario
**Layout**: balanced
```

**Differentiation requirements**:
- Each strategy MUST have different outline structure AND different recommended style
- A typically 4-6 pages, B typically 3-5, C typically 3-4
- Include `style_reason` explaining why this style fits
- Reference: `references/workflows/outline-template.md`

## Step 4: Confirmation 2 - Selection Details

**Question 1: Outline Strategy** — A/B/C/Combine

**Question 2: Visual Style** — Use recommended / Select from gallery / Custom

**Question 3: Visual Elements** (after style selection):
- Background: solid-pastel / solid-saturated / gradient-linear / gradient-radial / paper-texture / grid
- Decorations: hearts / stars-sparkles / flowers / clouds / leaves / confetti
- Or custom preferences

## Step 5: Image Generation Details

**Visual Consistency — Reference Image Chain**:
1. Generate image 1 (cover) FIRST — without `--ref`
2. Use image 1 as `--ref` for ALL remaining images (2, 3, ..., N)

**Watermark** (if enabled): See `references/config/watermark-guide.md`

**Session Management**: Generate session ID `xhs-{topic-slug}-{timestamp}`, use for all images

## Step 6: Completion Report Format

```
Xiaohongshu Infographic Series Complete!

Topic: [topic]
Strategy: [A/B/C/Combined]
Style: [style name]
Layout: [layout name or "varies"]
Location: [directory path]
Images: N total

✓ analysis.md
✓ outline-strategy-a.md / b.md / c.md
✓ outline.md (selected: [strategy])

Files:
- 01-cover-[slug].png ✓ Cover (sparse)
- 02-content-[slug].png ✓ Content (balanced)
- ...
```

## Image Modification

| Action | Steps |
|--------|-------|
| **Edit** | **Update prompt file FIRST** → Regenerate with same session ID |
| **Add** | Specify position → Create prompt → Generate → Renumber subsequent (NN+1) → Update outline |
| **Delete** | Remove files → Renumber subsequent (NN-1) → Update outline |

## File Structure

```
xhs-images/{topic-slug}/
├── source-{slug}.{ext}
├── analysis.md
├── outline-strategy-a.md / b.md / c.md
├── outline.md
├── prompts/
│   ├── 01-cover-[slug].md
│   └── ...
├── 01-cover-[slug].png
├── 02-content-[slug].png
└── NN-ending-[slug].png
```

**Slug**: 2-4 words, kebab-case. **Conflict**: Append timestamp if directory exists.

## Content Breakdown Principles

1. **Cover (Image 1)**: Hook + visual impact → `sparse` layout
2. **Content (Middle)**: Core value per image → `balanced`/`dense`/`list`/`comparison`/`flow`
3. **Ending (Last)**: CTA / summary → `sparse` or `balanced`

**Style × Layout Matrix** (✓✓ = highly recommended, ✓ = works well):

| | sparse | balanced | dense | list | comparison | flow | mindmap | quadrant |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| cute | ✓✓ | ✓✓ | ✓ | ✓✓ | ✓ | ✓ | ✓ | ✓ |
| fresh | ✓✓ | ✓✓ | ✓ | ✓ | ✓ | ✓✓ | ✓ | ✓ |
| warm | ✓✓ | ✓✓ | ✓ | ✓ | ✓✓ | ✓ | ✓ | ✓ |
| bold | ✓✓ | ✓ | ✓ | ✓✓ | ✓✓ | ✓ | ✓ | ✓✓ |
| minimal | ✓✓ | ✓✓ | ✓✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| retro | ✓✓ | ✓✓ | ✓ | ✓✓ | ✓ | ✓ | ✓ | ✓ |
| pop | ✓✓ | ✓✓ | ✓ | ✓✓ | ✓✓ | ✓ | ✓ | ✓ |
| notion | ✓✓ | ✓✓ | ✓✓ | ✓✓ | ✓✓ | ✓✓ | ✓✓ | ✓✓ |
| chalkboard | ✓✓ | ✓✓ | ✓✓ | ✓✓ | ✓ | ✓✓ | ✓✓ | ✓ |
| study-notes | ✗ | ✓ | ✓✓ | ✓✓ | ✓ | ✓ | ✓✓ | ✓ |

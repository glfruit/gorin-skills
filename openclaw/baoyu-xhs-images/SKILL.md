---
name: baoyu-xhs-images
description: Generates Xiaohongshu (Little Red Book) infographic series with 10 visual styles and 8 layouts. Breaks content into 1-10 cartoon-style images optimized for XHS engagement. Use when user mentions "小红书图片", "XHS images", "RedNote infographics", "小红书种草", or wants social media infographics for Chinese platforms.
---

# Xiaohongshu Infographic Series Generator

Break down complex content into eye-catching infographic series for Xiaohongshu with multiple style options.

## Usage

```bash
/baoyu-xhs-images posts/ai-future/article.md
/baoyu-xhs-images posts/ai-future/article.md --style notion
/baoyu-xhs-images posts/ai-future/article.md --layout dense
/baoyu-xhs-images posts/ai-future/article.md --style notion --layout list
/baoyu-xhs-images  # Then paste content
```

## Options

| Option | Description |
|--------|-------------|
| `--style <name>` | Visual style (see Style Gallery) |
| `--layout <name>` | Information layout (see Layout Gallery) |

## Two Dimensions

| Dimension | Controls | Options |
|-----------|----------|---------|
| **Style** | Visual aesthetics | cute, fresh, warm, bold, minimal, retro, pop, notion, chalkboard, study-notes |
| **Layout** | Information structure | sparse, balanced, dense, list, comparison, flow, mindmap, quadrant |

Style × Layout can be freely combined.

## Style Gallery

| Style | Description |
|-------|-------------|
| `cute` (Default) | Sweet, adorable, girly - classic XHS aesthetic |
| `fresh` | Clean, refreshing, natural |
| `warm` | Cozy, friendly, approachable |
| `bold` | High impact, attention-grabbing |
| `minimal` | Ultra-clean, sophisticated |
| `retro` | Vintage, nostalgic, trendy |
| `pop` | Vibrant, energetic, eye-catching |
| `notion` | Minimalist hand-drawn line art, intellectual |
| `chalkboard` | Colorful chalk on black board, educational |
| `study-notes` | Realistic handwritten photo style |

Detailed style definitions: `references/presets/<style>.md`

## Layout Gallery

| Layout | Description |
|--------|-------------|
| `sparse` (Default) | Minimal information, maximum impact |
| `balanced` | Standard content layout |
| `dense` | High information density |
| `list` | Enumeration and ranking |
| `comparison` | Side-by-side contrast |
| `flow` | Process and timeline |
| `mindmap` | Center radial mind map |
| `quadrant` | Four-quadrant layout |

Detailed layout definitions: `references/elements/canvas.md`

## Auto Selection

详见 `references/workflow-details.md`（Auto Selection 表、Outline Strategies、Style × Layout Matrix）

## Workflow

```
XHS Infographic Progress:
- [ ] Step 0: Check preferences (EXTEND.md) ⛔ BLOCKING
- [ ] Step 1: Analyze content → analysis.md
- [ ] Step 2: Confirmation 1 - Content understanding ⚠️ REQUIRED
- [ ] Step 3: Generate 3 outline + style variants
- [ ] Step 4: Confirmation 2 - Outline & style & elements ⚠️ REQUIRED
- [ ] Step 5: Generate images (sequential)
- [ ] Step 6: Completion report
```

### Flow

```
Input → [Step 0: Preferences] → Analyze → [Confirm 1] → 3 Outlines → [Confirm 2] → Generate → Complete
```

### Step 0: Load Preferences ⛔ BLOCKING

Check EXTEND.md. If not found, complete first-time setup BEFORE any other steps.

详见 `references/config/first-time-setup.md` | Schema: `references/config/preferences-schema.md`

### Step 1: Analyze Content → `analysis.md`

Read source, save if needed (backup rule for existing files), deep analysis following `references/workflows/analysis-framework.md`.

### Step 2: Confirmation 1 ⚠️ REQUIRED

Validate understanding + collect missing info. Ask: core selling point, target audience, style preference, additional context.

### Step 3: Generate 3 Outline + Style Variants

Three strategies with different outlines AND recommended styles:
- A: Story-driven (warm, cute, fresh)
- B: Information-dense (notion, minimal, chalkboard)
- C: Visual-first (bold, pop, retro)

详见 `references/workflow-details.md`（outline format, differentiation requirements）

### Step 4: Confirmation 2 ⚠️ REQUIRED

User chooses: outline strategy, visual style, visual elements customization.

详见 `references/workflow-details.md`（question details, element options）

### Step 5: Generate Images

1. Generate cover first (no --ref), then use cover as --ref for all remaining images
2. Save prompts to `prompts/NN-{type}-[slug].md`
3. Watermark if enabled (see `references/config/watermark-guide.md`)
4. Report progress after each

### Step 6: Completion Report

详见 `references/workflow-details.md`（report format）

## References

| File | Content |
|------|---------|
| `references/workflow-details.md` | Step details, file structure, modification, style×layout matrix |
| `references/presets/<style>.md` | Element combination definitions per style |
| `references/elements/canvas.md` | Aspect ratios, safe zones, grid layouts |
| `references/elements/image-effects.md` | Cutout, stroke, filters |
| `references/elements/typography.md` | Decorated text, tags, text direction |
| `references/elements/decorations.md` | Emphasis marks, backgrounds, doodles, frames |
| `references/workflows/analysis-framework.md` | Content analysis framework |
| `references/workflows/outline-template.md` | Outline template with layout guide |
| `references/workflows/prompt-assembly.md` | Prompt assembly guide |
| `references/config/preferences-schema.md` | EXTEND.md schema |
| `references/config/first-time-setup.md` | First-time setup flow |
| `references/config/watermark-guide.md` | Watermark configuration |

## Notes

- Auto-retry once on failure | Cartoon alternatives for sensitive figures
- Use confirmed language preference | Maintain style consistency
- **Two confirmation points required** (Steps 2 & 4) - do not skip

## Extension Support

Custom configurations via EXTEND.md. See **Step 0** for paths and supported options.

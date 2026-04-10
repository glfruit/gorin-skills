---
name: baoyu-slide-deck
description: Generates professional slide deck images from content. Creates outlines with style instructions, then generates individual slide images. Use when user asks to "create slides", "make a presentation", "generate deck", "slide deck", or "PPT".
---

# Slide Deck Generator

Transform content into professional slide deck images.

## Usage

```bash
/baoyu-slide-deck path/to/content.md
/baoyu-slide-deck path/to/content.md --style sketch-notes
/baoyu-slide-deck path/to/content.md --audience executives
/baoyu-slide-deck path/to/content.md --lang zh
/baoyu-slide-deck path/to/content.md --slides 10
/baoyu-slide-deck path/to/content.md --outline-only
/baoyu-slide-deck  # Then paste content
```

## Script Directory

**Agent Execution Instructions**:
1. Determine this SKILL.md file's directory path as `SKILL_DIR`
2. Script path = `${SKILL_DIR}/scripts/<script-name>.ts`

| Script | Purpose |
|--------|---------|
| `scripts/merge-to-pptx.ts` | Merge slides into PowerPoint |
| `scripts/merge-to-pdf.ts` | Merge slides into PDF |

## Options

| Option | Description |
|--------|-------------|
| `--style <name>` | Visual style: preset name, `custom`, or custom style name |
| `--audience <type>` | Target: beginners, intermediate, experts, executives, general |
| `--lang <code>` | Output language (en, zh, ja, etc.) |
| `--slides <number>` | Target slide count (8-25 recommended, max 30) |
| `--outline-only` | Generate outline only, skip image generation |
| `--prompts-only` | Generate outline + prompts, skip images |
| `--images-only` | Generate images from existing prompts directory |
| `--regenerate <N>` | Regenerate specific slide(s): `--regenerate 3` or `--regenerate 2,5,8` |

**Slide Count by Content Length**:
| Content | Slides |
|---------|--------|
| < 1000 words | 5-10 |
| 1000-3000 words | 10-18 |
| 3000-5000 words | 15-25 |
| > 5000 words | 20-30 (consider splitting) |

## Style System

16 presets available (blueprint, chalkboard, corporate, minimal, sketch-notes, watercolor, dark-atmospheric, notion, bold-editorial, editorial-infographic, fantasy-animation, intuition-machine, pixel-art, scientific, vector-illustration, vintage).

Each preset maps to 4 dimensions: texture, mood, typography, density. Custom dimensions can also be selected.

详见 `references/style-system.md`（完整预设表、维度定义、自动选择规则）。

## Design Philosophy

Decks designed for **reading and sharing**, not live presentation. See `references/design-guidelines.md`.

## File Management

Output to `slide-deck/{topic-slug}/`. See `references/file-management.md`（目录结构、slug 规则、冲突处理、备份规则）。

## Language Handling

Detection: `--lang` > EXTEND.md > conversation language > source language. See `references/language-handling.md`.

## Workflow

Copy this checklist and check off items as you complete them:

```
Slide Deck Progress:
- [ ] Step 1: Setup & Analyze
  - [ ] 1.1 Load preferences (EXTEND.md)
  - [ ] 1.2 Analyze content
  - [ ] 1.3 Check existing ⚠️ REQUIRED
- [ ] Step 2: Confirmation ⚠️ REQUIRED (Round 1, optional Round 2)
- [ ] Step 3: Generate outline
- [ ] Step 4: Review outline (conditional)
- [ ] Step 5: Generate prompts
- [ ] Step 6: Review prompts (conditional)
- [ ] Step 7: Generate images
- [ ] Step 8: Merge to PPTX/PDF
- [ ] Step 9: Output summary
```

### Flow

```
Input → Preferences → Analyze → [Check Existing?] → Confirm (1-2 rounds) → Outline → [Review Outline?] → Prompts → [Review Prompts?] → Images → Merge → Complete
```

### Step 1: Setup & Analyze

**1.1 Load Preferences (EXTEND.md)**

Check project-level first, then user-level:
```bash
test -f .openclaw/skills-config/baoyu/baoyu-slide-deck/EXTEND.md && echo "project"
test -f "$HOME/.openclaw/skills-config/baoyu/baoyu-slide-deck/EXTEND.md" && echo "user"
```

When found → read, parse, output summary. Schema: `references/config/preferences-schema.md`.

When not found → first-time setup (proceed with defaults).

**1.2 Analyze Content**

1. Save source content (backup existing `source.md`)
2. Follow `references/analysis-framework.md` for content analysis
3. Analyze content signals for style recommendations
4. Detect source language, determine slide count, generate topic slug

**1.3 Check Existing Content** ⚠️ REQUIRED

Use Bash to check if output directory exists. If exists → ask user (see `references/file-management.md`).

Save to `analysis.md`: topic, audience, content signals, recommended style, slide count, language.

### Step 2: Confirmation ⚠️ REQUIRED

Two-round confirmation. Round 1: always (5 questions: style, audience, slides, outline review, prompt review). Round 2: only if "Custom dimensions" selected (4 dimension questions).

详见 `references/confirmation-workflow.md`（完整的 AskUserQuestion 格式）。

After confirmation: update `analysis.md`, store review flags → Step 3.

### Step 3: Generate Outline

- If preset → read `references/styles/{preset}.md`
- If custom dimensions → read `references/dimensions/*.md` and combine
- Follow `references/outline-template.md` for structure
- Save as `outline.md`
- If `--outline-only`, stop here

### Step 4: Review Outline (Conditional)

Skip if user selected "No" in Step 2. Display slide summary table, ask user to confirm/edit/regenerate.

详见 `references/review-workflow.md`。

### Step 5: Generate Prompts

1. Read `references/base-prompt.md`
2. For each slide: extract STYLE_INSTRUCTIONS from outline, add slide-specific content
3. Save to `prompts/` directory (backup existing files)
4. If `--prompts-only`, stop here

### Step 6: Review Prompts (Conditional)

Skip if user selected "No" in Step 2. Display prompt list, ask user to confirm/edit/regenerate.

详见 `references/review-workflow.md`。

### Step 7: Generate Images

1. Select image generation skill
2. Generate session ID: `slides-{topic-slug}-{timestamp}`
3. Generate images sequentially (backup existing)
4. Report progress, auto-retry once on failure

For `--images-only`: start here. For `--regenerate N`: only specified slides.

### Step 8: Merge to PPTX and PDF

```bash
npx -y bun ${SKILL_DIR}/scripts/merge-to-pptx.ts <slide-deck-dir>
npx -y bun ${SKILL_DIR}/scripts/merge-to-pdf.ts <slide-deck-dir>
```

### Step 9: Output Summary

Output: topic, style, location, slide list, file paths (outline, PPTX, PDF). Language: user's preferred language.

## Partial Workflows

详见 `references/partial-workflows.md`（--outline-only, --prompts-only, --images-only, --regenerate）。

## Slide Modification

详见 `references/modification-guide.md`（编辑/添加/删除幻灯片、重编号、备份规则）。

## References

| File | Content |
|------|---------|
| `references/style-system.md` | Presets, dimensions, auto-selection rules |
| `references/analysis-framework.md` | Content analysis for presentations |
| `references/outline-template.md` | Outline structure and format |
| `references/base-prompt.md` | Base prompt for image generation |
| `references/confirmation-workflow.md` | Step 2 AskUserQuestion formats |
| `references/review-workflow.md` | Step 4 & 6 review formats |
| `references/modification-guide.md` | Edit, add, delete slide workflows |
| `references/partial-workflows.md` | --outline-only, --prompts-only, etc. |
| `references/file-management.md` | Directory structure, slug, conflict handling |
| `references/language-handling.md` | Language detection and rules |
| `references/content-rules.md` | Content and style guidelines |
| `references/design-guidelines.md` | Audience, typography, colors, visual elements |
| `references/layouts.md` | Layout options and selection tips |
| `references/dimensions/*.md` | Dimension specifications (texture, mood, typography, density) |
| `references/dimensions/presets.md` | Preset → dimension mapping |
| `references/styles/<style>.md` | Full style specifications (legacy) |
| `references/config/preferences-schema.md` | EXTEND.md structure |

## Notes

- Image generation: 10-30 seconds per slide
- Auto-retry once on generation failure
- Use stylized alternatives for sensitive public figures
- Maintain style consistency via session ID
- **Step 2 confirmation required** - do not skip
- **Step 4 conditional** - only if user requested outline review in Step 2
- **Step 6 conditional** - only if user requested prompt review in Step 2

## Extension Support

Custom configurations via EXTEND.md. See **Step 1.1** for paths and supported options.

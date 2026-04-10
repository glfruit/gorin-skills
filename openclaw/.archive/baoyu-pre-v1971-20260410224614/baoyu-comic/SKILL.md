---
name: baoyu-comic
description: Knowledge comic creator supporting multiple art styles and tones. Creates original educational comics with detailed panel layouts and sequential image generation. Use when user asks to create "知识漫画", "教育漫画", "biography comic", "tutorial comic", or "Logicomix-style comic".
---

# Knowledge Comic Creator

Create original knowledge comics with flexible art style × tone combinations.

## Usage

```bash
/baoyu-comic posts/turing-story/source.md
/baoyu-comic article.md --art manga --tone warm
/baoyu-comic  # then paste content
```

## Options

| Option | Values |
|--------|--------|
| `--art` | ligne-claire (default), manga, realistic, ink-brush, chalk |
| `--tone` | neutral (default), warm, dramatic, romantic, energetic, vintage, action |
| `--layout` | standard (default), cinematic, dense, splash, mixed, webtoon |
| `--aspect` | 3:4 (default), 4:3, 16:9 |
| `--lang` | auto (default), zh, en, ja |
| `--storyboard-only` | Generate storyboard only |
| `--prompts-only` | Generate storyboard + prompts |
| `--images-only` | Generate from existing prompts |
| `--regenerate N` | Regenerate specific page(s) |

Details: `references/partial-workflows.md`

## Art Styles & Tones

5 art styles × 7 tones. See `references/art-styles/` and `references/tones/` for details.

| Art Style | ✓✓ Best Tones |
|-----------|-------------|
| ligne-claire | neutral, warm |
| manga | neutral, romantic, energetic, action |
| realistic | neutral, warm, dramatic, vintage |
| ink-brush | neutral, dramatic, action, vintage |
| chalk | neutral, warm, energetic |

### Preset Shortcuts

| Preset | Equivalent | Special Rules |
|--------|-----------|---------------|
| `--style ohmsha` | manga + neutral | Visual metaphors, NO talking heads |
| `--style wuxia` | ink-brush + action | Qi effects, combat visuals |
| `--style shoujo` | manga + romantic | Decorative elements, eye details |

Auto selection: `references/auto-selection.md`

## Script

`scripts/merge-to-pdf.ts` — Merge comic pages into PDF.

## File Structure

Output: `comic/{topic-slug}/` — slug from 2-4 words kebab-case.

Files: `source-*`, `analysis.md`, `storyboard.md`, `characters/`, `prompts/`, `*.png`, `{slug}.pdf`

## Language

Detection: `--lang` > EXTEND.md > conversation language > source language. Use user's language for all interactions.

## Workflow

```
Comic Progress:
- [ ] Step 1: Setup & Analyze (EXTEND.md ⛔ BLOCKING)
- [ ] Step 2: Confirmation - Style & options ⚠️ REQUIRED
- [ ] Step 3: Generate storyboard + characters
- [ ] Step 4: Review outline (conditional)
- [ ] Step 5: Generate prompts
- [ ] Step 6: Review prompts (conditional)
- [ ] Step 7: Generate images ⚠️ CHARACTER REF REQUIRED
  - [ ] 7.1 Generate character sheet FIRST → characters/characters.png
  - [ ] 7.2 Generate pages WITH --ref characters/characters.png
- [ ] Step 8: Merge to PDF
- [ ] Step 9: Completion report
```

### Key Steps

**Step 1.1**: Load EXTEND.md preferences. If not found, complete first-time setup BEFORE other steps. See `references/config/first-time-setup.md`.

**Step 2**: Confirm style, focus, audience, review preferences.

**Step 3**: Generate storyboard + characters. Templates: `references/storyboard-template.md`, `references/character-template.md`.

**Step 7 ⚠️ CRITICAL**:
1. Generate character sheet FIRST → `characters/characters.png`
2. Compress character sheet (pngquant/optipng)
3. Generate EVERY page with `--ref characters/characters.png`

详见 `references/workflow.md`（完整步骤、备份规则、命令示例）

## EXTEND.md

| Path | Location |
|------|----------|
| `.openclaw/skills-config/baoyu/baoyu-comic/EXTEND.md` | Project |
| `$HOME/.openclaw/skills-config/baoyu/baoyu-comic/EXTEND.md` | User home |

Supports: Watermark | Preferred art/tone/layout | Character presets | Language. Schema: `references/config/preferences-schema.md`

## Page Modification

**Edit**: Update prompt FIRST → `--regenerate N` → PDF
**Add**: Create prompt → Generate with ref → Renumber → Update storyboard → PDF
**Delete**: Remove files → Renumber → Update storyboard → PDF

## References

| File | Content |
|------|---------|
| `references/workflow.md` | Full workflow with commands |
| `references/auto-selection.md` | Content signal analysis |
| `references/partial-workflows.md` | Partial workflow options |
| `references/analysis-framework.md` | Content analysis |
| `references/character-template.md` | Character definition format |
| `references/storyboard-template.md` | Storyboard structure |
| `references/ohmsha-guide.md` | Ohmsha manga specifics |
| `references/art-styles/` | Art style definitions |
| `references/tones/` | Tone definitions |
| `references/presets/` | Preset special rules |
| `references/layouts/` | Layout definitions |
| `references/config/` | Preferences schema, setup, watermark |

## Notes

- Auto-retry once on failure | Stylized alternatives for sensitive figures
- **Step 2 confirmation required** | Steps 4/6 conditional
- **Step 7.1 character sheet MUST be generated before pages**
- **Step 7.2 EVERY page MUST reference characters via --ref**

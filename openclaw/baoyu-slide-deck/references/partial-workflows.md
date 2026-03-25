# Partial Workflows Reference

## Overview

| Option | Workflow |
|--------|----------|
| `--outline-only` | Steps 1-3 only (stop after outline) |
| `--prompts-only` | Steps 1-5 (generate prompts, skip images) |
| `--images-only` | Skip to Step 7 (requires existing prompts/) |
| `--regenerate N` | Regenerate specific slide(s) only |

## Using `--prompts-only`

Generate outline and prompts without images:

```bash
/baoyu-slide-deck content.md --prompts-only
```

Output: `outline.md` + `prompts/*.md` ready for review/editing.

## Using `--images-only`

Generate images from existing prompts (starts at Step 7):

```bash
/baoyu-slide-deck slide-deck/topic-slug/ --images-only
```

Prerequisites:
- `prompts/` directory with slide prompt files
- `outline.md` with style information

## Using `--regenerate`

Regenerate specific slides:

```bash
# Single slide
/baoyu-slide-deck slide-deck/topic-slug/ --regenerate 3

# Multiple slides
/baoyu-slide-deck slide-deck/topic-slug/ --regenerate 2,5,8
```

Flow:
1. Read existing prompts for specified slides
2. Regenerate images only for those slides
3. Regenerate PPTX/PDF

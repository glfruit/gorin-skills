# Review Workflow Reference

Detailed formats for Step 4 (Review Outline) and Step 6 (Review Prompts).

## Step 4: Review Outline

**Skip this step** if user selected "No, skip outline review" in Step 2.

**Language**: Use user's input language or saved language preference.

**Display**:
- Total slides: N
- Style: [preset name or "custom: texture+mood+typography+density"]
- Slide-by-slide summary table:

```
| # | Title | Type | Layout |
|---|-------|------|--------|
| 1 | [title] | Cover | title-hero |
| 2 | [title] | Content | [layout] |
| 3 | [title] | Content | [layout] |
| ... | ... | ... | ... |
```

**Use AskUserQuestion**:
```
header: "Confirm"
question: "Ready to generate prompts?"
options:
  - label: "Yes, proceed (Recommended)"
    description: "Generate image prompts"
  - label: "Edit outline first"
    description: "I'll modify outline.md before continuing"
  - label: "Regenerate outline"
    description: "Create new outline with different approach"
```

**After response**:
1. If "Edit outline first" → Inform user to edit `outline.md`, ask again when ready
2. If "Regenerate outline" → Back to Step 3
3. If "Yes, proceed" → Continue to Step 5

## Step 6: Review Prompts

**Skip this step** if user selected "No, skip prompt review" in Step 2.

**Language**: Use user's input language or saved language preference.

**Display**:
- Total prompts: N
- Style: [preset name or custom dimensions]
- Prompt list:

```
| # | Filename | Slide Title |
|---|----------|-------------|
| 1 | 01-slide-cover.md | [title] |
| 2 | 02-slide-xxx.md | [title] |
| ... | ... | ... |
```

- Path to prompts directory: `prompts/`

**Use AskUserQuestion**:
```
header: "Confirm"
question: "Ready to generate slide images?"
options:
  - label: "Yes, proceed (Recommended)"
    description: "Generate all slide images"
  - label: "Edit prompts first"
    description: "I'll modify prompts before continuing"
  - label: "Regenerate prompts"
    description: "Create new prompts with different approach"
```

**After response**:
1. If "Edit prompts first" → Inform user to edit prompts, ask again when ready
2. If "Regenerate prompts" → Back to Step 5
3. If "Yes, proceed" → Continue to Step 7

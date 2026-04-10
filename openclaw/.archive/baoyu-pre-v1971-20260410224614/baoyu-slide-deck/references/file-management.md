# File Management Reference

## Output Directory Structure

```
slide-deck/{topic-slug}/
├── source-{slug}.{ext}
├── outline.md
├── prompts/
│   └── 01-slide-cover.md, 02-slide-{slug}.md, ...
├── 01-slide-cover.png, 02-slide-{slug}.png, ...
├── {topic-slug}.pptx
└── {topic-slug}.pdf
```

## Slug Generation

**Format**: Extract topic (2-4 words, kebab-case).

Example: "Introduction to Machine Learning" → `intro-machine-learning`

## Conflict Handling

When existing content is detected (Step 1.3), use AskUserQuestion:

```
header: "Existing"
question: "Existing content found. How to proceed?"
options:
  - label: "Regenerate outline"
    description: "Keep images, regenerate outline only"
  - label: "Regenerate images"
    description: "Keep outline, regenerate images only"
  - label: "Backup and regenerate"
    description: "Backup to {slug}-backup-{timestamp}, then regenerate all"
  - label: "Exit"
    description: "Cancel, keep existing content unchanged"
```

## Backup Rules

| Scenario | Backup Action |
|----------|--------------|
| Source file exists | Rename to `source-backup-YYYYMMDD-HHMMSS.md` |
| Prompt file exists | Rename to `prompts/NN-slide-{slug}-backup-YYYYMMDD-HHMMSS.md` |
| Image file exists | Rename to `NN-slide-{slug}-backup-YYYYMMDD-HHMMSS.png` |
| Full regeneration | Backup directory to `{slug}-backup-{timestamp}` |

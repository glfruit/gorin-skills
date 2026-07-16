# Implementation Notes

## Directory Structure

```
visual-knowledge-explainer/
├── SKILL.md
├── references/
├── templates/
├── scripts/
└── research/
```

## File Responsibilities

### `SKILL.md`
- User-facing trigger guidance
- When to use / when not to use
- Quick start
- Core workflow

### `references/`
- `aesthetic-rules.md`: theme guidelines
- `rendering-strategy.md`: template selection logic
- `page-patterns.md`: template patterns
- `mermaid-guidelines.md`: Mermaid constraints
- `anti-slop-rules.md`: quality rules
- `output-conventions.md`: naming and delivery conventions
- `eval-prompts.md`: real eval prompts
- `templates-readme.md`: template inventory

### `templates/`
- Reusable HTML structures
- Inline CSS, portable output

### `scripts/`
- `main.ts`: entrypoint
- `detect-content-type.ts`: content-type detection
- `select-template.ts`: template selection
- `render-html.ts`: HTML generation
- `generate-screenshot.ts`: optional screenshot generation
- `maybe-open.sh`: optional local browser open

## Design Notes

- `SKILL.md` stays concise; implementation detail belongs here.
- Screenshot generation is optional enhancement, not required for HTML success.
- Theme switching must affect real CSS output, not just metadata.
- Integrated workflows should pass an explicit output directory when they care about artifact location.

## Future Work

- stronger structured extraction for workflow/comparison content
- more stable screenshot fallback chain
- more teaching-specific page variants

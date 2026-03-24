# Parameter Design

Only add parameters when they reduce repetition or make acceptance/testing easier.

## Useful parameter patterns

### `--quick`
Use when the skill has an interactive or multi-step flow and power users may want defaults.

Do not let `--quick` bypass:
- destructive-operation confirmations
- required auth checks
- user-facing completion rules

### `--dry-run`
Use when the skill changes files, sends data, or triggers side effects.

### `--only <phase>`
Use when the workflow has cleanly separable phases, for example:
- `--only research`
- `--only validate`
- `--only package`

### `--regenerate <target>`
Use when one expensive sub-artifact may need selective reruns.

## argument-hint

If the skill benefits from parameters, expose them in frontmatter:

```yaml
argument-hint: [subject] [--quick] [--dry-run] [--only phase]
```

## Rule of thumb

Add parameters only if they make the workflow more reusable, testable, or recoverable.
If the parameter exists only because the workflow is unclear, fix the workflow instead.

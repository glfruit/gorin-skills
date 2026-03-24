# Readiness Gates

`enhanced-skill-creator` must distinguish between a well-designed skill and a proven, integrated skill. Use these gates when creating or reviewing any skill.

## Levels

### 1. `scaffold`

Use when the skill has:
- a coherent `SKILL.md`,
- sane structure,
- references/assets/scripts layout,
- but no proven runnable happy path.

Allowed claims:
- "scaffold"
- "draft"
- "partial"
- "planning-ready"

Forbidden claims:
- "ready to use"
- "production-ready"
- "fully integrated"

Typical evidence:
- `SKILL.md`
- template files
- script stubs
- references

### 2. `mvp`

Use when the skill has:
- one real happy path that runs end-to-end,
- one primary entrypoint that works,
- no critical TODO in the executed path,
- at least one real output artifact.

Allowed claims:
- "mvp"
- "minimally usable"
- "happy path verified"

Required evidence:
- command used
- concrete input
- concrete output path
- success criteria

### 3. `production-ready`

Use when the skill has:
- stable happy path,
- documented failure boundaries,
- doc/implementation consistency,
- at least one regression check,
- clear output contract.

Required evidence:
- happy-path run
- failure-mode run or explicit fallback proof
- acceptance contract
- validator output

### 4. `integrated`

Use when the skill has:
- all `production-ready` evidence,
- at least one upstream caller or workflow integration,
- at least one real integrated run,
- output locations confirmed in the real consumer flow.

Required evidence:
- upstream integration point
- integrated invocation command or workflow trigger
- resulting artifact path
- any integration-specific bug fixes already folded back

## Blocking Rules

Do not label a skill `mvp` or above if any of these are true:
- primary entrypoint contains `TODO` or equivalent placeholder logic
- executed path throws `not implemented`
- documentation says "ready" but no real output artifact exists
- output directory behavior has not been tested
- required dependency is assumed but never checked

Do not label a skill `production-ready` or `integrated` if:
- screenshots/downloads/uploads are still stubbed but advertised as working
- only unit-like validation exists and no real invocation has been run
- the skill has never been called from the workflow it is meant to serve

## Minimum Acceptance Contract

For output-generating or integration-heavy skills, record:
- primary entrypoint
- supported input shapes
- expected outputs
- output directory rules
- success criteria
- fallback behavior
- known non-goals

This can live in `references/`, `assets/`, or a review report. It does not need to be long, but it must exist.

## Example: `visual-knowledge-explainer`

What went wrong initially:
- structure and templates looked mature,
- `main.ts` was still a stub,
- screenshot path was still placeholder,
- docs implied direct usability,
- integration bug only appeared after being called from the book-reading workflow.

Correct labeling at that point:
- `scaffold`, not `production-ready`

Correct labeling after fixes:
- `mvp`, then `integrated` once called successfully from the reading workflow.

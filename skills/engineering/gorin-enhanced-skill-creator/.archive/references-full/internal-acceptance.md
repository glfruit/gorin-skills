# Internal Acceptance

`enhanced-skill-creator` must treat internal acceptance as a mandatory gate, not a nice-to-have.

## User-facing rule

Only report a skill as **created/completed** when internal readiness has reached `integrated`.

These are internal-only states:
- `scaffold`
- `mvp`
- `production-ready`
- `integrated`

User-facing completion is allowed **only** at `integrated`.
If integrated proof is missing, report `failed` or `blocked` instead of pretending completion.

## Internal acceptance result types

### `passed`
Use when:
- one real happy path was executed,
- expected artifacts or side effects exist,
- success criteria were actually observed.

### `failed`
Use when:
- the path ran but broke,
- output was wrong,
- artifacts were missing,
- acceptance criteria were not met.

### `blocked`
Use when:
- external auth is missing,
- required tools are unavailable,
- upstream system access is unavailable,
- the path cannot be executed without outside help.

## Minimum acceptance record

Every skill should define one concrete happy-path case and record:
- skill name
- timestamp
- concrete input
- invocation method or command
- expected artifacts
- actual artifacts
- result: `passed` / `failed` / `blocked`
- blocker or failure notes
- integration point checked or not checked

## Minimum acceptance policy

A new skill is not deliverable just because:
- `SKILL.md` exists,
- the structure looks good,
- validators pass,
- examples look convincing.

A new skill becomes user-deliverable only when:
1. quick validate passes
2. strict validate passes
3. one internal acceptance run passes
4. one integration path is proven

## Report wording

### Allowed
- "Internal acceptance passed; integration path proven; skill creation complete."
- "Internal acceptance failed; skill not complete yet."
- "Internal acceptance blocked by external dependency; skill not complete yet."

### Forbidden
- "The skill is complete" when only scaffold/mvp/production-ready is reached.
- "The skill is basically done" without a passing internal acceptance record.
- handing a scaffold to the user as if it were a finished skill.

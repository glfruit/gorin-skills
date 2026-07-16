---
name: gorin-code-review
description: Review concrete git changes, staged changes, untracked additions, pull-request ranges, or branch diffs for correctness, security, reliability, and removal risks. Use when the user asks for a code review before merge or wants findings on an existing diff. Do not use for implementation, free-form architecture advice, lint-only checks, or non-git documents.
license: MIT
user-invocable: true
---

# Code Review

Review evidence in a git diff and return severity-ranked findings. The review is read-only until the user explicitly authorizes fixes.

## Workflow

### 1. Establish the review set

Run:

```bash
git status -sb
git ls-files --others --exclude-standard
git diff --stat
git diff
git diff --cached
```

If the user names a range, use `git diff <base>...<head>` instead. Include untracked files in scope as full-file additions. If no reviewable change exists, ask for a range or branch; completion means every reviewed path and the chosen diff source are stated.

For a diff larger than 500 lines or spanning unrelated concerns, group it by behavior/module and review one group at a time. State any group not covered.

### 2. Read enough surrounding code

Use the repository's code graph when available; otherwise use `rg` to find callers, contracts, tests, migrations, and ownership rules affected by changed lines. Review the diff rather than re-reviewing unchanged files. Completion means every potential finding has been checked against its relevant contract or caller.

### 3. Apply all four lenses

- Read `references/security-checklist.md` for trust boundaries, data integrity, concurrency, and supply-chain changes.
- Read `references/code-quality-checklist.md` for error, performance, async, and boundary behavior.
- Read `references/solid-checklist.md` only when the diff changes module responsibilities or interfaces.
- Read `references/removal-plan.md` only when deletion or deprecation is relevant.

A finding is valid only when it identifies changed behavior, file and line, impact, and an actionable correction. Do not report preferences as defects. Completion means every changed behavior has been considered under correctness, security/reliability, and regression risk.

### 4. Rank findings

| Severity | Meaning | Merge guidance |
| --- | --- | --- |
| P0 | Exploitable vulnerability, data loss, or systemic correctness failure | Block |
| P1 | Likely production bug, broken authorization/invariant, or major regression | Block until fixed |
| P2 | Real maintainability or edge-case risk with bounded impact | Fix or track |
| P3 | Low-risk improvement | Optional |

Severity follows impact and likelihood, not code style.

### 5. Report

Lead with findings in P0→P3 order. Each finding must use `path:line`, explain the failure scenario, and give the smallest credible correction. Then state:

- reviewed scope and diff source;
- tests or checks actually run;
- areas not verified and residual risks;
- overall result: `APPROVE`, `REQUEST_CHANGES`, or `COMMENT`.

If no findings exist, say so explicitly and name what was checked. Never invent a finding to fill a severity section.

### 6. Stop at the confirmation gate

Summarize finding counts and ask whether to fix all, only blocking findings, selected findings, or none. The review is complete when the report is actionable and no source file has been modified.

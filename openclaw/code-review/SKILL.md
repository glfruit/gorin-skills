---
name: code-review
description: "Structured code review of git changes with senior engineer rigor. Checks SOLID violations, security risks, race conditions, error handling, performance, boundary bugs, and removal candidates. Outputs severity-classified findings (P0–P3) with actionable fixes. Don't use it for general coding tasks, non-git file editing, or writing new code from scratch."
trigger-guide: |
  典型触发短语:
    - "帮我 review 一下这次改动"
    - "看下这个 PR 有没有问题"
    - "审查一下当前 diff"
    - "合并前帮我做个代码审查"
  适用场景:
    - 用户要审查 git 变更、PR、分支差异或当前工作区改动时使用。
    - 适合在提交、合并、发布前做结构化风险检查，并输出按严重级别分类的问题。
  不适用场景:
    - 写新功能、普通调试、非 git 上下文的文档审阅不该用这个 skill。
triggers: ["review my code", "review this PR", "code review", "review changes", "review the diff", "check my code", "审查代码", "代码审查", "review current changes", "pre-merge review"]
user-invocable: true
agent-usable: true
---

# Code Review

Structured review of git changes through a senior engineer lens. Detects SOLID violations, security risks, race conditions, performance regressions, and boundary bugs. Outputs severity-classified findings with actionable fixes. Review-first by default — no changes until you confirm.

## When to Use

- Before merging a PR or pushing to main
- After completing a feature branch and wanting a second pair of eyes
- When reviewing someone else's changes in a local checkout
- When you suspect a diff introduced security or correctness issues
- When cleaning up before a release and want to catch removal candidates

## When NOT to Use

- General coding help or writing new code from scratch — just ask the agent directly
- Reviewing non-git files or arbitrary documents — this skill requires git context
- Quick syntax or linting checks — use your linter/formatter instead
- Architecture design discussions without concrete code changes — use a planning skill

## Design Pattern

This skill follows the **Reviewer** pattern: checklist-driven analysis with severity classification.

- Review checklists live in `references/` and are loaded on demand at each workflow step
- Severity scheme: P0 (Critical) → P3 (Low) with merge-blocking guidance
- Output: structured findings report with inline file:line references
- Confirmation gate: no fixes applied until user explicitly opts in

## Core Workflow

### 1) Preflight — Scope the Changes

Run these commands to understand what you're reviewing:

```bash
git status -sb
git ls-files --others --exclude-standard
git diff --stat
git diff
```

If the user specified a commit range or branch comparison, use that instead:
```bash
git diff <base>...<head> --stat
git diff <base>...<head>
```

Treat untracked files returned by `git ls-files --others --exclude-standard` as full-file additions when they fall inside the requested review scope.

Use `rg` or `grep` to find related modules, usages, and contracts when context is needed.

**Decision table for diff source:**

| Situation | What to review | Command |
|-----------|---------------|---------|
| Unstaged changes exist | Unstaged diff | `git diff` |
| Only staged changes | Staged diff | `git diff --cached` |
| Untracked files exist | Review as new-file additions | `git ls-files --others --exclude-standard` + full file read |
| User specifies commit range | Range diff | `git diff <base>...<head>` |
| User specifies branch | Branch diff | `git diff main...<branch>` |
| No changes at all | Ask user | Inform and ask for commit range or branch |
| Not a git repo | Stop | Inform user this skill requires a git repository |

**Large diff (>500 lines):** Summarize by file first (`git diff --stat`), then review in batches grouped by module/feature area. Don't try to review everything in one pass.

**Mixed concerns:** Group findings by logical feature, not file order.

### 2) SOLID + Architecture Smells

Load `references/solid-checklist.md` and check each item against the diff.

Focus areas:
- **SRP**: Modules with unrelated responsibilities mixed together
- **OCP**: Behavior added by editing core logic instead of extension points
- **LSP**: Subclasses that break parent expectations or require type checks
- **ISP**: Wide interfaces with unused methods
- **DIP**: Business logic coupled to infrastructure implementations

When proposing a refactor, explain *why* it improves cohesion/coupling. If the refactor is non-trivial, propose an incremental plan rather than a rewrite.

### 3) Removal Candidates

Load `references/removal-plan.md` for the template.

Identify code that is unused, redundant, or feature-flagged off. Distinguish:
- **Safe delete now**: no references, no consumers, tests pass without it
- **Defer with plan**: has consumers that need migration, or needs stakeholder sign-off

### 4) Security + Reliability Scan

Load `references/security-checklist.md` and check each category.

Priority targets: auth boundaries, data writes, network calls, user input handling, crypto usage, concurrent access patterns.

Call out both **exploitability** and **impact** for each finding.

### 5) Code Quality Scan

Load `references/code-quality-checklist.md` and check each category.

Priority targets: error handling gaps, N+1 queries, unbounded memory, null/undefined handling, off-by-one errors, async error propagation.

Flag issues that may cause silent failures or production incidents.

### 6) Output — Structured Review Report

```markdown
## Code Review Summary

**Files reviewed**: X files, Y lines changed
**Overall assessment**: [APPROVE / REQUEST_CHANGES / COMMENT]

---

### P0 — Critical
(none or list)

### P1 — High
1. **[file:line]** Brief title
   - Description of issue
   - Suggested fix

### P2 — Medium
(continue numbering)

### P3 — Low
...

---

### Removal/Iteration Plan
(if applicable)

### Additional Suggestions
(optional, not blocking)
```

For file-specific inline comments, use:
```
::code-comment{file="path/to/file.ts" line="42" severity="P1"}
Description and suggested fix.
::
```

**Clean review:** If no issues found, explicitly state what was checked and any areas not covered (e.g., "Did not verify database migrations"). Note residual risks.

### 7) Next Steps — Confirmation Gate

⚠️ REQUIRED: Do NOT implement any changes until user explicitly confirms.

```markdown
---
## Next Steps

Found X issues (P0: _, P1: _, P2: _, P3: _).

**How would you like to proceed?**
1. **Fix all** — implement all suggested fixes
2. **Fix P0/P1 only** — address critical and high priority
3. **Fix specific items** — tell me which issues to fix
4. **No changes** — review complete, no implementation needed
```

## Quick Reference

| Severity | Name | Action | Blocks merge? |
|----------|------|--------|---------------|
| P0 | Critical | Security vuln, data loss, correctness bug | Yes |
| P1 | High | Logic error, major SOLID violation, perf regression | Should fix first |
| P2 | Medium | Code smell, maintainability, minor SOLID violation | Fix or create follow-up |
| P3 | Low | Style, naming, minor suggestion | Optional |

| Review phase | Reference file | Focus |
|-------------|---------------|-------|
| SOLID | `references/solid-checklist.md` | Architecture smells, coupling |
| Removal | `references/removal-plan.md` | Dead code, feature flags |
| Security | `references/security-checklist.md` | Injection, auth, race conditions |
| Quality | `references/code-quality-checklist.md` | Errors, perf, boundaries |
| Coding Guidelines | `~/.openclaw/shared/coding-guidelines.md` | Anti-Pattern: 假设隐藏、过度复杂、非手术刀改动、弱目标、命令式指令、概念错误、附和倾向、跳过人类审查 |

## Common Mistakes

| Mistake | Why It Fails | Better Approach |
|---------|-------------|-----------------|
| Reviewing without reading surrounding code | Misses context, false positives | Use `rg` to find callers and contracts before flagging |
| Flagging style issues as P1 | Noise drowns real issues | Reserve P1+ for correctness, security, logic errors |
| Proposing large rewrites in review | Unrealistic, blocks merge | Propose incremental plan with concrete first step |
| Implementing fixes without asking | User may disagree with approach | Always present findings first, wait for confirmation |
| Reviewing entire file instead of diff | Wastes time, scope creep | Focus on changed lines and their immediate context |

## Error Handling

### Not a Git Repository
Inform the user: "This directory is not a git repository. Code review requires git context to identify changes. Please run from a git repo or specify files to review manually."

### No Changes Detected
Ask the user what they want reviewed: staged changes (`git diff --cached`), a specific commit range, or a branch comparison. Don't silently do nothing.

### Git Command Failure
If `git diff` or `git status` fails (permissions, corrupt repo, etc.), report the error and suggest the user check their git state. Don't guess.

### Ambiguous Scope
If the diff touches 20+ files across unrelated modules, ask the user if they want a full review or want to focus on specific areas. Don't silently skip files.

### Partial Review
If you couldn't cover all phases (e.g., skipped security due to context limits), explicitly state what was and wasn't reviewed. Never claim a complete review when it wasn't.

## Gotchas

- `git diff` shows unstaged changes only. If user staged everything, you'll see an empty diff and think there's nothing to review. Always check `git diff --cached` as fallback.
- Large diffs (>500 lines) will degrade review quality if processed in one shot. Split by module and review in batches.
- Race condition bugs are the most commonly missed category. Always ask: "What happens if two requests hit this code simultaneously?"
- Don't confuse "code I don't like" with "code that's wrong." P2/P3 findings should be clearly labeled as suggestions, not blockers.
- When reviewing TypeScript/JavaScript, check for unhandled promise rejections — they're silent in many runtimes and cause production incidents.
- Removal candidates need evidence (grep for references). Don't flag code as "unused" based on the diff alone — it may be called from outside the changed files.
- The confirmation gate (Step 7) is not optional. Skipping it and implementing fixes directly is the #1 user complaint with review skills.
- If the repo has a `.github/CODEOWNERS` or review checklist, mention it — the user may have team-specific review requirements you should incorporate.

## Internal Acceptance

- **Happy-path input**: In a real git repository with local changes, invoke the skill on `review current changes` or `review this diff`.
- **Invocation method**: direct skill invocation in a git repo, or an upstream caller that routes a review request into this skill.
- **Expected artifacts**:
  - a structured review summary in chat or markdown,
  - severity-classified findings (P0-P3),
  - clear statement of reviewed scope,
  - explicit next-step confirmation gate.
- **Success criteria**:
  - the skill correctly identifies the diff source,
  - reviews changed code rather than free-associating,
  - uses severity consistently,
  - does not implement fixes before confirmation,
  - produces a review that a human can act on.
- **Fallback / blocker behavior**:
  - if not in a git repo, report blocked and ask for repo/commit range;
  - if no diff exists, report blocked and ask what should be reviewed;
  - if scope is too broad, narrow or batch it before claiming completion.
- **Integration point**: user asks for code review in a git repo, or an upstream engineering workflow routes a pre-merge review to this skill.

## Delivery Contract

- Internal readiness may move through `scaffold`, `mvp`, `production-ready`, and `integrated`.
- These are internal states only.
- Do **not** report this skill as created/completed to the user unless its internal readiness has reached **`integrated`**.
- If internal acceptance or real git-review integration proof is missing, report `failed` or `blocked` instead of claiming completion.

## Resources

| File | Purpose |
|------|---------|
| `references/solid-checklist.md` | SOLID smell prompts, code smell table, refactor heuristics |
| `references/security-checklist.md` | Input safety, auth, JWT, secrets, CORS, runtime risks, race conditions, data integrity |
| `references/code-quality-checklist.md` | Error handling, performance/caching, boundary conditions |
| `references/removal-plan.md` | Template for deletion candidates and deferred removal plans |

---
name: harness-audit
description: >
  Reviewer-type skill for auditing OpenClaw agent harness configuration health.
  Scans SOUL.md, AGENTS.md, SKILL.md, and cron jobs across all agent workspaces
  for bloat, stale references, rule duplication, and hard-coded payloads.
  Outputs severity-classified findings (P0–P3) with trend tracking across audits.
  Use when user says "audit harness", "检查配置健康", "harness review",
  "配置审计", or when a periodic cron triggers monthly review.
  Do NOT use for code review (use code-review skill), host security (use healthcheck),
  or single-file editing.
---

# Harness Audit

Periodic health audit of OpenClaw agent harness configurations. Detects bloat,
stale references, rule duplication, and configuration drift across all workspaces,
skills, and cron jobs. Outputs structured, severity-classified reports.

## Design Pattern

**Reviewer pattern**: checklist-driven analysis with severity classification.

- Audit checklists live in `references/` (separated by dimension)
- Severity: P0 (必改) → P1 (建议) → P2 (可选) → P3 (信息)
- Read-only by default — no config changes without user confirmation
- Trend tracking across monthly runs

## When to Use

- User requests harness/config health check
- Monthly periodic audit via cron
- After major model changes (rules written for old models may be stale)
- After adding/removing agent workspaces

## When NOT to Use

- Code review of git diffs → use `code-review` skill
- Host security hardening → use `healthcheck` skill
- Single file editing → edit directly
- Skill creation/improvement → use `enhanced-skill-creator`

## Core Workflow

### 1) Scope — Gather Configuration Inventory

Run the audit script to collect baseline metrics:

```bash
python3 scripts/harness_audit.py --all --json
```

This returns structured findings. For human-readable output:

```bash
python3 scripts/harness_audit.py --all --report
```

The script scans:
- All `~/.openclaw/workspace-*/SOUL.md` and `AGENTS.md`
- All `~/.openclaw/skills/*/SKILL.md`
- Cron job inventory (if available)

### 2) Enrich — Contextual Analysis

Review the JSON output and apply context the script cannot detect:

**Rule effectiveness**: For agents with >10 hard-coded rules, check whether the rules
are actually referenced in recent session transcripts. Rules that are never triggered
are candidates for removal (inspired by Anthropic's "non-load-bearing" principle:
*if removing a rule causes no behavioral change, it's overhead*).

**Model-fit check**: Rules written as workarounds for old model limitations may be
obsolete after model upgrades. Check rule descriptions for model-specific language
(e.g., "because gpt-4 can't...", "workaround for kimi timeout...").

**Cross-agent duplication**: If 3+ agents have identical rule text, consider promoting
it to the global `~/.openclaw/SOUL.md` or a shared references file.

### 3) Report — Structured Findings

Generate the audit report:

```bash
python3 scripts/harness_audit.py --all --report ~/.openclaw/audits
```

Report structure:

```markdown
# Harness 审计报告 — YYYY-MM

## 摘要
- Agent/Skill/Cron counts
- P0/P1/P2/P3 breakdown
- Comparison with previous audit (trend)

## 概况
- SOUL.md line count ranking (Top 5, flag >150)
- SKILL.md line count ranking (Top 5, flag >300)

## 发现
### P0 必改
### P1 建议
### P2 可选
### P3 信息

## 趋势
- Line count changes since last audit
- New/removed workspaces
- Recurring issues
```

### 4) Gate — Confirmation Required

⚠️ Do NOT implement any changes based on the audit report.

Present findings to the user with priority-sorted action items. Wait for explicit
confirmation before modifying any configuration files.

```
Found X issues (P0: _, P1: _, P2: _, P3: _).
How to proceed?
1. Fix P0 only
2. Fix P0+P1
3. Discuss specific items
4. Archive report, no changes
```

## Audit Dimensions

See `references/thresholds.md` for full checklist per dimension:

| Dimension | Checks | Thresholds |
|-----------|--------|------------|
| SOUL.md | Line count, rule count, broken refs, overlap with AGENTS.md | >150 warn, >200 critical |
| AGENTS.md | Line count, broken refs, stale processes | >150 warn |
| Skills | SKILL.md line count, broken refs | >300 warn |
| Cron | Payload length, hardcoded paths, failure rate, orphaned tasks | >500 chars warn |

## Severity Definitions

| Level | Name | Action | Example |
|-------|------|--------|---------|
| P0 | 必改 | Fix immediately | Broken path reference causing agent errors |
| P1 | 建议 | Fix soon | SOUL.md >200 lines, rule duplication |
| P2 | 可选 | Fix when convenient | Line count approaching threshold |
| P3 | 信息 | Awareness only | New workspace added, skill count changed |

## Gotchas

- The script detects *literal* path references but cannot detect *implied* paths
  (e.g., "use the sync script" without naming it). Manual review needed for these.
- SOUL.md rule count is based on `**bold**` pattern — if rules use different formatting,
  the count may undercount. Spot-check heavy agents manually.
- Jaccard similarity between SOUL.md and AGENTS.md is line-level, not semantic.
  Two files may score low overlap but express the same rule differently.
- Cron audit requires `openclaw cron list` output. If the command is unavailable or
  returns an error, cron dimension is silently skipped.
- Historical trend comparison only works if previous reports exist in
  `~/.openclaw/audits/`. First run has no baseline.
- The "non-load-bearing" check (Step 2 rule effectiveness) requires session transcript
  access and cannot be automated by the script alone. This is the highest-value
  but most labor-intensive check.

## Trend Tracking

Reports are saved as `~/.openclaw/audits/harness-YYYY-MM.md`. On subsequent runs,
the script compares against the previous month's report and includes:

- Line count deltas per agent
- New/removed workspaces and skills
- Issues that appeared in previous report but are now resolved (credit)
- Issues that persist across 2+ consecutive audits (escalation candidate)

## Internal Acceptance

- **Happy-path**: Run `python3 scripts/harness_audit.py --all --report` on a system
  with 30+ agent workspaces and 40+ skills.
- **Expected artifacts**: Markdown report in `~/.openclaw/audits/` with correct counts,
  severity-classified findings, and top-5 rankings.
- **Success criteria**: Report is accurate (verified by spot-checking 3 random findings),
  script completes in <10 seconds, no false P0s.
- **Readiness**: `mvp` (script works, manual enrichment step needs real session
  transcript access for full validation).

## Resources

| File | Purpose |
|------|---------|
| `references/thresholds.md` | Checklist per dimension with specific thresholds |
| `scripts/harness_audit.py` | Core audit script (Python) |

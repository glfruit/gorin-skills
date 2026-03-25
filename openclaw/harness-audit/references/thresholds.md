# Audit Checklists & Thresholds

## SOUL.md Checklist

| # | Check | Method | Threshold | Severity |
|---|-------|--------|-----------|----------|
| 1 | Total line count | `wc -l` | >150 P2, >200 P1 | 膨胀 |
| 2 | Hard-coded rule count | Match `**bold**: ` pattern | >10 P1 | 过度约束 |
| 3 | Broken path references | Expand `~/` and check `os.path.exists` | Any = P0 | 运行时错误 |
| 4 | Overlap with AGENTS.md | Line-level Jaccard similarity | >30% = P1 | 重复维护 |
| 5 | Model-specific language | Grep for model names in rule context | Flag for review = P3 | 可能过时 |
| 6 | Empty/placeholder sections | Grep for TODO, FIXME, placeholder | Any = P2 | 未完成 |

## AGENTS.md Checklist

| # | Check | Method | Threshold | Severity |
|---|-------|--------|-----------|----------|
| 1 | Total line count | `wc -l` | >150 P2 | 膨胀 |
| 2 | Broken path references | Expand and check | Any = P0 | 运行时错误 |
| 3 | Stale process references | Check referenced scripts/commands exist | Any = P1 | 流程断裂 |
| 4 | Duplicate rules with SOUL.md | Same as SOUL.md #4 | >30% = P1 | 重复维护 |

## Skills Checklist

| # | Check | Method | Threshold | Severity |
|---|-------|--------|-----------|----------|
| 1 | SKILL.md line count | `wc -l` | >300 P1 | 应拆分到 references/ |
| 2 | Broken path references | Expand and check | Any = P1 | 文档错误 |
| 3 | Missing SKILL.md | Directory exists but no SKILL.md | Flag = P3 | 不完整 |

## Cron Checklist

| # | Check | Method | Threshold | Severity |
|---|-------|--------|-----------|----------|
| 1 | Payload length | `len(payload.message)` | >500 chars = P1 | 应提取为脚本 |
| 2 | Hardcoded paths in payload | Grep `~/` or `/Users/` | Any = P1 | 不够灵活 |
| 3 | Consecutive errors | `job.consecutiveErrors` | >=2 = P0, >=1 = P2 | 需要关注 |
| 4 | Orphaned workspace | Job references non-existent workspace | Any = P0 | 无用任务 |

## Manual Enrichment (Script Cannot Automate)

| # | Check | How | Value |
|---|-------|-----|-------|
| 1 | Rule effectiveness | Grep session transcripts for rule-related keywords | Remove rules that never trigger |
| 2 | Model-fit | Check if rules reference old model behavior/workarounds | Remove if model has improved |
| 3 | Cross-agent duplication | Compare rule text across 3+ agents | Promote to global SOUL.md |
| 4 | Rule quality | Read rule text for vagueness or contradiction | Rewrite for clarity |

These manual checks follow the Anthropic "non-load-bearing" principle:
if removing a rule causes no measurable behavioral change, it's overhead.

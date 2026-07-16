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

## Self-Monitoring & Auto-Promotion

Skills with `production-ready` status should **self-monitor** and auto-promote to `integrated` when conditions are met, rather than relying on manual tracking.

### When to Add Self-Monitoring

| Skill Type | Monitoring Mechanism |
|---|---|
| Monitor/Cron | Cron payload includes step N: check run history, promote if conditions met |
| Pipeline/Orchestrator | State file tracks `runs[]`, cron or heartbeat checks conditions |
| Tool Wrapper | No self-monitoring needed (promoted manually after integration test) |
| PKM Integration | No self-monitoring needed (promoted after one real zk call succeeds) |

### Implementation Pattern

**In cron payload (last step):**
```
N. 自检升级: 读取 state 文件 runs[] 数组，如果最近 {N} 次成功 run 跨越 >= {D} 个不同日期:
   - 用 edit 工具将 SKILL.md Origin Metadata 的 readiness 从 "{current}" 改为 "{target}"
   - 记录升级时间到 state 文件
```

**In SKILL.md Origin Metadata:**
```json
{
  "origin": "self",
  "readiness": "production-ready",
  "auto_promote": {
    "target": "integrated",
    "condition": "3 successful runs spanning >= 3 different dates in runs[]",
    "checked_by": "cron step N"
  }
}
```

**Promotion conditions by skill type:**

| Type | Condition | Reasoning |
|---|---|---|
| Monitor/Cron | N=3 runs, D=3 days | Proves daily stability |
| Pipeline (cron-driven) | N=3 runs, D=3 days | Same — daily execution is the proof |
| Pipeline (on-demand) | N=5 runs, no date requirement | Volume proves maturity |
| API Integration | N=10 calls, 0 errors | Error-free threshold |

**After promotion:**
- Remove `auto_promote` from Origin Metadata (mission accomplished)
- The self-monitoring step in the payload can remain (harmless no-op) or be removed for cleanliness

### State File Convention

```json
{
  "runs": [
    {"run": "R1", "ts": "2026-03-26T12:30:00+08:00", "items": 18, "status": "ok"},
    {"run": "R2", "ts": "2026-03-26T12:42:00+08:00", "items": 15, "status": "ok"},
    {"run": "R3", "ts": "2026-03-26T13:50:00+08:00", "items": 15, "status": "ok"}
  ]
}
```

Each cron run appends to `runs[]`. The self-check extracts dates from `ts`, counts unique dates among `status: "ok"` entries, and promotes when threshold is met.

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

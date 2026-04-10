---
name: enhanced-skill-creator
description: "Create high-quality skills using case-based methodology from domain masters. Research real examples, extract patterns, and generate skills with real content. Use when the user wants to create or rebuild an AgentSkill. Don't use it for simple one-off script edits, trivial aliases, or direct minor SKILL.md tweaks."
triggers: ["create skill", "build skill", "make a skill", "new skill", "design skill"]
user-invocable: true
agent-usable: true
---

# Enhanced Skill Creator

> "The hard part isn't the format — it's knowing the best way to do the thing."

## Core Principles

- **Concise is mandatory**: Every section justifies its token cost. Research (SkillReducer, arXiv:2603.29919, 55K skills) shows removing 39% body content improves quality by 2.8% — less-is-more.
- **Right degree of freedom**: High (judgment) / Medium (parameterized) / Low (encode in scripts)
- **Progressive disclosure**: SKILL.md → references/ → scripts/ → assets/. Only actionable core rules in context; examples/background on demand.
- **Start from real use cases**: Ask for concrete scenarios before designing

## 8-Step Workflow

### Step 1: Narrow the Task
Ask: Domain, Scenario, Constraints, Audience. Classify via `references/skill-taxonomy.md` (12 types). Read `references/creation-patterns/{type}.md` for patterns.

### Step 2: Find Golden Cases (CRITICAL)
Search: local skills → vault → web → GitHub.
**STOP. Must have 3+ real golden cases with verifiable sources.**
Read `.archive/references-full/golden-examples.md` for methodology.

### Step 3: Extract Patterns + Body Layering
For each case: What makes it effective? What would a novice miss? Create before/after comparisons.

**Layering pass**: Classify each planned section as:
- **Core (always loaded)**: actionable rules, decision trees, hard constraints
- **Reference (on demand)**: examples, background theory, data tables, API specs
- Core goes in SKILL.md; reference goes in `references/` or loaded via `read` tool at runtime.

### Step 4: Apply Theory (Optional)
Only add theory when it explains **why** patterns work. No generic filler.

### Step 5: Generate the Skill
1. `scripts/init-skill.sh <name> <dir>` or copy `config/skill-template.md`
2. Fill every section with **real content** — no placeholders
3. Python preferred; bash only as thin wrappers (<50L)
4. Include `## Gotchas` section
5. Assign readiness: scaffold / mvp / production-ready / integrated

### Step 6: Validate
Run these in order (all must pass):
1. `scripts/validate-skill.sh` — structural check
2. `python3 scripts/description_optimizer.py <dir>` — **description quality check (no non-routing content)**
3. `scripts/detect-overlap.sh` — trigger collision check
4. `scripts/detect-blockers.sh` — dependency check
5. `python3 scripts/context_sizer.py <dir>` — **Grade B+ required** (now includes per-invocation cost estimate)
6. `python3 scripts/trigger_eval.py <dir>` — **F1 ≥ 0.8 required**
7. `python3 scripts/governance_check.py <dir>` — **Score ≥ 70 required**
8. Golden case test — output quality matches cases?
9. Failure mode test — prevents known anti-patterns?

If validation fails → return to Step 2 or 3 (almost always insufficient research).

### Step 7: Internal Acceptance
Run one real happy-path case with concrete input. If fails: keep fixing. Record: command, input, expected/actual, result.
Update `references/creation-patterns/{type}.md` with lessons learned.

### Step 8: Prove Integration
Run through upstream caller if applicable. Fix integration bugs before labeling `integrated`.

## Internal Acceptance
- **Happy-path**: 创建一个 Type 5 (Monitor) 技能 `test-health-check`
- **Invocation**: 直接调用 Step 1-6，在 `/tmp/test-health-check/` 生成
- **Expected**: SKILL.md（frontmatter + 必填段 + 无 placeholder）、Python 脚本、.skill-meta.json
- **Success**: validate-skill.sh + context_sizer Grade B+ + trigger_eval F1 ≥ 0.8

## Delivery Contract
Do **not** report "skill creation complete" unless: quick-validate ✓, strict-validate ✓, internal acceptance ✓, integration proven. On failure: report exact failures + recommended next step.

## Gotchas
1. **validate-skill checks structure, not quality** — golden case test (Step 6 #8-9) is the real quality gate
2. **"Fill with real content" is the most common shortcut** — agents write generic filler; cross-check golden cases
3. **Triggers must have negative cases** — broad triggers like "make" cause collisions; run detect-overlap.sh
4. **research/ is ephemeral** — archive after creation; don't ship in the skill
5. **Description ≠ documentation** — description is for routing, not for humans. Run description_optimizer.py.
6. **Less-is-more is real** — SkillReducer research: 39% body reduction → 2.8% quality improvement. Don't pad skills.

## Error Handling
- **< 3 golden cases**: Stop. Ask for references or broaden search. Never fabricate.
- **Validation failure**: Return to Step 2/3. Almost always research, not structure.
- **Blocked by dependencies**: Record explicitly. Don't guess or skip.
- **Overclaiming readiness**: If implementation < documentation maturity, downgrade.

## Output Structure
```
{skill-name}/
├── SKILL.md          # Core methodology
├── scripts/          # Python preferred, bash thin wrappers
├── references/       # Supporting docs
└── config/           # Config files
```

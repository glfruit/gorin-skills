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
**先扫当前对话历史**：如果用户正在做某件事（用了哪些工具、走了哪些步骤、做了哪些纠正），直接从对话中提取 workflow，不要让用户从零描述。缺失的细节再问。

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

#### Writing Style
- **解释 why，不要堆 MUST**：如果你发现自己在写 ALWAYS / NEVER / MUST，停下来，改成解释为什么这件事重要。LLM 理解动机比遵守规则更可靠。规则越多，skill 越脆。
- **用祈使句**，不用被动语态。`Read the file first` 比 `The file should be read first` 更清晰。
- **举例胜过描述**：与其说“格式要规范”，不如给一个 before/after 对比。

#### Description 字段写作原则
Claude 有“undertrigger”倒向——即使描述匹配，也可能不触发 skill。写 description 时要适度主动：
- 不只说“this skill does X”，还要说“use this skill whenever Y / Z / W，even if the user doesn't explicitly mention X”
- 把触发场景的关键词写进 description，不要只放在 triggers 数组里
- description 是路由机制，不是文档——面向 Claude 的路由判断，不是面向人类阅读

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

**Baseline 对比（改进已有 skill 时必须执行）**：
- 改进前先快照旧版：`cp -r <skill-path> /tmp/<skill-name>-snapshot/`
- 用相同测试用例跑旧版和新版，对比输出质量
- 没有 baseline 对比，无法证明改进有效

If validation fails → return to Step 2 or 3 (almost always insufficient research).

### Step 7: Eval Loop（迭代验证）
运行真实测试用例，邀请用户 review 输出质量，根据反馈改进，再跑一遍。结构：

```
<skill-name>-workspace/
├── iteration-1/
│   ├── eval-0/
│   │   ├── with_skill/outputs/
│   │   ├── without_skill/outputs/   # 新建时；改进时用 old_skill/
│   │   └── eval_metadata.json
│   └── benchmark.json
├── iteration-2/
│   └── ...
```

每轮 eval 至少 2-3 个真实测试用例。用户 review 后给出反馈，改进 skill，进入下一轮。
停止条件：用户满意 / 反馈全为空 / 已无实质性改进空间。

### Step 8: Internal Acceptance
Run one real happy-path case with concrete input. If fails: keep fixing. Record: command, input, expected/actual, result.
Update `references/creation-patterns/{type}.md` with lessons learned.

### Step 9: Prove Integration
Run through upstream caller if applicable. Fix integration bugs before labeling `integrated`.

## Delivery Contract
Do **not** report "skill creation complete" unless: quick-validate ✓, strict-validate ✓, eval loop ≥ 1 iteration ✓, internal acceptance ✓, integration proven. On failure: report exact failures + recommended next step.

## Internal Acceptance
- **Happy-path**: 创建一个 Type 5 (Monitor) 技能 `test-health-check`
- **Invocation**: 直接调用 Step 1-6，在 `/tmp/test-health-check/` 生成
- **Expected**: SKILL.md（frontmatter + 必填段 + 无 placeholder）、Python 脚本、.skill-meta.json
- **Success**: validate-skill.sh + context_sizer Grade B+ + trigger_eval F1 ≥ 0.8

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

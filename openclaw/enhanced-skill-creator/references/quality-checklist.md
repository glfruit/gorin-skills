# Quality Checklist & Error Handling Reference

## Quality Checklist

Before declaring a skill complete, verify:

### Structure (automated — run validate-skill.sh)
- [ ] SKILL.md exists with valid YAML frontmatter
- [ ] `name` field: lowercase-hyphen format
- [ ] `description` field: 50+ characters with domain trigger words
- [ ] Core sections present (Overview, When to Use, Workflow)
- [ ] No placeholder text remaining
- [ ] Scripts have shebang lines and execute permissions
- [ ] No hardcoded user paths
- [ ] Under 500 lines

### Content (manual — Claude judges)
- [ ] Every workflow step has specific, actionable instructions
- [ ] Examples are real or clearly illustrative (not "example.com")
- [ ] Failure modes / "When NOT to Use" section exists
- [ ] **`## Gotchas` section exists with concrete failure points** (mandatory)
- [ ] Error Handling section exists or is explicitly justified as unnecessary
- [ ] Triggers cover natural phrasing (not just commands)
- [ ] No wildcard / catch-all trigger behavior exists
- [ ] Negative triggers are explicit and realistic
- [ ] Research sources are cited or traceable
- [ ] A competent agent could follow this skill and produce real output
- [ ] Data persistence uses stable paths outside the skill directory (if applicable)
- [ ] On-demand hooks documented if the skill defines any (if applicable)

### Methodology Depth
- [ ] Based on 3+ golden cases (not invented)
- [ ] Contains non-obvious insights a novice would miss
- [ ] Before/after comparisons for key decisions
- [ ] Domain-specific vocabulary used correctly

### Eval Readiness
- [ ] Includes 2-3 realistic trigger prompts for later testing
- [ ] Can be compared against a no-skill or previous-version baseline
- [ ] Description is explicit enough to trigger, but narrow enough to avoid collisions

### Readiness Honesty
- [ ] Internal readiness level is explicitly chosen: scaffold / mvp / production-ready / integrated
- [ ] Primary happy path has been run for real
- [ ] Documentation does not overclaim stubbed features
- [ ] Acceptance contract exists for artifact-generating skills
- [ ] Integrated call evidence exists before claiming integrated readiness
- [ ] User-facing completion is withheld unless readiness has actually reached integrated
- [ ] If integrated is not proven, the status reported outward is failed or blocked — not completed

## Error Handling

- If research yields fewer than 3 real golden cases, stop and ask for better references or broaden the search; do not fabricate sources.
- If metadata or triggers are broad, collision-prone, or include wildcard behavior, narrow them before packaging. Use `references/routing-safety.md`.
- If a skill requires dense rules, large templates, or deterministic parsing logic, move them into `references/`, `assets/`, or `scripts/` instead of bloating `SKILL.md`.
- If validation fails, report the exact failing checks and revise the skill; do not package a skill with unresolved structural or routing-safety failures.
- If the workflow cannot continue without guessing, record the blocker explicitly and ask for clarification or add the missing rule/resource.
- If implementation maturity is lower than documentation maturity, downgrade the skill's readiness label instead of pretending the missing parts do not matter.
- If no real artifact has been produced, do not claim `mvp` or above.

## Anti-Patterns (Lessons from This Skill's Previous Version)

These are real failures from the previous enhanced-skill-creator implementation:

| Anti-Pattern | What Happened | Lesson |
|-------------|---------------|--------|
| Mock research | `research.ts` returned fabricated data with fake URLs | Research must produce real sources or fail explicitly |
| Template-only output | Generated SKILL.md had "Step one / Step two" placeholders | Every section must contain domain-specific content |
| Over-engineering | 6 TypeScript files + bun dependency for what Claude does natively | SKILL.md itself is the skill — scripts are optional helpers |
| Simulated tests | `test-suite.ts` passed by testing mock data against mock expectations | Tests must validate real artifacts |
| Shell injection | `version-manager.ts` passed user input to `git` without escaping | Always quote variables in shell commands |
| Disconnected research | Research output was never fed into skill generation | Research must directly inform generated content |
| Runtime assumptions | Scripts required `bun` without checking availability | Use bash or check dependencies explicitly |
| Pipeline theater | 5-stage pipeline gave the appearance of rigor without substance | Process without real content is worse than no process |

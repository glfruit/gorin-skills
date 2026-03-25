---
name: enhanced-skill-creator
description: "Create high-quality skills using case-based methodology from domain masters. Research real examples, extract patterns, and generate skills with real content. Use when the user wants to create or rebuild an AgentSkill. Don't use it for simple one-off script edits, trivial aliases, or direct minor SKILL.md tweaks."
triggers: ["create skill", "build skill", "make a skill", "new skill", "design skill"]
user-invocable: true
agent-usable: true
---

# Enhanced Skill Creator

> "The hard part of creating a skill isn't the format — it's knowing the best way to do the thing."

A skill is a methodology document that teaches Claude how to perform a task expertly. This skill guides creation of new skills by researching real-world best practices, extracting patterns, and generating skills filled with genuine content — never placeholder templates.

## Core Principles

- **Concise is mandatory**: Every section must justify its token cost with specific, reusable value
- **Set the right degree of freedom**: High (judgment matters) / Medium (parameterized) / Low (fragile, encode in scripts)
- **Progressive disclosure**: SKILL.md (trigger + workflow) → references/ (dense detail) → scripts/ (automation) → assets/ (templates)
- **Ask for concrete use cases before designing**: Start from realistic use cases, not vague requests

## When to Use

- Creating a **new** skill from scratch
- Rebuilding a skill that produces generic or low-quality output
- The domain requires expert knowledge that Claude doesn't have by default

## When NOT to Use

- Editing an existing skill (just edit the SKILL.md directly)
- The task is simple enough to be a bash script or alias
- The domain is trivial and needs no methodology

---

## 6-Step Workflow

### Step 1: Narrow the Task

Ask: Domain, Scenario (specific), Constraints (tools/APIs/paths), Audience (user/agent/both).

Consult `references/skill-taxonomy.md` to classify into one of 12 skill types. Check `references/creation-patterns/{type}.md` for accumulated experience.

**Output**: 2-3 sentence skill summary with type classification.

### Step 2: Find Golden Cases (Most Critical)

Search: local skills → vault knowledge → methodology database → web → GitHub.

**CHECKPOINT: STOP. Must have 3+ golden cases before continuing.**

**Output**: Research notes with real sources, URLs, and key quotes.

### Step 3: Extract Patterns

For each golden case: What makes it effective? What would a novice miss? What fails when done poorly?

Create before/after comparisons.

**Output**: Pattern list with evidence from specific cases.

### Step 4: Apply Theory (Optional)

Only add theoretical frameworks when they explain **why** the practical patterns work. No generic filler.

### Step 5: Generate the Skill

1. Start with skeleton: `scripts/init-skill.sh <name> <dir>` or copy `config/skill-template.md`
2. Fill every section with real content — no placeholders
3. Write scripts in Python (preferred) or bash (thin wrappers only)
4. Cross-check against golden cases
5. Assign internal readiness: `scaffold` / `mvp` / `production-ready` / `integrated`
6. **Include mandatory `## Gotchas` section** — highest-signal content
7. (Optional) On-demand hooks: session-scoped runtime safeguards
8. (Optional) Data persistence: append-only log, JSON, or SQLite with stable paths

**Content quality rules:**
- No placeholder text, no fake data, no wildcard triggers
- Triggers: specific enough to avoid false positives, broad enough to catch natural phrasing
- Include explicit negative triggers
- Keep SKILL.md lean; move dense rules to references/

**Validation**: `bash scripts/validate-skill.sh <new-skill-directory>`

### Step 6: Validate Structure and Routing

1. Golden case test — would this produce output as good as the cases?
2. Failure mode test — does it prevent known anti-patterns?
3. Discovery validation via `assets/discovery-validation-prompt.md`
4. Quick validate: `scripts/quick-validate.sh`
5. Strict validate: `scripts/validate-skill.sh`
6. Collision check: `scripts/detect-overlap.sh`
7. Blocker detection: `scripts/detect-blockers.sh`
8. Structure suggestions: `scripts/suggest-structure.sh`
9. Fix suggestions: `scripts/suggest-fixes.sh`
10. Error handling: `scripts/generate-error-handling.sh`
11. Peer comparison: check against `references/golden-examples.md`
12. Acceptance contract (for artifact-generating skills)

If validation fails, return to Step 2 or 3 — the issue is almost always insufficient research.

### Step 7: Internal Acceptance (Mandatory)

1. Define one real happy-path case in `## Internal Acceptance`
2. Run it for real with concrete input
3. Record command, input, expected/actual artifacts, result
4. If fails, keep fixing. Do not report completion.
5. **Update creation patterns** (`references/creation-patterns/{type}.md`) with lessons learned

### Step 8: Prove Integration

1. Run one real happy path end-to-end
2. If called by upstream workflow, run through that caller
3. Fix integration bugs before labeling `integrated`

## Delivery Rule (Non-Negotiable)

User-facing completion requires: quick validate ✓, strict validate ✓, internal acceptance ✓, one real integration path proven.

Do NOT tell the user a skill is "completed" unless readiness has reached `integrated`.

## Skill Repo Management

Self-created skills are version-controlled via `scripts/skill-repo-sync.py`. 详见 `references/skill-repo-management.md`

## Quality Checklist & Error Handling

详见 `references/quality-checklist.md`（完整检查清单、错误处理策略、反模式表）

## Skill Taxonomy

12 types: Tool Wrapper, API Integration, Pipeline, PKM Integration, Monitor, Interactive Reader, Content Generator, Library, Process Guide, Research, Meta-Skill, Reviewer. 详见 `references/skill-taxonomy-quick.md`

## Output Structure

```
{skill-name}/
├── SKILL.md              # Core methodology
├── scripts/              # Automation (Python preferred, bash for thin wrappers)
├── references/           # Supporting documentation
├── research/             # Research notes (if valuable)
└── config/               # Configuration files
```

No `README.md`, `INSTALL.md`, or `CHANGELOG.md` at skill root.

## Resources

| Resource | Path |
|----------|------|
| Skill template | `config/skill-template.md` |
| Master methodologies | `references/methodology-database.md` |
| Skill type guide | `references/skill-taxonomy.md` |
| Design patterns | `references/google-adk-patterns.md` |
| Golden examples | `references/golden-examples.md` |
| Failure patterns | `references/failure-patterns.md` |
| Quality standards | `references/quality-standards.md` |
| Readiness gates | `references/readiness-gates.md` |
| Internal acceptance | `references/internal-acceptance.md` |
| Routing safety | `references/routing-safety.md` |
| Description engineering | `references/description-engineering.md` |
| Parameter design | `references/parameter-design.md` |
| Eval playbook | `references/eval-playbook.md` |
| Output schema | `references/output-schema.md` |
| MVP plan | `references/mvp-implementation-plan.md` |
| Usage tracking | `references/skill-usage-tracking.md` |
| Distribution | `references/skill-distribution.md` |
| Creation patterns | `references/creation-patterns/` |
| Discovery eval prompt | `assets/discovery-validation-prompt.md` |
| Error handling template | `assets/error-handling-template.md` |
| Acceptance contract | `assets/acceptance-contract-template.md` |

---
name: enhanced-skill-creator
description: "Create high-quality skills using case-based methodology from domain masters. Research real examples, extract patterns, and generate skills with real content. Use when the user wants to create or rebuild an AgentSkill. Don't use it for simple one-off script edits, trivial aliases, or direct minor SKILL.md tweaks."
triggers: ["create skill", "build skill", "make a skill", "new skill", "design skill"]
user-invocable: true
agent-usable: true
---

# Enhanced Skill Creator

> "The hard part of creating a skill isn't the format — it's knowing the best way to do the thing."
> — skill-from-masters

---

## Updates

**2026-03-25**: Added **gorin-skills repo management** — version-controlled skill storage via `scripts/skill-repo-sync.py`:
- New `## Skill Repo Management` section with setup and daily workflow
- New script `scripts/skill-repo-sync.py` — clone/pull/push/link/unlink/add/remove/status/list
- Repo URL configured via `GORIN_SKILLS_REPO` env var (never hardcoded)
- Updated `references/skill-distribution.md` with repo-based workflow
- Skills in repo are symlinked into `~/.openclaw/skills/` for OpenClaw loading

**2026-03-19**: Integrated insights from [Anthropic Thariq's "Lessons from Building Claude Code: How We Use Skills"](https://www.anthropic.com/engineering/claude-code-skills) (2026-03-17):
- Added **mandatory `## Gotchas` section** in Step 5 — highest-signal content in any skill
- Added **on-demand hooks guidance** — session-scoped runtime safeguards (`/careful`, `/freeze`)
- Added **data persistence guidance** — stable storage paths, format choices, migration notes
- Created `references/skill-usage-tracking.md` — PreToolUse hook tracking with JSONL schema
- Created `references/skill-distribution.md` — repo, workspace, ClawHub, npm distribution strategies
- Updated `references/golden-examples.md` — added frontend-design, signup-flow-driver, standup-post
- Updated `config/skill-template.md` — Gotchas, Hooks, and Data Persistence sections

**2026-03-18**: Integrated [Google Cloud Tech's 5 Agent Skill design patterns](https://x.com/GoogleCloudTech/status/2033953579824758855) (by Shubham Saboo and Lavinigam):
- Added **Reviewer** as a new skill type (type 12)
- Added **Design Patterns** section to taxonomy (Tool Wrapper, Generator, Reviewer, Inversion, Pipeline)
- Updated skill template with pattern-specific structure guidance
- Added complete pattern examples to golden-examples.md
- Created `references/google-adk-patterns.md` with detailed implementation guide

---

A skill is a methodology document that teaches Claude how to perform a task expertly. This skill guides the creation of new skills by researching real-world best practices from domain masters, extracting actionable patterns, and generating skills filled with genuine content — never placeholder templates.

## Upstream Alignment

This enhanced version extends the latest official `skill-creator` rather than replacing it wholesale.

Inherited non-negotiables from the official skill:
- Keep `SKILL.md` concise; context is a shared resource.
- Match the degree of freedom to the fragility of the task.
- Use progressive disclosure: core workflow in `SKILL.md`, dense detail in `references/`, deterministic repeatable logic in `scripts/`, output resources in `assets/`.
- Do not create auxiliary clutter such as `README.md`, `INSTALL.md`, or `CHANGELOG.md` inside the skill root unless there is a strong independent product reason.

This enhanced version adds:
- case-based research and “golden case” extraction,
- explicit anti-pattern analysis,
- stronger routing-safety checks,
- stronger shell/script quality checks,
- real-content generation requirements instead of template-only scaffolds,
- readiness gates that distinguish `scaffold`, `mvp`, `production-ready`, and `integrated`,
- doc/implementation consistency checks so polished docs cannot outrun the code.

## Core Principles

### Concise Is Still Mandatory

The model is already capable. Do not spend tokens explaining generic concepts it already knows.
Every section must justify its token cost with specific, reusable value.

### Set the Right Degree of Freedom

- **High freedom**: text workflows where judgment matters
- **Medium freedom**: parameterized scripts or structured playbooks
- **Low freedom**: fragile operations that must run the same way every time

If a workflow breaks easily, encode it into `scripts/` or decision tables instead of loose prose.

### Use Progressive Disclosure

Default structure:
- `SKILL.md`: trigger guidance, workflow, routing boundaries
- `references/`: dense background, schemas, long examples, quality bars
- `scripts/`: deterministic helpers and validators
- `assets/`: templates or reusable output resources

Never duplicate the same information in both `SKILL.md` and `references/`.

### Ask for Concrete Use Cases Before Designing

When the user is creating a new skill, start from realistic use cases and failure cases.
Do not jump from a vague request straight into scaffolding.

## When to Use

- Creating a **new** skill from scratch
- Rebuilding a skill that produces generic or low-quality output
- The domain requires expert knowledge that Claude doesn't have by default

## When NOT to Use

- Editing an existing skill (just edit the SKILL.md directly)
- The task is simple enough to be a bash script or alias
- The domain is trivial and needs no methodology (e.g., "echo hello")

---

## 6-Step Workflow

### Step 1: Narrow the Task

Clarify what the skill does before researching how. Ask the user:

1. **Domain**: What field does this skill operate in?
2. **Scenario**: What specific task does it accomplish? (Not "writing" but "writing technical blog posts for developer audiences")
3. **Constraints**: What tools/APIs/paths must it use? Any limits?
4. **Audience**: Who triggers this skill?
   - `user-invocable: true` — user says "do X" in chat
   - `agent-usable: true` — other skills/agents call it programmatically
   - Both — most common for utility skills

Consult `references/skill-taxonomy.md` to identify which of the 11 skill types this falls under. The type determines the template emphasis (e.g., Tool Wrapper needs config + error handling, Process Guide needs step-by-step workflow).

Do not overwhelm the user with a long questionnaire. Ask only the minimum set of questions needed to establish:
- what should trigger the skill,
- what should not trigger it,
- what files, systems, or commands it must use,
- what successful output looks like.

**Output**: 2-3 sentence skill summary with type classification.

---

### Step 2: Find Golden Cases (Most Critical Step)

Research real examples that demonstrate excellence in this domain. You need evidence, not intuition.

**Search in this order:**

1. **Local skills** — Run `ls skills/` and read 3-5 SKILL.md files from similar skills. These are your strongest references because they follow the same format and conventions.

2. **Vault knowledge** — Use `obsidian-search` to find related methodology notes, Zettelkasten entries, or prior research in the user's PKM vault.

3. **Methodology database** — Check `references/methodology-database.md` for established frameworks in this domain (e.g., Minto Pyramid for writing, TDD for testing, JTBD for product).

4. **Web search** — Search for:
   - `"{domain} best practices" site:github.com`
   - `"{domain} expert methodology"`
   - `"{domain} common mistakes beginners make"`

5. **GitHub search** — Find similar tools, automation projects, or skill definitions that solve the same problem.

**CHECKPOINT: STOP here. You must have 3+ golden cases before continuing.**

If you cannot find 3 golden cases:
- Broaden the search terms
- Look at adjacent domains
- Ask the user for references they trust
- Do NOT proceed with fewer than 3 real examples

**Output**: Research notes with real sources, URLs, and key quotes. Save to `research/{skill-name}-research.md` if the research is substantial.

---

### Step 3: Extract Patterns

For each golden case from Step 2, analyze:

1. **What specifically makes it effective?** — Not "it's well-organized" but "it uses a decision table for choosing between 4 caching strategies based on data size and read/write ratio"
2. **What would a novice miss?** — The non-obvious insights that separate expert from beginner output
3. **What fails when this is done poorly?** — Check `references/failure-patterns.md` for common anti-patterns

Create before/after comparisons:

| Aspect | Naive Approach | Expert Approach |
|--------|---------------|-----------------|
| {topic} | {what beginners do} | {what the golden case does} |

**Output**: Pattern list with evidence from specific cases.

---

### Step 4: Apply Theory (Optional)

Only add theoretical frameworks when they explain **why** the practical patterns from Step 3 work. Theory without case support is filler.

Good: "The Zettelkasten method explains why linking notes bidirectionally (as seen in idea-creator's 5-Type relations) produces emergent insights — each note becomes a node in a thinking network."

Bad: "According to cognitive load theory, skills should minimize extraneous information." (True but generic — doesn't help write better skills.)

---

### Step 5: Generate the Skill

Build the skill using research from Steps 2-4:

1. **Start with the skeleton**: Run `scripts/init-skill.sh <skill-name> <output-dir> [resources]` or copy `config/skill-template.md` as the structural base
2. **Fill every section with real content**: Replace each `{REPLACE: ...}` marker with content derived from your research. Every section must contain specific, actionable guidance — not generic advice.
3. **Write scripts in Python (preferred) or bash**: If the skill needs automation scripts, prefer Python for anything involving structured data (JSON, config, state). Use bash only for thin wrappers (`exec python3 ...`) or minimal system glue. Follow SCRIPT_POLICY.md and patterns from existing project scripts:
   - Python: use `oclib` shared library (`~/.openclaw/lib/oclib/`) for config, state, notify, lock, log
   - Bash wrappers: use `set -euo pipefail`, set `PYTHONPATH`, `exec python3`
   - No hardcoded `/Users/` paths — use `$HOME`, `Path.home()`, or config variables
   - Validate inputs before processing
   - Output JSON for programmatic consumers, text for humans
   - Note: `validate-skill.sh` will check shebang, executable bit, syntax, and `shellcheck` (for .sh) or `py_compile` (for .py)
4. **Cross-check against golden cases**: Each major section should trace back to evidence from Step 2
5. **Assign an internal readiness target**:
   - `scaffold` if structure is done but runnable evidence is absent
   - `mvp` if one real happy path is expected
   - `production-ready` only if validation and output contract will exist
   - `integrated` only if an upstream workflow will actually call it
   - These labels are **internal only** until Step 8 is proven. Do not tell the user the skill is "completed" unless readiness has actually reached `integrated`.

6. **Include a `## Gotchas` section (mandatory)** — This is the highest-signal section of any skill. Gotchas capture the failures and edge cases that only emerge from real usage:
   - Common failure points where Claude (or the user) reliably goes wrong
   - Boundary conditions that cause silent errors or wrong output
   - Non-obvious ordering constraints ("must run X before Y")
   - Things that look right but produce subtly wrong results
   - Gotchas are living content: every time an agent using this skill makes a mistake, add the lesson here
   - Format as concise bullets or a table — never generic advice

7. **(Optional) On-demand Hooks** — For skills that need runtime safeguards, configure on-demand hooks that activate only when the skill is invoked and auto-expire when the session ends:
   - Example: `/careful` — intercepts destructive operations (delete, overwrite, force-push) and requires explicit confirmation
   - Example: `/freeze` — restricts write scope to a specific directory tree, blocking writes outside it
   - Hooks are scoped to the session; they do not persist or require installation
   - Add a `## Hooks` section to the SKILL.md listing available hooks and their behavior
   - Include hook configuration section in `config/skill-template.md` if applicable

8. **(Optional) Data Persistence** — If the skill needs to maintain state across invocations:
   - **Append-only log** (`data/activity.log`): Best for audit trails, simple and crash-safe
   - **JSON file** (`data/state.json`): Best for structured state that needs read-modify-write
   - **SQLite** (`data/skill.db`): Best for concurrent access or complex queries
   - **Critical**: Use stable storage paths outside the skill directory (e.g., OpenClaw workspace `~/.openclaw/workspace-{name}/` or a dedicated data dir). The skill directory itself may be overwritten during upgrades
   - Document the storage path, schema, and migration strategy in the SKILL.md

Also enforce the official skill anatomy:
- Keep root clean: `SKILL.md` plus only `scripts/`, `references/`, `assets/`, `research/`, or `config/` when justified
- Do not create convenience docs that duplicate the skill itself
- If the skill grows beyond a lean `SKILL.md`, move detailed material into `references/` rather than letting the main file sprawl

**Content quality rules:**
- No placeholder text ("Step one", "example.com", "TODO", "placeholder")
- No fake data or mock results
- Every example must be real or clearly marked as illustrative
- Triggers must be specific enough to avoid false positives, broad enough to catch natural phrasing
- Never use wildcard or catch-all trigger patterns such as `*`, `.*`, `any request`, or `all tasks`
- Every skill description must include explicit negative triggers (what should NOT trigger the skill)
- Keep `SKILL.md` lean; move dense rules to `references/`, templates to `assets/`, and deterministic repeatable logic to `scripts/`
- Include both English and Chinese triggers if the user base is bilingual

Read `references/routing-safety.md` before finalizing metadata or trigger phrasing.
Read `references/readiness-gates.md` before deciding what maturity claims are allowed.

**Run structural validation:**
```bash
bash scripts/validate-skill.sh <new-skill-directory>
```

---

### Step 6: Validate Structure and Routing

Test the generated skill against your research and quality bars:

1. **Golden case test**: Would this skill produce output as good as the golden cases from Step 2?
2. **Failure mode test**: Does it prevent the failure patterns documented in `references/failure-patterns.md`?
3. **Discovery validation**: Use `assets/discovery-validation-prompt.md` to test trigger quality and routing safety
4. **Quick validation**: Run `scripts/quick-validate.sh` for fast structural feedback
5. **Structural validation**: Run `scripts/validate-skill.sh` and fix any failures
6. **Collision check**: Run `scripts/detect-overlap.sh` and review whether the metadata overlaps or competes with existing skills
7. **Blocker detection**: Run `scripts/detect-blockers.sh` to identify missing fallbacks, ambiguity hotspots, and hidden execution assumptions
8. **Structure suggestions**: Run `scripts/suggest-structure.sh` to identify candidate content that should move into `assets/`, `scripts/`, or `references/`
9. **Fix suggestions**: Run `scripts/suggest-fixes.sh` to get low-risk rewrite and insertion drafts for common failures
10. **Error handling draft**: Run `scripts/generate-error-handling.sh` and adapt the generated section to the real blockers and failure modes of the skill
11. **Peer comparison**: Compare the generated SKILL.md against `references/golden-examples.md` — does it reach the same quality bar?
12. **Acceptance contract**: For any artifact-generating or integration-heavy skill, create a short acceptance contract from `assets/acceptance-contract-template.md`.

If validation fails, return to Step 2 or Step 3 — the issue is almost always insufficient research, not formatting.

### Step 7: Internal Acceptance (Mandatory)

Every new skill must pass one internal acceptance run before you can consider it deliverable.

1. Define one real happy-path case in `## Internal Acceptance`.
2. Run the path for real with a concrete input.
3. Record:
   - command or invocation path,
   - concrete input,
   - expected artifacts,
   - actual artifact paths,
   - result: `passed` / `failed` / `blocked`.
4. Use `scripts/run-acceptance.sh` when a command-and-artifact path can be executed deterministically.
5. If the acceptance run fails, keep fixing. Do not report completion to the user.
6. If the acceptance run is blocked by external constraints, report the blocker explicitly and do not call the skill complete.

### Step 8: Prove Integration

For any skill that claims to be complete, prove the path that matters end-to-end:

1. Run one real happy path end-to-end.
2. If the skill is meant to be called by another workflow, run it once through that upstream caller.
3. Fix any integration bugs before changing the readiness label to `integrated`.
4. Package only after quick validate, strict validate, and internal acceptance all pass.

Do not stop at "the script looks right." If the skill is supposed to produce HTML, PNG, Markdown, API side effects, or workflow artifacts, one of those artifacts must exist before you call it ready.

## Delivery Rule (Non-Negotiable)

- `scaffold`, `mvp`, and `production-ready` are **internal** states only.
- Do **not** tell the user a skill is "created/completed" unless internal readiness has reached `integrated`.
- User-facing completion requires:
  1. quick validate passed,
  2. strict validate passed,
  3. internal acceptance passed,
  4. one real integration path proven.
- If any of the above is missing, report `failed` or `blocked` instead of pretending the skill is complete.

---

## Skill Repo Management

Self-created skills are version-controlled in the **gorin-skills** git repo, synced to OpenClaw via symlinks.

### Setup (One-Time)

```bash
# 1. Set repo URL (add to ~/.zshrc or openclaw config env)
export GORIN_SKILLS_REPO=git@github.com:glfruit/gorin-skills.git

# 2. Clone and link
python3 scripts/skill-repo-sync.py clone
python3 scripts/skill-repo-sync.py link

# 3. Verify
python3 scripts/skill-repo-sync.py status
```

The `GORIN_SKILLS_REPO` env var is **required** — never hardcode the URL in any script or SKILL.md. Default local clone path is `~/.gorin-skills` (override with `GORIN_SKILLS_DIR`).

### How It Works

```
~/.gorin-skills/skills/my-skill/   ← canonical source (git tracked)
        ↓ symlink
~/.openclaw/skills/my-skill/      ← OpenClaw loads from here
```

- `link` creates individual symlinks (not directory-level) so coexistence with other skill sources works
- `unlink` removes symlinks without touching repo files
- OpenClaw's `skills.load.extraDirs` is automatically updated to include the repo path

### Daily Workflow

**After creating a new skill** (reaches `integrated` readiness):
```bash
python3 scripts/skill-repo-sync.py add <skill-name>
python3 scripts/skill-repo-sync.py push "add <skill-name> skill"
python3 scripts/skill-repo-sync.py link
```

**After editing an existing skill**:
```bash
python3 scripts/skill-repo-sync.py push "update <skill-name>: <brief change>"
```

**After pulling on another machine**:
```bash
python3 scripts/skill-repo-sync.py pull
python3 scripts/skill-repo-sync.py link
```

**Check status**:
```bash
python3 scripts/skill-repo-sync.py status    # repo + symlink + config status
python3 scripts/skill-repo-sync.py list      # skills in repo
```

### When Creating Skills

In Step 5 (Generate the Skill), after validation passes:
1. Create the skill in `~/.openclaw/skills/<name>/` as normal
2. Run `python3 scripts/skill-repo-sync.py add <name>` to copy to repo
3. The symlink is created automatically by `add`
4. On `push`, changes in the repo are committed

### Integration with Step 8

When a skill reaches `integrated` readiness and the user confirms acceptance, offer to:
1. `add` the skill to the repo
2. `push` with a descriptive commit message
3. Verify the symlink is active

Do NOT auto-push without user confirmation.

---

## Error Handling

- If research yields fewer than 3 real golden cases, stop and ask for better references or broaden the search; do not fabricate sources.
- If metadata or triggers are broad, collision-prone, or include wildcard behavior, narrow them before packaging. Use `references/routing-safety.md`.
- If a skill requires dense rules, large templates, or deterministic parsing logic, move them into `references/`, `assets/`, or `scripts/` instead of bloating `SKILL.md`.
- If validation fails, report the exact failing checks and revise the skill; do not package a skill with unresolved structural or routing-safety failures.
- If the workflow cannot continue without guessing, record the blocker explicitly and ask for clarification or add the missing rule/resource.
- If implementation maturity is lower than documentation maturity, downgrade the skill's readiness label instead of pretending the missing parts do not matter.
- If no real artifact has been produced, do not claim `mvp` or above.

---

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

---

## Skill Taxonomy Quick Reference

| # | Type | Example | Key Trait |
|---|------|---------|-----------|
| 1 | Tool Wrapper | obsidian-search | Config + error handling + dual output |
| 2 | API Integration | send-email | Auth + retry + payload format |
| 3 | Pipeline/Orchestrator | content-curator-monitor | Multi-source + scoring + routing |
| 4 | PKM Integration | pkm-save-note, idea-creator | 5-type relations + vault paths |
| 5 | Monitor/Cron | system-health-check | launchd + schedule + alerts |
| 6 | Interactive Reader | book-reader-notes | State tracking + user rhythm |
| 7 | Content Generator | qwen-cover-image | API call + asset management |
| 8 | Library/Internal | example-library-skill | Not user-invocable, called by others |
| 9 | Process Guide | dev-workflow | Step-by-step + decision points |
| 10 | Research/Discovery | codex-deep-search | Search strategy + result synthesis |
| 11 | Meta-Skill | enhanced-skill-creator | Self-referential methodology |
| 12 | Reviewer | code-reviewer | Rubric + severity classification |

**Design Patterns** (cross-type, from [Google Cloud Tech](https://x.com/GoogleCloudTech/status/2033953579824758855)):
- **Tool Wrapper**: Dynamic loading of library conventions
- **Generator**: Template + variable filling for consistent output
- **Reviewer**: Checklist-driven analysis with severity levels
- **Inversion**: Agent interviews user before acting
- **Pipeline**: Strict multi-step workflow with checkpoints

Full details with examples and common pitfalls: `references/skill-taxonomy.md`  
Pattern implementation guide: `references/google-adk-patterns.md`

---

## Output Structure

A generated skill directory should follow this layout:

```
{skill-name}/
├── SKILL.md              # Core methodology (the skill itself)
├── scripts/              # Automation scripts (bash, optional)
│   └── *.sh
├── references/           # Supporting documentation (optional)
│   └── *.md
├── research/             # Research notes (optional, keep if valuable)
│   └── *-research.md
└── config/               # Configuration files (optional)
    └── *.{json,yaml,md}
```

Rules:
- No `README.md` at skill root (SKILL.md is the entry point)
- No `INSTALL.md` (installation goes in SKILL.md)
- No `CHANGELOG.md` unless the skill is versioned independently
- Scripts in Python by default; bash only for thin wrappers (see SCRIPT_POLICY.md)

---

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

---

## Resources

- **Skill template**: `config/skill-template.md`
- **Master methodologies**: `references/methodology-database.md`
- **Skill type guide**: `references/skill-taxonomy.md`
- **Design patterns**: `references/google-adk-patterns.md` — 5 patterns from Google Cloud Tech (Tool Wrapper, Generator, Reviewer, Inversion, Pipeline)
- **Golden examples**: `references/golden-examples.md`
- **Failure patterns**: `references/failure-patterns.md`
- **Quality standards**: `references/quality-standards.md`
- **Readiness gates**: `references/readiness-gates.md`
- **Internal acceptance**: `references/internal-acceptance.md`
- **Routing safety guide**: `references/routing-safety.md`
- **Description engineering**: `references/description-engineering.md`
- **Parameter design**: `references/parameter-design.md`
- **Eval playbook**: `references/eval-playbook.md`
- **Output schema**: `references/output-schema.md`
- **MVP implementation plan**: `references/mvp-implementation-plan.md`
- **Discovery eval prompt**: `assets/discovery-validation-prompt.md`
- **Error handling template**: `assets/error-handling-template.md`
- **Acceptance contract template**: `assets/acceptance-contract-template.md`
- **Scaffold generator**: `scripts/init-skill.sh`
- **Quick validation script**: `scripts/quick-validate.sh`
- **Validation script**: `scripts/validate-skill.sh`
- **Acceptance runner**: `scripts/run-acceptance.sh`
- **Package script**: `scripts/package-skill.sh`
- **Blocker detector**: `scripts/detect-blockers.sh`
- **Overlap checker**: `scripts/detect-overlap.sh`
- **Structure suggester**: `scripts/suggest-structure.sh`
- **Fix suggester**: `scripts/suggest-fixes.sh`
- **Shell quality runner**: `scripts/run-shell-quality.sh`
- **Error-handling generator**: `scripts/generate-error-handling.sh`
- **Research example**: `research/content-curator-monitor-research.md`
- **Usage tracking**: `references/skill-usage-tracking.md`
- **Distribution guide**: `references/skill-distribution.md`

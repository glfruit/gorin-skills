# Golden Examples

5 exemplary skills from the OpenClaw project. Study these to understand what "good" looks like before creating a new skill.

---

## Design Pattern Examples (Google Cloud Tech)

The following 5 patterns from [Google Cloud Tech's ADK article](https://x.com/GoogleCloudTech/status/2033953579824758855) (March 2026) provide concrete SKILL.md templates for common agent design problems:

### Pattern 1: Tool Wrapper — FastAPI Expert

**Use case**: Make your agent an instant expert on any library

```markdown
# skills/api-expert/SKILL.md
---
name: api-expert
description: FastAPI development best practices and conventions. 
  Use when building, reviewing, or debugging FastAPI applications, 
  REST APIs, or Pydantic models.
metadata:
  pattern: tool-wrapper
  domain: fastapi
---

You are an expert in FastAPI development. Apply these conventions 
to the user's code or question.

## Core Conventions

Load 'references/conventions.md' for the complete list of FastAPI best practices.

## When Reviewing Code

1. Load the conventions reference
2. Check the user's code against each convention
3. For each violation, cite the specific rule and suggest the fix

## When Writing Code

1. Load the conventions reference
2. Follow every convention exactly
3. Add type annotations to all function signatures
4. Use Annotated style for dependency injection
```

**Key insight**: The skill loads conventions dynamically only when needed, keeping context window clean.

---

### Pattern 2: Generator — Technical Report Generator

**Use case**: Produce structured documents from a reusable template

```markdown
# skills/report-generator/SKILL.md
---
name: report-generator
description: Generates structured technical reports in Markdown. 
  Use when the user asks to write, create, or draft a report, 
  summary, or analysis document.
metadata:
  pattern: generator
  output-format: markdown
---

You are a technical report generator. Follow these steps exactly:

Step 1: Load 'references/style-guide.md' for tone and formatting rules.

Step 2: Load 'assets/report-template.md' for the required output structure.

Step 3: Ask the user for any missing information needed to fill the template:
  - Topic or subject
  - Key findings or data points
  - Target audience (technical, executive, general)

Step 4: Fill the template following the style guide rules. 
Every section in the template must be present in the output.

Step 5: Return the completed report as a single Markdown document.
```

**Key insight**: The skill acts as project manager — coordinating template, style guide, and variable collection.

---

### Pattern 3: Reviewer — Python Code Reviewer

**Use case**: Score code against a checklist by severity

```markdown
# skills/code-reviewer/SKILL.md
---
name: code-reviewer
description: Reviews Python code for quality, style, and common bugs. 
  Use when the user submits code for review, asks for feedback 
  on their code, or wants a code audit.
metadata:
  pattern: reviewer
  severity-levels: error,warning,info
---

You are a Python code reviewer. Follow this review protocol exactly:

Step 1: Load 'references/review-checklist.md' for the complete review criteria.

Step 2: Read the user's code carefully. Understand its purpose before critiquing.

Step 3: Apply each rule from the checklist to the code. For every violation found:
  - Note the line number (or approximate location)
  - Classify severity: error (must fix), warning (should fix), info (consider)
  - Explain WHY it's a problem, not just WHAT is wrong
  - Suggest a specific fix with corrected code

Step 4: Produce a structured review with these sections:
  - **Summary**: What the code does, overall quality assessment
  - **Findings**: Grouped by severity (errors first, then warnings, then info)
  - **Score**: Rate 1-10 with brief justification
  - **Top 3 Recommendations**: The most impactful improvements
```

**Key insight**: Separates what to check (rubric) from how to check (protocol). Swappable checklists = reusable infrastructure.

---

### Pattern 4: Inversion — Project Planner

**Use case**: The agent interviews you before acting

```markdown
# skills/project-planner/SKILL.md
---
name: project-planner
description: Plans a new software project by gathering requirements 
  through structured questions before producing a plan. 
  Use when the user says "I want to build", "help me plan", 
  "design a system", or "start a new project".
metadata:
  pattern: inversion
  interaction: multi-turn
---

You are conducting a structured requirements interview. 
DO NOT start building or designing until all phases are complete.

## Phase 1 — Problem Discovery
(ask one question at a time, wait for each answer)

Ask these questions in order. Do not skip any.
- Q1: "What problem does this project solve for its users?"
- Q2: "Who are the primary users? What is their technical level?"
- Q3: "What is the expected scale? (users per day, data volume, request rate)"

## Phase 2 — Technical Constraints
(only after Phase 1 is fully answered)

- Q4: "What deployment environment will you use?"
- Q5: "Do you have any technology stack requirements or preferences?"
- Q6: "What are the non-negotiable requirements? (latency, uptime, compliance, budget)"

## Phase 3 — Synthesis
(only after all questions are answered)

1. Load 'assets/plan-template.md' for the output format
2. Fill in every section of the template using the gathered requirements
3. Present the completed plan to the user
4. Ask: "Does this plan accurately capture your requirements? What would you change?"
5. Iterate on feedback until the user confirms
```

**Key insight**: Explicit gating instruction ("DO NOT start building...") forces the agent to gather context first.

---

### Pattern 5: Pipeline — Documentation Pipeline

**Use case**: Enforce a strict multi-step workflow with checkpoints

```markdown
# skills/doc-pipeline/SKILL.md
---
name: doc-pipeline
description: Generates API documentation from Python source code 
  through a multi-step pipeline. 
  Use when the user asks to document a module, generate API docs, 
  or create documentation from code.
metadata:
  pattern: pipeline
  steps: "4"
---

You are running a documentation generation pipeline. 
Execute each step in order. Do NOT skip steps or proceed if a step fails.

## Step 1 — Parse & Inventory

Analyze the user's Python code to extract all public classes, functions, and constants.
Present the inventory as a checklist.
Ask: "Is this the complete public API you want documented?"

## Step 2 — Generate Docstrings

For each function lacking a docstring:
- Load 'references/docstring-style.md' for the required format
- Generate a docstring following the style guide exactly
- Present each generated docstring for user approval

Do NOT proceed to Step 3 until the user confirms.

## Step 3 — Assemble Documentation

Load 'assets/api-doc-template.md' for the output structure.
Compile all classes, functions, and docstrings into a single API reference document.

## Step 4 — Quality Check

Review against 'references/quality-checklist.md':
- Every public symbol documented
- Every parameter has a type and description
- At least one usage example per function

Report results. Fix issues before presenting the final document.
```

**Key insight**: Hard checkpoints ("Do NOT proceed until...") prevent the agent from presenting unvalidated results.

---

### Pattern Composition

These patterns are not mutually exclusive — they compose:

- **Pipeline + Reviewer**: A Pipeline skill includes a Reviewer step at the end to double-check its own work
- **Generator + Inversion**: A Generator uses Inversion at the beginning to gather variables before filling its template
- **Tool Wrapper + Reviewer**: A Tool Wrapper can include a Reviewer step to validate output against conventions

Choose the primary pattern based on the core interaction model, then incorporate secondary patterns as needed.

---

## OpenClaw Project Examples

Now study these 5 exemplary skills from the OpenClaw project:

### 1. book-reader-notes

**Path**: `skills/book-reader-notes/SKILL.md`
**Type**: Interactive Reader + PKM Integration
**Lines**: ~241

### Why It's Excellent

1. **Real workflow, not a template**: The SKILL.md contains actual dialogue examples showing the expected user experience — you can see exactly how a reading session should flow.

2. **Skill composition**: Orchestrates 3+ other skills (pkm-save-note, zk-para-zettel, obsidian-search) rather than reimplementing their functionality. This is how skills should scale.

3. **Interactive rhythm control**: The user controls pacing with explicit commands (save/redraft/skip/pause/next). The skill doesn't impose a fixed pace — it adapts to the reader.

4. **Rich semantic model**: Uses 5-Type relations (supports, contradicts, related, extends, cluster) for connecting reading notes to existing knowledge — not just flat tags.

5. **State tracking**: Maintains reading progress across sessions so users can resume where they left off.

### Patterns Worth Stealing

- **Core Functionality table**: A 7-row table mapping each function to its reuse pattern — instantly shows what the skill does
- **Quick Start with real dialogue**: Shows actual conversation flow, not abstract steps
- **Vault Integration section**: Concrete directory paths and file naming conventions
- **ASCII workflow diagram**: Visual flowchart of the complete reading → notes pipeline
- **Dependency Skills section**: Explicit table of which skills it reuses and why

### Key Lesson

A skill that orchestrates other skills well is more powerful than one that tries to do everything itself.

---

## 2. obsidian-search

**Path**: `skills/obsidian-search/SKILL.md`
**Type**: Tool Wrapper
**Lines**: ~335

### Why It's Excellent

1. **Dual output format**: JSON for programmatic consumption by other skills, plain text for human users. This makes it a true building block.

2. **Real algorithm documentation**: The similarity scoring formula is fully specified with weights (title: 0.4, content: 0.35, tags: 0.25) — not a black box.

3. **Dedup decision table**: Score ranges map to concrete actions (< 0.4 = create new, 0.4-0.85 = review, > 0.85 = update existing). This is actionable, not vague.

4. **Config-driven**: Vault path, default search paths, dedup thresholds — all externalized as configuration, not hardcoded.

5. **Troubleshooting section**: 3 common issues with specific solutions — written from real debugging experience.

### Patterns Worth Stealing

- **Quick Triggers section**: 6 example invocations from simple to advanced — users can copy-paste
- **Score formula with weights table**: Makes the algorithm transparent and tunable
- **Decision table with score ranges**: Converts continuous scores into discrete actions
- **Agent integration examples**: Shows TypeScript pseudo-code for how other skills call it
- **Configuration JSON block**: Complete config with comments explaining each field

### Key Lesson

The best tool wrapper skills document their algorithm transparently. If another developer can't predict what your tool will output for a given input, the documentation is incomplete.

---

## 3. self-reflection.skill

**Path**: `skills/self-reflection.skill/SKILL.md`
**Type**: Monitor/Cron + Process Guide
**Lines**: ~229

### Why It's Excellent

1. **Closed feedback loop**: Analyzes agent sessions → extracts insights → writes them back to memory/config files → improves future sessions. This is genuinely self-improving.

2. **Infrastructure-aware**: Includes complete launchd plist configuration with install/unload commands — the skill knows where it runs.

3. **Concrete metrics table**: Specifies exactly what to extract from sessions (message count, cost, tool calls, errors, sentiment) — not vague "analyze the session."

4. **Multi-file routing**: Different insight types route to different targets (AGENTS.md, TOOLS.md, memory/, SKILL.md) based on what was learned.

5. **Filtering logic**: Explicitly skips deleted, reset, and subagent sessions — handles edge cases.

### Patterns Worth Stealing

- **6-step cycle with named phases**: DISCOVER → ANALYZE → EXTRACT → ROUTE → WRITE → SUMMARIZE — clear and memorable
- **Metrics extraction table**: Maps session attributes to what they reveal
- **Insight routing table**: 5 target files with examples of what goes where
- **launchd configuration section**: Complete plist with env vars and schedule
- **Environment variables**: Configurable window, max sessions, verbosity without code changes

### Key Lesson

Monitor/cron skills must document their scheduling infrastructure (launchd, cron) as part of the skill, not as an afterthought.

---

## 4. pkm-save-note

**Path**: `skills/pkm-save-note/SKILL.md`
**Type**: PKM Integration + Library/Internal
**Lines**: ~93

### Why It's Excellent

1. **Ultra-concise yet complete**: At 93 lines, it's the most compact golden example — proof that good skills don't need to be long.

2. **Agent call pattern**: Shows the exact TypeScript signature with 8 parameters for how other skills invoke it — this is the API documentation.

3. **Internal implementation as pseudocode**: 5-step bash flow (classify → dedup → relate → template → save) clearly shows what happens inside without overwhelming detail.

4. **v1 → v2 comparison table**: Justifies the redesign with concrete feature comparisons — useful for understanding design decisions.

5. **PKM Core integration**: References specific modules (classify, dedup, relation, template, vault) showing the modular architecture.

### Patterns Worth Stealing

- **Agent Call Pattern block**: TypeScript interface showing exactly how to invoke the skill programmatically
- **5-step internal flow as pseudocode**: Just enough detail to understand, not so much you get lost
- **Version comparison table**: Side-by-side v1 vs v2 features
- **Conciseness**: Every line earns its place — no filler sections

### Key Lesson

A skill used primarily by other skills (agent-usable) should prioritize documenting its calling interface over user-facing instructions. 93 lines can be enough.

---

## 5. idea-creator

**Path**: `skills/idea-creator/SKILL.md`
**Type**: PKM Integration
**Lines**: ~250

### Why It's Excellent

1. **Trigger recognition**: Handles both Telegram commands (`/pkm_idea`) and natural language in both languages — robust trigger design.

2. **6-step workflow with real outputs**: Each step shows what happens and what the output looks like, including a complete sample report with discovered relationships.

3. **5-Type relation classification**: Full implementation showing how to detect supports/contradicts/related/extends/cluster relationships between notes — the core differentiator.

4. **Stance detection**: Goes beyond similarity to detect when two notes have opposite stances on the same topic — a non-obvious insight that most note-taking tools miss.

5. **Complete script example**: 50-line bash pseudocode showing the full pipeline with all 8 processing steps.

### Patterns Worth Stealing

- **User-facing output sample**: Shows exactly what the user receives (report with relations, emojis, links)
- **Bilingual triggers**: Chinese + English natural language + command triggers
- **Stance detection logic**: Same topic + high similarity + opposite stance = "contradicts" relation
- **PKM Core dependency list**: 6 specific modules with their roles
- **Benefits of integration section**: Explains why using PKM Core is better than custom code

### Key Lesson

The best PKM skills go beyond CRUD — they discover relationships and surface non-obvious connections between pieces of knowledge.

---

## Cross-Cutting Patterns

These patterns appear in 3+ golden examples:

| Pattern | Where Used | Why It Matters |
|---------|-----------|----------------|
| Real examples/dialogues | All 5 | Users and agents can see exactly what to expect |
| PKM Core integration | 4/5 | Reuse beats reimplementation |
| 5-Type relations | 4/5 | Rich semantics > flat tags |
| Dual audience (user + agent) | 3/5 | Skills are building blocks, not islands |
| Pseudocode/script examples | 4/5 | Implementation clarity without source code bloat |
| Explicit dependency list | 3/5 | Callers know what's required |
| Bilingual triggers (EN + CN) | 3/5 | Serves the actual user base |
| Decision tables | 3/5 | Converts ambiguity into discrete actions |
| Version comparison (v1 → v2) | 2/5 | Documents design evolution |

---

## External Golden Examples (Thariq, Anthropic — March 2026)

From [Thariq's "Lessons from Building Claude Code: How We Use Skills"](https://www.anthropic.com/engineering/claude-code-skills) (2026-03-17). These illustrate skill categories not fully covered by the OpenClaw examples above.

### frontend-design

**Category**: Design / Anti-Pattern Enforcement  
**Pattern**: Reviewer + Tool Wrapper

A skill that prevents Claude from generating the same generic AI-designed UI every time. Instead of telling Claude what good design looks like (which it already knows), the skill catalogs what *bad* AI design looks like — specifically:
- Never use Inter as the default font
- Never use purple gradients or the Tailwind default blue (#3B82F6)
- Never use Heroicons or Lucide icons with no variation
- Never center everything with `max-w-7xl mx-auto`
- Never use the same card-with-shadow layout for every section

**Key insight**: Negative examples ("don't do X") are often more effective than positive guidance ("do Y") because Claude already knows good design — it just defaults to safe, generic patterns under uncertainty. The skill acts as a constraint set, not a design teacher.

### signup-flow-driver

**Category**: Product Validation / Testing  
**Pattern**: Inversion + Pipeline

A skill that automates end-to-end testing of a signup flow by driving a real browser through the complete user journey:
1. Navigate to signup page
2. Fill form with test data (including edge-case inputs)
3. Submit and verify email confirmation
4. Check onboarding completion
5. Report success/failure at each step

**Key insight**: This skill encodes a product team's QA checklist into an automated workflow. It's not a test framework — it's a *methodology* for validating that a critical user flow works. The skill knows what to check at each step because it was built from the team's real post-launch incident history.

### standup-post

**Category**: Business Process Automation  
**Pattern**: Generator

A skill that reads yesterday's completed work (from git commits, Jira tickets, and conversation history) and generates a daily standup post in the team's preferred format. Key features:
- Sources data from multiple tools (not just one)
- Formats output to match the team's template (not a generic summary)
- Handles partial days (WFH, PTO, half-days)
- Posts automatically to the right channel

**Key insight**: The value isn't in generating text — it's in knowing *where to look* for yesterday's work and *how to format* it for this specific team. The skill is a thin wrapper around data collection + formatting, but those two things alone save 15 minutes every morning.

### Common Thread Across These Examples

1. **Negative constraints beat positive guidance**: frontend-design tells Claude what NOT to do, not what to do
2. **Domain expertise is non-transferable**: Each skill encodes knowledge that Claude doesn't have by default
3. **The skill is the methodology, not the automation**: The scripts are simple; the value is in knowing what to check and when
4. **Gotchas are the highest-value content**: Each of these skills contains hard-won lessons from real failures

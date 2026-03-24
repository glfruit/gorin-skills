# Google ADK Design Patterns

> Source: [Google Cloud Tech - 5 Agent Skill design patterns every ADK developer should know](https://x.com/GoogleCloudTech/status/2033953579824758855)  
> Authors: Shubham Saboo, Lavinigam  
> Date: March 2026

---

## Overview

Google's Agent Development Kit (ADK) team identified 5 recurring design patterns across the agent skill ecosystem. These patterns solve the content design problem — not how to package a skill (the format), but how to structure the logic inside it.

> "The specification explains how to package a skill, but offers zero guidance on how to structure the logic inside it."

---

## The 5 Patterns

### 1. Tool Wrapper

**Core idea**: Give your agent on-demand context for a specific library or technology.

**Problem it solves**: Instead of hardcoding API conventions into your system prompt (where they consume context tokens even when not needed), you package them into a skill that loads only when the agent actually works with that technology.

**Mechanism**:
- SKILL.md listens for specific library keywords in the user's prompt
- Dynamically loads internal documentation from `references/` directory
- Applies those rules as absolute truth

**Best for**:
- Distributing team coding guidelines
- Framework-specific best practices
- API conventions and standards

**Key instruction pattern**:
```markdown
Load 'references/conventions.md' for the complete list of {technology} best practices.
```

**Composition**: Can include a Reviewer step at the end to validate output against conventions.

---

### 2. Generator

**Core idea**: Enforce consistent output structure through a fill-in-the-blank process.

**Problem it solves**: Agents tend to generate different document structures on every run. The Generator solves this by orchestrating a template-based workflow.

**Mechanism**:
- `assets/` holds the output template
- `references/` holds the style guide
- SKILL.md acts as project manager: load template → read style guide → collect variables → populate document

**Best for**:
- API documentation generation
- Standardized commit messages
- Project architecture scaffolding
- Any output requiring consistent structure

**Key instruction pattern**:
```markdown
Step 1: Load 'assets/{template}.md' for the required output structure.
Step 2: Load 'references/{style-guide}.md' for tone and formatting rules.
Step 3: Ask the user for any missing information needed to fill the template.
Step 4: Fill the template following the style guide rules.
```

**Composition**: Can use Inversion at the start to gather template variables.

---

### 3. Reviewer

**Core idea**: Separate what to check from how to check it.

**Problem it solves**: Long system prompts detailing every code smell are hard to maintain. The Reviewer pattern stores a modular rubric in `references/` and methodically scores submissions.

**Mechanism**:
- Rubric/checklist stored in `references/review-checklist.md`
- Agent loads checklist and applies each rule systematically
- Findings grouped by severity (error/warning/info)
- Each violation includes: line number, severity, explanation (why not just what), specific fix

**Best for**:
- Code review automation
- Security audits (OWASP, etc.)
- Documentation quality checks
- PR review assistance

**Key instruction pattern**:
```markdown
Step 1: Load 'references/review-checklist.md' for the complete review criteria.
Step 2: Apply each rule from the checklist to the input.
Step 3: For every violation found:
  - Note the line number
  - Classify severity: error (must fix), warning (should fix), info (consider)
  - Explain WHY it's a problem
  - Suggest a specific fix with corrected code
```

**Composition**: Can be a step in a Pipeline, or used standalone.

---

### 4. Inversion

**Core idea**: Flip the dynamic — the agent interviews the user before acting.

**Problem it solves**: Agents inherently want to guess and generate immediately. Inversion forces structured context gathering first.

**Mechanism**:
- Explicit gating instructions prevent premature synthesis (e.g., "DO NOT start building until all phases are complete")
- Structured questions asked sequentially
- Agent waits for answers before moving to next phase
- Final synthesis only after complete picture gathered

**Best for**:
- Requirements gathering
- Project planning
- System design
- Any task where premature execution leads to poor results

**Key instruction pattern**:
```markdown
You are conducting a structured requirements interview. 
DO NOT start building or designing until all phases are complete.

## Phase 1 — {Topic}
(ask one question at a time, wait for each answer)

Ask these questions in order. Do not skip any.
- Q1: "..."
- Q2: "..."

## Phase 2 — {Next Topic}
(only after Phase 1 is fully answered)
...

## Phase 3 — Synthesis
(only after all questions are answered)
...
```

**Composition**: Output feeds into Generator (variables) or Pipeline (workflow).

---

### 5. Pipeline

**Core idea**: Enforce strict sequential workflow with hard checkpoints.

**Problem it solves**: For complex tasks, you cannot afford skipped steps or ignored instructions.

**Mechanism**:
- Instructions serve as workflow definition
- Explicit diamond gate conditions (user approval required before proceeding)
- Different reference files/templates loaded only at specific steps
- Context window stays clean (only relevant context loaded at each step)

**Best for**:
- Multi-stage documentation generation
- Complex data processing workflows
- Anything requiring validation at intermediate stages

**Key instruction pattern**:
```markdown
You are running a {task} pipeline. 
Execute each step in order. Do NOT skip steps or proceed if a step fails.

## Step 1 — {Action}
...
Ask: "..."

## Step 2 — {Next Action}
...
Do NOT proceed to Step 3 until the user confirms.

## Step 3 — {Final Action}
...
```

**Composition**: Can include Reviewer as final step for quality assurance.

---

## Pattern Selection Decision Tree

```
Does the skill teach the agent about a specific library/technology?
  └─ YES → Tool Wrapper
  
Does it need to produce consistent structured output?
  └─ YES → Generator
  
Does it analyze input against quality criteria?
  └─ YES → Reviewer
  
Does it need to gather requirements before acting?
  └─ YES → Inversion
  
Does it involve multiple sequential steps with validation?
  └─ YES → Pipeline
```

---

## Pattern Composition Examples

| Primary Pattern | Secondary Pattern | Use Case |
|----------------|-------------------|----------|
| Pipeline | + Reviewer | Documentation pipeline with final quality check |
| Generator | + Inversion | Report generator that first interviews user for variables |
| Tool Wrapper | + Reviewer | FastAPI expert that reviews code against conventions |
| Inversion | + Generator | Project planner that gathers requirements then generates plan |
| Pipeline | + Tool Wrapper | Multi-step workflow where each step loads specific expertise |

---

## Implementation Checklist

When implementing any of these patterns:

- [ ] Pattern is explicitly declared in SKILL.md metadata
- [ ] Loading instructions specify exact paths in `references/` or `assets/`
- [ ] For Reviewer: severity classification scheme is defined
- [ ] For Inversion: gating instructions are explicit and non-negotiable
- [ ] For Pipeline: gate conditions are clear (user approval, validation, etc.)
- [ ] Pattern composition is documented if multiple patterns used
- [ ] Output structure is specified for Generator and Reviewer patterns

---

## Key Takeaways

1. **Format is solved**: With 30+ agent tools standardizing on SKILL.md layout, formatting is no longer the challenge.

2. **Content design matters**: The same SKILL.md structure can produce wildly different behaviors depending on internal logic structure.

3. **Patterns compose**: These aren't mutually exclusive categories. A Pipeline can include a Reviewer step; a Generator can use Inversion for variable gathering.

4. **Progressive disclosure**: All patterns leverage the optional `references/` and `assets/` directories to keep SKILL.md lean while providing rich context when needed.

5. **Explicit gating**: The most effective pattern implementations use explicit "DO NOT proceed until..." instructions to prevent premature execution.

---
name: {REPLACE: lowercase-hyphen-numbers-only, e.g. "my-cool-skill"}
description: "{REPLACE: 50+ characters. Include domain keywords that help trigger matching. Be specific about what it does, not just the category. Include at least one explicit negative trigger such as 'Don't use it for ...'.}"
triggers: ["{REPLACE: natural language phrases users would say}", "{REPLACE: command-style triggers}", "{REPLACE: Chinese variants if bilingual}"]
user-invocable: {REPLACE: true or false}
agent-usable: {REPLACE: true or false}
---

# {REPLACE: Skill Title}

{REPLACE: 1-2 sentence overview. What does this skill do and why does it exist? Reference the core methodology or framework it's based on.}

**Token-cost rule**: Every section in this skill must justify its context cost. Remove generic advice Claude already knows.

## When to Use

{REPLACE: 3-5 bullet points describing specific scenarios where this skill applies.}

## When NOT to Use

{REPLACE: 2-3 bullet points. What looks like a use case but isn't? What should the user do instead? Make negative triggers explicit.}

## Design Pattern (Choose One)

This skill follows the **{REPLACE: Tool Wrapper / Generator / Reviewer / Inversion / Pipeline}** pattern:

{REPLACE: Describe which of the 5 patterns this skill uses and why it's the right fit. See references/google-adk-patterns.md for pattern descriptions.}

### Pattern-Specific Structure

{REPLACE: Based on chosen pattern, include the relevant structure below:}

**If Tool Wrapper:**
- Library/technology keywords that trigger loading
- Path to conventions document in `references/`
- Rules for applying conventions when reviewing vs writing

**If Generator:**
- Path to output template in `assets/`
- Path to style guide in `references/`
- Required variables to collect from user
- Steps for filling the template

**If Reviewer:**
- Path to review checklist/rubric in `references/`
- Severity classification scheme (error/warning/info)
- Output structure (line numbers, explanations, fixes)
- Review protocol steps

**If Inversion:**
- Phased question sequence
- Explicit gating instructions (e.g., "DO NOT proceed until...")
- What to synthesize after all answers collected
- Template for final output

**If Pipeline:**
- Numbered steps with hard checkpoints
- Gate conditions for proceeding (user approval, validation)
- What to load at each step from `references/` or `assets/`
- Failure handling for each step

## Core Workflow

1. {REPLACE: First concrete step in the workflow}
2. {REPLACE: Second concrete step in the workflow}
3. {REPLACE: Third concrete step or validation step in the workflow}

{REPLACE: Add decision branches, tables, or supporting notes only if they are truly needed.}

## Quick Reference

{REPLACE: A condensed lookup table, cheat sheet, or command reference for experienced users who already know the workflow. Format as a table or bulleted list.}

## Common Mistakes

{REPLACE: 3-5 failure patterns specific to this domain. Use before/after format:}

| Mistake | Why It Fails | Better Approach |
|---------|-------------|-----------------|
| {REPLACE} | {REPLACE} | {REPLACE} |

## Error Handling

### Missing Prerequisites
{REPLACE: What should happen if files, tools, credentials, or environment variables are missing?}

### Unsupported Input or Configuration
{REPLACE: What project variants, edge cases, or configurations are not supported?}

### Script or Tool Failure
{REPLACE: What should the agent do if a deterministic script or command fails?}

### Ambiguous State
{REPLACE: When must the agent stop instead of guessing?}

### Partial Success
{REPLACE: How should the agent report partial completion or manual follow-up?}

## Gotchas

{REPLACE: Mandatory. List concrete failure points, edge cases, and mistakes that agents commonly make when using this skill. Update this section every time a new failure is discovered. Format as bullets or a table.}

{REPLACE: Examples of good gotchas:}
- {REPLACE: "Always run X before Y — running Y first silently produces wrong output"}
- {REPLACE: "The API returns 200 on validation errors — check the response body, not just the status code"}
- {REPLACE: "File paths with spaces break the script unless wrapped in quotes"}

## Hooks (Optional)

{REPLACE: If this skill needs runtime safeguards, document on-demand hooks here. Hooks activate when the skill is invoked and auto-expire when the session ends.}

{REPLACE: Example hooks:}
- `/careful` — {REPLACE: describe what this hook blocks and how to confirm}
- `/freeze` — {REPLACE: describe the allowed write scope}

## Data Persistence (Optional)

{REPLACE: If the skill maintains state across invocations, document it here.}

- **Storage path**: {REPLACE: Use stable paths outside this skill directory, e.g., `~/.openclaw/workspace-{name}/data/{skill-name}/`}
- **Format**: {REPLACE: append-only log / JSON / SQLite — choose based on access patterns}
- **Schema**: {REPLACE: Describe the data structure}
- **Migration**: {REPLACE: How to handle schema changes between versions}

{REPLACE: Note: The skill directory itself may be overwritten during upgrades. Never store persistent data inside it.}

## Internal Acceptance

{REPLACE: Mandatory. Define one real happy-path acceptance case that the agent must run before reporting completion to the user.}

- **Happy-path input**: {REPLACE: concrete user input or invocation example}
- **Invocation method**: {REPLACE: direct skill call / upstream caller / command path}
- **Expected artifacts**: {REPLACE: concrete files, API side effects, or outputs that must exist}
- **Success criteria**: {REPLACE: how the agent knows the path really worked}
- **Fallback / blocker behavior**: {REPLACE: what to report if external deps, auth, or tools block the run}
- **Integration point**: {REPLACE: if the skill claims to be complete, name the upstream workflow/caller that must invoke it before readiness can be called integrated}

## Delivery Contract

- Internal readiness may move through `scaffold`, `mvp`, `production-ready`, and `integrated`.
- These are **internal** states only.
- Do **not** report "skill creation complete" to the user unless internal readiness has reached **`integrated`**.
- If internal acceptance or integration proof is missing, report `failed` or `blocked` instead of claiming completion.

## Resources

{REPLACE: Links to references/, scripts/, assets/, external documentation. Only include resources that actually exist.}

## Origin Metadata

When a skill is created by gorin (self), place a `.skill-meta.json` file in the skill root:

```json
{
  "origin": "self",
  "author": "gorin"
}
```

For third-party or ClawHub-installed skills:

```json
{
  "origin": "third-party",
  "author": "external"
}
```

This file is read by `skill-repo-sync.py` to classify skills. It travels with the skill in git and is the canonical source of origin truth.

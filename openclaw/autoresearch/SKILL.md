---
name: autoresearch
description: "Autonomously optimize any OpenClaw skill via repeated sub-agent runs, binary eval scoring, prompt mutation, and improvement retention. Based on Karpathy's autoresearch. Don't use for one-off skill edits, creating new skills, or optimizing non-skill configs."
triggers:
  - "optimize this skill"
  - "improve this skill"
  - "run autoresearch on"
  - "self-improve skill"
  - "eval my skill"
  - "benchmark skill"
  - "autoresearch"
  - "自动优化这个skill"
  - "跑autoresearch"
  - "评估skill"
user-invocable: true
agent-usable: false
---

# Autoresearch for Skills

Most skills work ~70% of the time. The fix isn't rewriting from scratch — it's running an autonomous loop that tests, scores, mutates the prompt, and keeps what works.

Adapts Karpathy's autoresearch methodology to OpenClaw skills. Instead of optimizing ML training code, we optimize SKILL.md prompts via binary evals.

## Design Pattern

**Pipeline** pattern — strict multi-step workflow with autonomous loop and checkpoint gates.

The pipeline: gather context → baseline → experiment loop → deliver results. Each step has explicit exit conditions.

## When to Use

- An existing skill produces inconsistent output (sometimes great, sometimes garbage)
- You want to objectively measure skill quality with repeatable evals
- You have a specific "what does good look like" definition (binary yes/no checks)
- You want the skill to improve itself while you do something else

## When NOT to Use

- One-off skill edits (just edit the SKILL.md directly)
- Creating new skills from scratch (use `enhanced-skill-creator`)
- Optimizing non-skill things (prompts, system configs, code quality)
- The skill already passes 90%+ on subjective quality (diminishing returns)
- You can't define clear binary eval criteria (evals must be yes/no, not vibes)

## Core Workflow

### Phase 0: Gather Context (blocking gate — do not proceed without user confirmation)

Ask the user for these **before running anything**:

| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| Target skill path | Yes | — | Exact path to SKILL.md |
| Test inputs (3-5) | Yes | — | Prompts that exercise the skill; variety prevents overfitting |
| Eval criteria (3-6) | Yes | — | Binary yes/no checks; see `references/eval-guide.md` |
| Runs per experiment | No | 5 | More = reliable but slower. 5 is the sweet spot. |
| Budget cap | No | ∞ | Max experiment cycles. Stop early if you must. |
| Output directory | No | `~/.openclaw/workspace/autoresearch/{name}/` | Where results go |

**Do NOT skip this phase.** Do NOT guess test inputs or eval criteria.

### Phase 1: Understand the Skill

1. Read the full SKILL.md
2. Read any linked `references/`, `scripts/`, `assets/`
3. Identify: core job, process steps, output contract, existing quality checks
4. Note anti-patterns and gotchas already present

Output: a short internal summary of what the skill does and what its current instructions look like.

### Phase 2: Build the Eval Suite

Convert user criteria into structured evals. **Every check must be binary.**

Format:
```
EVAL [N]: [Short name]
Question: [Yes/no question about the output]
Pass: [What "yes" looks like — one specific sentence]
Fail: [What triggers "no" — one specific sentence]
```

Rules:
- **Binary only.** No scales, no "rate 1-7", no vibes.
- **Specific enough to be consistent** across multiple runs.
- **Not so narrow** that the skill games the eval instead of improving.
- **3-6 evals.** More than 6 → skill parrots eval criteria instead of actually getting better.
- **No overlap** between evals (each must test something distinct).

Max score: `number_of_evals × runs_per_experiment`

See `references/eval-guide.md` for detailed examples per skill type.

### Phase 3: Establish Baseline (experiment #0)

1. Create output directory: `autoresearch-{name}/`
2. Back up original SKILL.md as `autoresearch-{name}/SKILL.md.baseline`
3. Run the skill **N times** using test inputs via `sessions_spawn` (isolated sub-agent)
4. Score every output against every eval
5. Record baseline in `autoresearch-{name}/results.json`
6. **Confirm baseline score with user** before proceeding
7. Generate `dashboard.html` and open it in browser

If baseline ≥ 90%, warn user — the skill may not need optimization.

**How to run a skill for eval:** Spawn an isolated sub-agent with the test input as the task, including the skill's SKILL.md content in the system prompt or workspace context. Capture the output and score it.

### Phase 4: Experiment Loop (autonomous — do not pause to ask)

Run this loop until stopped, budget exhausted, or ceiling hit (95%+ for 3 consecutive rounds).

**Each iteration:**

1. **Analyze failures** — Which evals fail most? Read actual failing outputs. Identify the pattern.
2. **Form one hypothesis** — Pick ONE thing to change.
   - Good: add specific instruction, reword ambiguity, add anti-pattern, add worked example, remove redundant instruction
   - Bad: rewrite entire skill, add 10 rules at once, "make it better"
3. **Mutate** SKILL.md with ONE targeted change
4. **Test** — Run skill N times with same test inputs (spawned sub-agents)
5. **Score** — Every output through every eval
6. **Decide:**
   - Score improved → **KEEP** (this is the new baseline)
   - Same or worse → **DISCARD** (revert SKILL.md to last kept version)
7. **Log** result to results.json and changelog.md
8. **Repeat**

**If stuck (3+ consecutive discards):**
- Re-read all failing outputs looking for deeper patterns
- Try removing instructions instead of adding
- Try combining two previous near-miss mutations
- Try a completely different approach to the same problem

### Phase 5: Deliver Results

When the loop stops, present:

1. **Score trajectory**: baseline → final (percent improvement)
2. **Experiment stats**: total tried, kept, discarded, keep rate
3. **Top changes** that helped most (from changelog)
4. **Remaining failure patterns** (what still goes wrong)
5. **Files produced**: improved SKILL.md (in place), results.json, changelog.md, SKILL.md.baseline

## Output Structure

```
autoresearch-{name}/
├── dashboard.html       # Live browser dashboard (auto-refreshes from results.json)
├── results.json         # Score data powering dashboard
├── changelog.md         # Every mutation tried, kept or discarded, with reasoning
└── SKILL.md.baseline    # Original skill before optimization
```

### results.json format

```json
{
  "skill_name": "web-reader",
  "skill_path": "~/.openclaw/skills/web-reader/SKILL.md",
  "status": "complete",
  "config": {
    "evals_count": 4,
    "runs_per_experiment": 5,
    "budget_cap": null
  },
  "baseline": { "score": 14, "max_score": 20, "pass_rate": 70.0 },
  "best": { "score": 19, "max_score": 20, "pass_rate": 95.0 },
  "experiments": [
    {
      "id": 0,
      "score": 14,
      "max_score": 20,
      "pass_rate": 70.0,
      "status": "baseline",
      "description": "original skill — no changes",
      "kept": true
    }
  ],
  "eval_breakdown": [
    { "name": "Content extraction", "pass_count": 8, "total": 10 }
  ]
}
```

### changelog.md format

```markdown
## Experiment 1 — KEEP
**Score:** 16/20 (80%) ↑ from 14/20
**Change:** Added explicit instruction to preserve markdown links in extraction
**Reasoning:** 3/5 baseline outputs had stripped links, causing content loss
**Result:** Link preservation eval improved from 2/5 to 5/5
```

## Running Skills for Eval

The key challenge: how to execute a skill in isolation and capture its output.

**Approach for OpenClaw:**

1. Read the target SKILL.md content
2. Spawn an isolated sub-agent via `sessions_spawn` with:
   - The SKILL.md content prepended to the task prompt as context
   - The test input as the main task
   - A directive to output ONLY the skill's result (no meta-commentary)
3. Capture the sub-agent's output text
4. Score it against the eval criteria

For skills that call external tools (scripts, CLI commands), the sub-agent will have access to the same tooling. Ensure test inputs don't have destructive side effects.

## Quick Reference

| Step | Action | Output |
|------|--------|--------|
| Phase 0 | Ask user for skill path, test inputs, evals | Confirmed config |
| Phase 1 | Read and understand target skill | Internal summary |
| Phase 2 | Write 3-6 binary evals | Eval suite |
| Phase 3 | Baseline run (N × evals) | Baseline score |
| Phase 4 | Loop: mutate → test → score → keep/discard | Improved SKILL.md |
| Phase 5 | Summarize results | Report + files |

## Common Mistakes

| Mistake | Why It Fails | Better Approach |
|---------|-------------|-----------------|
| Changing 5 things per experiment | Can't tell what helped | ONE mutation per round |
| Using "rate 1-10" evals | Unreliable across runs | Binary yes/no only |
| Using identical test inputs | Overfits to one scenario | 3-5 diverse inputs |
| More than 6 evals | Skill games the checklist | 3-6 focused checks |
| Stopping to ask between rounds | User might be away | Run autonomously until done |
| Ignoring baseline | No way to measure improvement | Always baseline first |
| Skipping changelog | Lost knowledge when model changes | Log every experiment |

## Error Handling

- **Sub-agent spawn fails**: Retry once, then skip that test input and note it in changelog
- **Skill execution errors**: Count as a failure on ALL evals for that run (the skill broke)
- **Ambiguous eval scoring**: If the scorer can't confidently say yes/no, score it as fail (conservative)
- **SKILL.md revert fails**: This is critical — before every mutation, save a copy. If revert fails, restore from the copy
- **Dashboard can't render**: results.json is the source of truth; dashboard is a convenience view

## Gotchas

- **The skill can improve at passing evals without actually improving.** If outputs technically pass but feel worse, the evals are bad — not the skill. Rewrite the evals.
- **More evals ≠ better signal.** Each additional eval dilutes the signal from the ones that matter. 3 strong evals beat 8 mediocre ones.
- **Sub-agent output includes meta-commentary.** Always instruct sub-agents to output ONLY the skill result. Strip any "Here is your output:" prefixes before scoring.
- **Mutation side effects.** A mutation that fixes eval 1 might break eval 3. This is why you score ALL evals per experiment, not just the one you're targeting.
- **Diminishing returns are real.** Going from 70% → 90% is usually fast. 90% → 95% takes much longer. 95% → 100% may be impossible without overfitting. Stop at 95%.
- **Changelog is the most valuable artifact.** Future models (or smarter models) can pick up where this run left off. Don't skip it.

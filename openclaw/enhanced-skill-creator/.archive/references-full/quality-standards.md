# Quality Standards

Scoring rubric for evaluating skill quality. 6 dimensions, 120 points total. Use this to assess a generated skill before finalizing.

---

## Scoring Dimensions

### 1. Structural Completeness (20 points)

Objective checks — can be automated with `scripts/validate-skill.sh`.

| Criterion | Points | Requirement |
|-----------|--------:|-------------|
| SKILL.md exists | 3 | File present at skill root |
| Valid YAML frontmatter | 3 | `name` and `description` fields present and non-empty |
| Name format | 2 | lowercase-hyphen-numbers only |
| Description quality | 2 | 50+ characters with domain keywords |
| Core sections | 4 | At least 2 of: Overview, When to Use, Core Workflow, Quick Reference |
| No forbidden files | 2 | No root README.md, INSTALL.md |
| Size constraint | 2 | SKILL.md under 500 lines |
| Script standards | 2 | `.sh` files have shebang, are executable |

### 2. Content Authenticity (30 points)

The most important dimension. Evaluates whether content is real or fabricated.

| Criterion | Points | How to Assess |
|-----------|--------:|---------------|
| No placeholder text | 6 | Search for "Step one", "TODO", "placeholder", "example.com", "lorem" |
| Real examples | 8 | Examples reference actual tools, techniques, or sources — not invented scenarios |
| Domain vocabulary | 6 | Uses terminology that practitioners in this field would recognize |
| Named methodologies | 5 | References specific frameworks, books, or experts (not "best practices say...") |
| Cited sources | 5 | Research can be traced to real origins (URLs, book titles, project names) |

### 3. Methodology Depth (25 points)

Evaluates the quality of the research and pattern extraction.

| Criterion | Points | How to Assess |
|-----------|--------:|---------------|
| 3+ golden cases | 5 | Research references at least 3 distinct, real examples |
| Non-obvious insights | 6 | Contains knowledge a novice would miss — not just "do it well" |
| Before/after comparisons | 5 | Shows concrete transformation from naive to expert approach |
| Failure modes documented | 5 | "When NOT to Use" and "Common Mistakes" with specific scenarios |
| Theory justified by practice | 4 | Any theoretical framework is connected to a real case, not abstract |

### 4. Practical Usability (25 points)

Can an agent (or user) follow this skill and produce real output?

| Criterion | Points | How to Assess |
|-----------|--------:|---------------|
| Actionable steps | 7 | Each workflow step specifies what to do, not just what to think about |
| Clear decision points | 5 | When choices arise, the skill provides criteria for choosing |
| Output format specified | 5 | The expected output structure is documented (not "generate a report") |
| Integration documented | 4 | How to call this skill and how it calls other skills is clear |
| Quick reference available | 4 | Experienced users have a condensed lookup without re-reading the full doc |

### 5. Readiness Honesty (10 points)

Evaluates whether the claimed maturity of the skill matches the actual implementation and validation evidence.

| Criterion | Points | How to Assess |
|-----------|--------:|---------------|
| Readiness level is explicit | 2 | Skill is clearly treated as scaffold / mvp / production-ready / integrated |
| Happy-path evidence exists | 3 | At least one real invocation produced a real artifact |
| Doc/implementation consistency | 2 | Docs do not claim working features that are still stubbed |
| Acceptance contract exists | 2 | Output rules and success criteria are documented |
| Integrated evidence when claimed | 1 | If described as integrated, there is at least one real upstream invocation |

### 6. Context Budget (10 points)

Evaluates whether the skill is token-efficient. Run `scripts/context_sizer.py <skill-dir>` to measure.

| Criterion | Points | How to Assess |
|-----------|--------:|---------------|
| Within total budget (8k tokens) | 3 | `context_sizer.py` reports within budget |
| SKILL.md within budget (2k tokens) | 3 | Core file is lean, details deferred to references/ |
| Quality density ≥ 0.6 | 2 | Not padded with filler, whitespace, or boilerplate |
| Progressive disclosure used | 2 | Dense content moved to references/ or loaded on demand |

---

## Grade Scale

| Score | Grade | Meaning |
|-------|-------|---------|
| 108-120 | A | Production-ready, could serve as a golden example |
| 96-107 | B | Good quality, minor improvements possible |
| 84-95 | C | Functional but missing depth — needs more research |
| 72-83 | D | Significant gaps — revisit Steps 2-3 |
| Below 72 | F | Not ready — restart from Step 1 |

**Minimum passing score**: 84 (Grade C)
**Target score for new skills**: 96+ (Grade B)

---

## Quick Assessment Protocol

For a rapid quality check without full scoring:

1. **30-second test**: Read only the SKILL.md frontmatter and first 20 lines. Can you tell exactly what this skill does and when to use it? If not → likely fails Content Authenticity.

2. **Domain expert test**: Show the Core Workflow section to someone who knows the domain. Would they say "yes, that's how experts do it" or "that's too generic"? If generic → fails Methodology Depth.

3. **Agent execution test**: Give the SKILL.md to Claude without additional context. Can Claude produce a real, useful output by following the instructions? If Claude produces template-like output → fails Practical Usability.

4. **Structural scan**: Run `bash scripts/validate-skill.sh <skill-dir>`. All checks pass? If not → fails Structural Completeness.

5. **Budget scan**: Run `python3 scripts/context_sizer.py <skill-dir>`. Within budget? If not → fails Context Budget.

---

## Dimension Weights Rationale

- **Content Authenticity (30/120 = 25%)** remains critical because placeholder content is the #1 failure mode.
- **Methodology Depth (25/120 = 21%)** and **Practical Usability (25/120 = 21%)** are core quality measures.
- **Structural Completeness (20/120 = 17%)** is weighted lower because it's the easiest to fix.
- **Readiness Honesty (10/120 = 8%)** prevents maturity overclaiming.
- **Context Budget (10/120 = 8%)** ensures token efficiency — important but secondary to content quality.

# Quality Standards

Scoring rubric for evaluating skill quality. 4 dimensions, 100 points total. Use this to assess a generated skill before finalizing.

---

## Scoring Dimensions

### 1. Structural Completeness (20 points)

Objective checks — can be automated with `scripts/validate-skill.sh`.

| Criterion | Points | Requirement |
|-----------|--------|-------------|
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
|-----------|--------|---------------|
| No placeholder text | 6 | Search for "Step one", "TODO", "placeholder", "example.com", "lorem" |
| Real examples | 8 | Examples reference actual tools, techniques, or sources — not invented scenarios |
| Domain vocabulary | 6 | Uses terminology that practitioners in this field would recognize |
| Named methodologies | 5 | References specific frameworks, books, or experts (not "best practices say...") |
| Cited sources | 5 | Research can be traced to real origins (URLs, book titles, project names) |

### 3. Methodology Depth (25 points)

Evaluates the quality of the research and pattern extraction.

| Criterion | Points | How to Assess |
|-----------|--------|---------------|
| 3+ golden cases | 5 | Research references at least 3 distinct, real examples |
| Non-obvious insights | 6 | Contains knowledge a novice would miss — not just "do it well" |
| Before/after comparisons | 5 | Shows concrete transformation from naive to expert approach |
| Failure modes documented | 5 | "When NOT to Use" and "Common Mistakes" with specific scenarios |
| Theory justified by practice | 4 | Any theoretical framework is connected to a real case, not abstract |

### 4. Practical Usability (25 points)

Can an agent (or user) follow this skill and produce real output?

| Criterion | Points | How to Assess |
|-----------|--------|---------------|
| Actionable steps | 7 | Each workflow step specifies what to do, not just what to think about |
| Clear decision points | 5 | When choices arise, the skill provides criteria for choosing |
| Output format specified | 5 | The expected output structure is documented (not "generate a report") |
| Integration documented | 4 | How to call this skill and how it calls other skills is clear |
| Quick reference available | 4 | Experienced users have a condensed lookup without re-reading the full doc |

### 5. Readiness Honesty (20 points)

Evaluates whether the claimed maturity of the skill matches the actual implementation and validation evidence.

| Criterion | Points | How to Assess |
|-----------|--------|---------------|
| Readiness level is explicit | 4 | Skill is clearly treated as scaffold / mvp / production-ready / integrated |
| Happy-path evidence exists | 5 | At least one real invocation produced a real artifact |
| Doc/implementation consistency | 4 | Docs do not claim working features that are still stubbed |
| Acceptance contract exists | 4 | Output rules and success criteria are documented |
| Integrated evidence when claimed | 3 | If described as integrated, there is at least one real upstream invocation |

---

## Grade Scale

| Score | Grade | Meaning |
|-------|-------|---------|
| 90-100 | A | Production-ready, could serve as a golden example |
| 80-89 | B | Good quality, minor improvements possible |
| 70-79 | C | Functional but missing depth — needs more research |
| 60-69 | D | Significant gaps — revisit Steps 2-3 |
| Below 60 | F | Not ready — restart from Step 1 |

**Minimum passing score**: 75 (Grade C)
**Target score for new skills**: 85+ (Grade B)

---

## Quick Assessment Protocol

For a rapid quality check without full scoring:

1. **30-second test**: Read only the SKILL.md frontmatter and first 20 lines. Can you tell exactly what this skill does and when to use it? If not → likely fails Content Authenticity.

2. **Domain expert test**: Show the Core Workflow section to someone who knows the domain. Would they say "yes, that's how experts do it" or "that's too generic"? If generic → fails Methodology Depth.

3. **Agent execution test**: Give the SKILL.md to Claude without additional context. Can Claude produce a real, useful output by following the instructions? If Claude produces template-like output → fails Practical Usability.

4. **Structural scan**: Run `bash scripts/validate-skill.sh <skill-dir>`. All checks pass? If not → fails Structural Completeness.

---

## Dimension Weights Rationale

- **Content Authenticity (30%)** is weighted highest because placeholder content is the #1 failure mode and the hardest to fix retroactively.
- **Methodology Depth (25%)** and **Practical Usability (25%)** remain core because a skill needs both good research and clear instructions.
- **Readiness Honesty (20%)** matters because overclaiming maturity creates workflow breakage later.
- **Structural Completeness (20%)** is weighted lowest because it's the easiest to fix — it's just format compliance.

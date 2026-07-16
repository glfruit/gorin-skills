# Failure Patterns (Top 10)

Full list with evidence in `.archive/references-full/failure-patterns.md`.

| # | Pattern | Symptom | Fix |
|---|---------|---------|-----|
| 1 | Fake research | Agent fabricates URLs/sources | Require 3+ real golden cases with verifiable URLs |
| 2 | Placeholder content | Sections filled with template text | Cross-check against golden cases; reject if no real content |
| 3 | Overly broad triggers | "make" matches everything | Run detect-overlap.sh; require negative triggers |
| 4 | Token bloat | SKILL.md > 4k tokens | Progressive disclosure → references/ |
| 5 | No error handling | Happy-path only | Generate error handling via scripts/generate-error-handling.sh |
| 6 | Missing gotchas | Skill looks perfect on paper | Mandatory Gotchas section with real failure modes |
| 7 | Template-driven creation | Output is generic boilerplate | Golden-case-first: 3+ real examples before writing |
| 8 | No internal acceptance | "Done" without testing | Mandatory real happy-path execution |
| 9 | Cross-skill overlap | Two skills handle same trigger | detect-overlap.sh in Step 6 |
| 10 | Premature readiness | Labeled "production" without proof | Governance check: evidence required for promotion |

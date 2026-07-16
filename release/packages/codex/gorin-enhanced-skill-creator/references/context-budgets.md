# Context Budgets (Quick Reference)

| Category | Default Budget | Note |
|----------|---------------|------|
| SKILL.md | 2,000 | Core routing + workflow only |
| scripts/ | 0 | Run as subprocess, not loaded |
| references/ | 4,000 | Loaded on demand |
| assets/ | 1,000 | Templates, loaded when needed |
| config/ | 500 | Static configuration |
| evals/ | 500 | Test cases |
| **Total** | **8,000** | Per skill target |

## Quality Density
| Grade | Density |
|-------|---------|
| A | ≥ 0.8 |
| B | 0.6–0.8 |
| C | 0.4–0.6 |
| D | < 0.4 |

Remediation: SKILL.md too large → move to references/. references/ too large → archive to .archive/.

# Skill Taxonomy Reference

## 12 Skill Types

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

## Design Patterns (cross-type)

From [Google Cloud Tech](https://x.com/GoogleCloudTech/status/2033953579824758855):

- **Tool Wrapper**: Dynamic loading of library conventions
- **Generator**: Template + variable filling for consistent output
- **Reviewer**: Checklist-driven analysis with severity levels
- **Inversion**: Agent interviews user before acting
- **Pipeline**: Strict multi-step workflow with checkpoints

Full details with examples: `references/google-adk-patterns.md`

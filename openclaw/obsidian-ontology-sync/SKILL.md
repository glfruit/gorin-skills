---
name: obsidian-ontology-sync
description: Bidirectional sync between Obsidian PKM (human-friendly notes) and structured ontology (machine-queryable graph). Automatically extracts entities and relationships from markdown, maintains ontology graph, and provides feedback to improve note structure. Run sync every few hours via cron.
metadata:
  {
    "tags": ["obsidian", "ontology", "knowledge-graph", "pkm", "automation"],
    "openclaw":
      {
        "requires": { "skills": ["pkm-core", "obsidian-bases", "obsidian-cli"] }
      }
  }
---

# Obsidian-Ontology Sync

**Philosophy:** Obsidian is PRIMARY (human writes natural notes) → Ontology is DERIVED (machine extracts structure) → Feedback loop improves both

## Core Concept

```
Obsidian Notes (Markdown)
    ↓ Extract (every 3 hours)
Ontology Graph (Structured)
    ↓ Query & Analyze
Insights & Suggestions
    ↓ Feedback
Improved Note Templates
```

## When to Use

| Situation | Action |
|-----------|--------|
| After creating/updating contacts | Run sync to extract entities |
| Before business queries | Sync then query ontology |
| Weekly review | Sync + analyze + get suggestions |
| New project setup | Extract entities + suggest structure |
| Team status tracking | Sync daily-status → ontology → analytics |

## What Gets Extracted

Entity types: Person, Organization, Project, Event, Task, Issue.

Relationships: works_at, assigned_to, met_at, for_client, reports_to, has_task, blocks.

Source directories and extraction rules: 详见 `references/extraction-rules.md`

## Sync Process

Three phases: Extract → Analyze → Feedback.

```bash
python3 skills/obsidian-ontology-sync/scripts/sync.py extract   # Phase 1
python3 skills/obsidian-ontology-sync/scripts/sync.py analyze   # Phase 2
python3 skills/obsidian-ontology-sync/scripts/sync.py feedback   # Phase 3
```

详见 `references/sync-process.md`（完整命令、config.yaml 配置、cron 设置）

## Queries

Query the ontology for business insights. 详见 `references/query-examples.md`

## Feedback Loop

The feedback phase generates actionable suggestions: missing info, broken links, relationship insights, template improvements. 详见 `references/feedback-examples.md`

## References

| File | Content |
|------|---------|
| `references/extraction-rules.md` | What gets extracted from each note type, detection rules |
| `references/sync-process.md` | 3-phase sync commands, config.yaml, cron setup |
| `references/query-examples.md` | Ontology query examples |
| `references/feedback-examples.md` | Feedback loop examples |
| `references/operational.md` | File structure, daily workflow, benefits, getting started, troubleshooting |

---

**Author:** Built for team management, contact tracking, and business intelligence at scale
**License:** MIT
**Tags:** obsidian, ontology, knowledge-graph, pkm, automation, sync

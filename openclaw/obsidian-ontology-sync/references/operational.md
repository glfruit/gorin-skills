# Operational Reference

## File Structure After Sync

```
/root/life/pkm/
├── references/
│   ├── contacts/          # Source notes (you write these)
│   ├── clients/           # Source notes
│   └── team/              # Source notes
├── daily-status/          # Source notes
├── projects/              # Source notes
│
├── memory/ontology/       # Generated ontology
│   ├── graph.jsonl        # Entity/relation storage
│   └── schema.yaml        # Type definitions
│
└── ontology-sync/         # Sync outputs
    ├── config.yaml        # Your config
    ├── feedback/
    │   ├── daily-insights.md
    │   ├── weekly-feedback.md
    │   └── suggestions.md
    └── logs/
        └── sync-YYYY-MM-DD.log
```

## Integration with Daily Workflow

### Morning Routine (9 AM)

```bash
# Cron runs analysis
# Generates daily-insights.md with:
- Response rate from yesterday's status requests
- Projects needing attention (blockers mentioned)
- Contacts to follow up (met > 3 days ago, no task)
```

### Weekly Review (Monday 10 AM)

```bash
# Cron generates weekly feedback
# Creates suggestions for:
- Missing information to fill in
- Broken links to fix
- New templates to adopt
- Relationship insights
```

## Benefits

### ✅ For You
1. **Zero Extra Work:** Just keep writing normal Obsidian notes
2. **Automatic Structure:** Ontology extracted automatically
3. **Powerful Queries:** Find patterns across all your data
4. **Quality Improvement:** Feedback loop catches missing info
5. **No Double Entry:** Single source of truth (Obsidian)

### ✅ For Team Management
- Track who's on which project (auto-extracted)
- Monitor response patterns (from daily-status)
- Identify unbalanced workloads
- Find blockers across projects

### ✅ For Sales/BD
- Track contact network (who you met, where, when)
- Follow-up reminders (contacted >7 days ago)
- Relationship mapping (who knows who)
- Pipeline insights (prospects → warm → clients)

### ✅ For Finance
- Project valuations (extracted from client notes)
- Team cost allocation (people → projects → revenue)
- Revenue forecasting (active projects × value)

## Comparison with Alternatives

| Approach | Pros | Cons |
|----------|------|------|
| **Manual ontology** | Full control | Too much work, falls behind |
| **Obsidian only** | Simple | No structured queries |
| **Ontology only** | Powerful queries | Not human-friendly |
| **This skill** | Best of both | Initial setup needed |

## Advanced: Bidirectional Sync

**Future capability:**

Update Obsidian notes FROM ontology insights:

```bash
# Automatically add missing fields
python3 skills/obsidian-ontology-sync/scripts/sync.py apply-feedback

# What it does:
# - Adds missing email field to contact notes
# - Creates suggested project files
# - Links related entities
# - Updates frontmatter
```

**Safety:** Always creates backup before modifying files.

## Getting Started

### 1. Install Dependencies

```bash
clawhub install obsidian  # If not already installed
```

### 2. Create Config

```bash
python3 skills/obsidian-ontology-sync/scripts/init.py

# Creates:
# - config.yaml with your vault path
# - ontology directory structure
# - cron jobs
```

### 3. Run First Sync

```bash
# Manual first sync to test
python3 skills/obsidian-ontology-sync/scripts/sync.py extract --dry-run

# See what would be extracted
# Review, then run for real:
python3 skills/obsidian-ontology-sync/scripts/sync.py extract
```

### 4. Enable Automatic Sync

```bash
python3 skills/obsidian-ontology-sync/scripts/setup-cron.py
```

### 5. Query Your Data

```bash
python3 skills/obsidian-ontology-sync/scripts/query.py "team members on high value projects"
```

## Troubleshooting

### Extraction Issues

```bash
# Dry run to see what would be extracted
python3 skills/obsidian-ontology-sync/scripts/sync.py extract --dry-run --verbose

# Check specific file
python3 skills/obsidian-ontology-sync/scripts/debug.py \
  --file references/contacts/Alice.md
```

### Query Not Finding Data

```bash
# Check what's in ontology
python3 skills/ontology/scripts/ontology.py query --type Person

# Verify sync ran
cat /root/life/pkm/ontology-sync/logs/sync-latest.log
```

### Feedback Not Generated

```bash
# Manually run analysis
python3 skills/obsidian-ontology-sync/scripts/sync.py analyze
python3 skills/obsidian-ontology-sync/scripts/sync.py feedback
```

## Version History

- **1.0.0** (2026-02-27) - Initial version with extraction, analysis, feedback loop

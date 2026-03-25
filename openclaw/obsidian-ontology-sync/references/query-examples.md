# Query Examples Reference

Once synced, you can query:

```bash
# All team members on high-value projects
python3 skills/ontology/scripts/ontology.py query \
  --type Person \
  --where '{"role":"team_member"}' \
  --related assigned_to \
  --filter '{"type":"Project","value__gt":400000}'

# Contacts from specific event not yet followed up
python3 skills/ontology/scripts/ontology.py query \
  --type Person \
  --where '{"met_at":"event_tech_conference_2026"}' \
  --missing has_task

# Team response patterns
python3 skills/ontology/scripts/ontology.py query \
  --type Person \
  --where '{"role":"team_member"}' \
  --aggregate response_pattern

# Projects by client
python3 skills/ontology/scripts/ontology.py query \
  --type Project \
  --group-by for_client \
  --count
```

## On-Demand Queries

```bash
# Before a meeting
"Show me all interactions with Client X"

# Resource planning
"Which team members are on <3 projects?"

# Sales pipeline
"Contacts met at conferences in last 30 days without follow-up"
```

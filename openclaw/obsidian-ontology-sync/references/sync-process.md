# Sync Process Reference

## Phase 1: Extract (Markdown → Ontology)

```bash
# Run extraction
python3 skills/obsidian-ontology-sync/scripts/sync.py extract

# What it does:
# 1. Scan configured Obsidian directories
# 2. Parse markdown frontmatter + content
# 3. Extract entities (Person, Project, Organization, etc.)
# 4. Extract relationships (works_at, assigned_to, etc.)
# 5. Write to ontology using append-only operations

# Dry run to see what would be extracted
python3 skills/obsidian-ontology-sync/scripts/sync.py extract --dry-run --verbose

# Check specific file
python3 skills/obsidian-ontology-sync/scripts/debug.py \
  --file references/contacts/Alice.md
```

## Phase 2: Analyze (Ontology → Insights)

```bash
# Run analytics
python3 skills/obsidian-ontology-sync/scripts/sync.py analyze

# Generates insights like:
# - "3 team members have no assigned projects"
# - "Contact 'John Doe' missing email address"
# - "Project 'X' has 5 people but no client linked"
# - "10 contacts from AI Summit not linked to follow-up tasks"
```

## Phase 3: Feedback (Insights → Improve PKM)

```bash
# Get suggestions
python3 skills/obsidian-ontology-sync/scripts/sync.py feedback

# Creates:
# - Missing property suggestions
# - Broken link reports
# - Relationship suggestions
# - Template improvements
```

**Example Feedback:**

```markdown
# Sync Feedback - 2026-02-27

## Missing Information (10 items)
- [ ] `Alice Johnson` missing phone number
- [ ] `Bob` missing email in team file
- [ ] Project `Project Alpha` missing deadline

## Suggested Links (5 items)
- [ ] Link `Jane Doe` (TechHub) to organization `TechHub`
- [ ] Link `Eve` to project (found in daily-status but not in team file)

## Relationship Insights
- `Project Alpha` team: Alice, Carol, David (extracted from daily-status)
- Suggest updating project file with team assignments

## Template Suggestions
- Add `Projects: [[]]` field to contact template
- Add `Response Pattern:` field to team template
```

## Configuration (config.yaml)

```yaml
# /root/life/pkm/ontology-sync/config.yaml

obsidian:
  vault_path: /root/life/pkm
  
  # What to sync
  sources:
    contacts:
      path: references/contacts
      entity_type: Person
      extract:
        - email_from_content
        - company_from_property
        - projects_from_links
    
    clients:
      path: references/clients
      entity_type: Organization
      extract:
        - contract_value
        - projects
        - contacts
    
    team:
      path: references/team
      entity_type: Person
      role: team_member
      extract:
        - assignments
        - response_patterns
        - reports_to
    
    daily_status:
      path: daily-status
      extract:
        - response_times
        - behavioral_patterns
        - blockers

ontology:
  storage_path: /root/life/pkm/memory/ontology
  format: jsonl  # or sqlite for scale
  
  # Entity types to track
  entities:
    - Person
    - Organization
    - Project
    - Event
    - Task
  
  # Relationships to extract
  relationships:
    - works_at
    - assigned_to
    - met_at
    - for_client
    - reports_to
    - has_task
    - blocks

feedback:
  output_path: /root/life/pkm/ontology-sync/feedback
  generate_reports: true
  suggest_templates: true
  highlight_missing: true

schedule:
  # Run via cron every 3 hours
  sync_interval: "0 */3 * * *"
  analyze_daily: "0 9 * * *"  # 9 AM daily
  feedback_weekly: "0 10 * * MON"  # Monday 10 AM
```

## Cron Integration

```bash
# Add to OpenClaw cron
python3 skills/obsidian-ontology-sync/scripts/setup-cron.py

# Or manually via cron tool
cron add \
  --schedule "0 */3 * * *" \
  --task "python3 skills/obsidian-ontology-sync/scripts/sync.py extract" \
  --label "Obsidian → Ontology Sync"
```

**Cron Jobs Created:**

1. **Every 3 hours:** Extract entities from Obsidian → Update ontology
2. **Daily 9 AM:** Run analytics and generate insights
3. **Weekly Monday 10 AM:** Generate feedback report + template suggestions

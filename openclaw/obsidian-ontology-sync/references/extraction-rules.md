# Extraction Rules Reference

## From Contact Notes (`references/contacts/*.md`)

**Extracts:**
- `Person` entity (name, email, phone)
- `works_at` → `Organization`
- `met_at` → `Event`
- `assigned_to` → `Project` (if mentioned)
- `status` → (prospect, warm_lead, client, etc.)

**Example:**
```markdown
# Alice Johnson

**Email:** alice@company.com
**Company:** Acme Corp
**Met At:** Tech Conference 2026
**Projects:** Project Alpha

## Notes
Great developer, responsive communication.
```

**Becomes:**
```json
{
  "entity": {
    "id": "person_alice_johnson",
    "type": "Person",
    "properties": {
      "name": "Alice Johnson",
      "email": "alice@company.com",
      "notes": "Great developer, responsive communication"
    }
  },
  "relations": [
    {"from": "person_alice_johnson", "rel": "works_at", "to": "org_acme"},
    {"from": "person_alice_johnson", "rel": "met_at", "to": "event_tech_conference_2026"},
    {"from": "person_alice_johnson", "rel": "assigned_to", "to": "project_alpha"}
  ]
}
```

## From Client Notes (`references/clients/*.md`)

**Extracts:**
- `Organization` entity
- `has_contract_value` → number
- `projects` → `Project` entities
- `primary_contact` → `Person`

## From Team Notes (`references/team/*.md`)

**Extracts:**
- `Person` entity
- `works_for` → `Organization`
- `assigned_to` → `Project[]`
- `reports_to` → `Person`
- `response_pattern` → (proactive, reactive, non-responsive)

## From Daily Status (`daily-status/YYYY-MM-DD/*.md`)

**Extracts:**
- `response_time` property on Person
- `status_update` → `Event`
- `blockers` → `Issue` entities
- `behavioral_pattern` tracking

## From Project Notes (`projects/*.md`)

**Extracts:**
- `Project` entity
- `for_client` → `Organization`
- `team` → `Person[]`
- `status`, `value`, `deadline`

## Detection Rules

```python
# Contact files
if file.startswith("references/contacts/"):
    entity_type = "Person"
    extract_email_from_content()
    extract_company_from_property("Company:")
    extract_projects_from_links([[Project]])
    
# Client files
if file.startswith("references/clients/"):
    entity_type = "Organization"
    extract_contract_value()
    extract_projects()
    
# Team files
if file.startswith("references/team/"):
    entity_type = "Person"
    role = "team_member"
    extract_assignments()
    extract_response_patterns()
```

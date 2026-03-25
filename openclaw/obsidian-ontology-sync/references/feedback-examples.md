# Feedback Loop Examples Reference

## Example 1: Missing Email Detection

**Ontology finds:** Person entity with no email property

**Feedback generated:**
```markdown
## Missing Contact Information

The following team members are missing email addresses:

- [ ] Bob (`references/team/Bob.md`)
- [ ] Lucky (`references/team/Lucky.md`)

**Suggestion:** Add email field to team member template:
\`\`\`markdown
**Email:** 
\`\`\`
```

## Example 2: Broken Project Links

**Ontology finds:** Person assigned_to Project that doesn't exist

**Feedback generated:**
```markdown
## Broken Project References

Found references to projects that don't have dedicated files:

- [ ] "Project Epsilon" mentioned in team files but no `projects/Project Epsilon.md`
- [ ] "Project Delta Tata DT" assigned but no project file

**Suggestion:** Create project files with template
```

## Example 3: Relationship Discovery

**Ontology finds:** Multiple people working at same company

**Feedback generated:**
```markdown
## Suggested Company Grouping

Found 3 contacts at "TechHub":
- Jane Doe
- [2 others from daily-status mentions]

**Suggestion:** Create `references/clients/TechHub.md` and link contacts
```

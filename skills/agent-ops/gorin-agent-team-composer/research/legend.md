# Legend

This file explains the field names and output conventions used by `agent-team-composer`.

## Core Output Files

- `SOUL.md`: team operating principles and collaboration posture
- `AGENTS.md`: role roster, routing, and task ownership
- `CollaborationRules.md`: explicit execution rules, handoffs, and reporting loop
- `Contacts.md`: IM channels, escalation targets, and notification surfaces
- `agent-config.yaml`: machine-readable team configuration for downstream tooling

## Common Template Variables

- `{{team_name}}`: user-facing team name
- `{{team_slug}}`: filesystem-safe directory name
- `{{team_mission}}`: concise mission statement inferred from the prompt
- `{{workflow_mode}}`: `parallel`, `serial`, or `hybrid`
- `{{im_channels}}`: enabled communication platforms such as Telegram, Discord, WeChat
- `{{agent_roster}}`: structured list of agents with role and responsibility

## Output Standard

- Generated files must be immediately readable and editable by humans.
- No unresolved `{{placeholder}}` tokens may remain in produced output.
- The generated team package should be safe by default:
  - no real credentials
  - no automatic deployment
  - no destructive mutations of existing teams

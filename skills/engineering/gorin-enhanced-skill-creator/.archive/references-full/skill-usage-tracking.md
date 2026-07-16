# Skill Usage Tracking

Track how often and how effectively skills are used, based on Anthropic's PreToolUse hook approach (Thariq, 2026).

## Why Track Usage

- Identify skills that are never triggered (dead code)
- Detect false positives (skill fires when it shouldn't)
- Measure effectiveness: does using the skill produce better outcomes?
- Justify investment in skill maintenance vs retirement

## Approach: PreToolUse Hook

The simplest tracking method intercepts skill activation via a PreToolUse hook on the relevant tool calls.

### Minimal Example (pseudo-code)

```bash
# In a PreToolUse hook that fires when a skill is loaded:
SKILL_NAME=$(extract_skill_name "$TOOL_INPUT")
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Append-only log — one JSONL line per invocation
echo "{\"ts\":\"$TIMESTAMP\",\"skill\":\"$SKILL_NAME\",\"session\":\"$SESSION_ID\",\"trigger\":\"$TRIGGER_PHRASE\"}" \
  >> "$CLAW_DATA/skills/usage-log.jsonl"
```

### OpenClaw Implementation

In OpenClaw, skill usage can be tracked by hooking into the skill resolution/trigger flow. Create a lightweight log in a stable data directory:

```
~/.openclaw/workspace-{name}/data/skill-usage/
├── usage-log.jsonl      # Append-only: one line per skill invocation
└── monthly-summary.json  # Aggregated stats, regenerated periodically
```

### Log Schema (JSONL)

```json
{
  "ts": "2026-03-19T04:46:00Z",
  "skill": "enhanced-skill-creator",
  "session": "agent:daily-devops:telegram:group:xxx:topic:1",
  "trigger": "create skill for X",
  "model": "zai/glm-5-turbo",
  "result": "success",
  "duration_ms": 120000
}
```

### Analysis Queries

```bash
# Most-used skills (last 30 days)
cat usage-log.jsonl | jq -r 'select(.ts > "2026-02-17") | .skill' | sort | uniq -c | sort -rn | head -10

# Skills never triggered (compare against installed list)
comm -23 <(ls ~/.openclaw/skills/ | sort) <(cat usage-log.jsonl | jq -r .skill | sort -u)

# False positive rate (skill loaded but not used)
cat usage-log.jsonl | jq 'select(.result == "dismissed")' | jq -r .skill | sort | uniq -c | sort -rn
```

## Best Practices

- **Append-only logs**: Never mutate the log file. Use separate aggregation scripts.
- **Stable paths**: Store logs outside the skill directory to survive upgrades.
- **Privacy**: Log skill names and session IDs, not full conversation content.
- **Retention**: Rotate logs monthly; keep summaries indefinitely.
- **Automation**: Use a cron/heartbeat job to regenerate the monthly summary.

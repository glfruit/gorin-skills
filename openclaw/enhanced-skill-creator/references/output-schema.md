# Output Schema

All machine-readable scripts in `enhanced-skill-creator` should converge toward this JSON envelope.

## Canonical Envelope

```json
{
  "tool": "validate-skill",
  "version": "0.1",
  "skillPath": "/abs/path/to/skill",
  "result": "PASS",
  "summary": {
    "pass": 18,
    "fail": 0,
    "warn": 0,
    "skip": 1,
    "score": 94
  },
  "findings": [
    {
      "id": "routing_safety_metadata",
      "severity": "fail",
      "category": "routing-safety",
      "message": "Description lacks explicit negative trigger phrasing",
      "detail": "...",
      "suggestedFix": "Add a negative trigger such as 'Don't use it for ...'"
    }
  ],
  "artifacts": {
    "overlaps": [],
    "suggestions": {},
    "draft": null
  }
}
```

## Field Semantics
- `tool`: script/tool name producing the result
- `version`: schema version for downstream consumers
- `skillPath`: analyzed skill root
- `result`: `PASS | FAIL | WARN | INFO`
- `summary`: compact counters + optional score
- `findings`: normalized diagnostic rows
- `artifacts`: tool-specific structured payloads (overlaps, suggestions, generated draft, etc.)

## Severity
- `fail`: blocking issue
- `warn`: non-blocking but important issue
- `skip`: optional check not executed
- `info`: informational note
- `pass`: only use when emitting explicit check rows; downstream consumers should primarily read failures/warnings

## Categories
- `structure`
- `metadata`
- `routing-safety`
- `workflow`
- `progressive-disclosure`
- `resources`
- `scripts`
- `error-handling`
- `collision`
- `blockers`

## Migration Guidance
MVP scripts do not need to fully rewrite to this schema immediately, but new scripts should either:
1. emit this schema directly, or
2. provide enough stable fields to be adapted into it later.

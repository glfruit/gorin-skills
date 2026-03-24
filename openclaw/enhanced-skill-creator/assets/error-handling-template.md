## Error Handling

### Missing Prerequisites
- If a required file, tool, credential, or environment variable is missing, stop immediately and report the exact missing prerequisite.
- Do not guess hidden defaults.

### Unsupported Input or Configuration
- If the input format, project layout, or toolchain is unsupported, explain exactly which assumption failed.
- If a safe fallback exists, use it. Otherwise stop and report.

### Script or Tool Failure
- If a script exits non-zero, capture the exact command, stderr summary, and likely cause.
- Do not silently continue after a failed deterministic step.

### Ambiguous State
- If the workflow cannot continue without guessing, stop and ask for clarification or report the blocker.
- Explicitly name the step where the ambiguity occurred.

### Partial Success
- If only part of the workflow succeeds, summarize:
  - what completed
  - what failed
  - what remains manual
  - whether rollback is needed

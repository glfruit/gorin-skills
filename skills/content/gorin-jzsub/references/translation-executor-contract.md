# Non-interactive Translation Executor contract

Use `translation_executor.py` for exactly one complete Source Transcript
attempt. V1 supports the `codex` adapter. The request and every progress/final
record use `schema_version: "1.0.0"`; unknown fields and schema majors fail
closed.

The request is Provider-neutral:

```json
{
  "schema_version": "1.0.0",
  "attempt_id": "job-123-translation-1",
  "subtitle_manifest": "/working/job-123/subtitles/subtitle-manifest.json",
  "provider": {"adapter": "codex", "model": "gpt-5.4"},
  "limits": {"batch_timeout_seconds": 300, "max_batch_attempts": 2},
  "cancellation_path": "/controller/job-123/cancel.requested",
  "progress_path": "/controller/job-123/translation-progress.jsonl"
}
```

Invoke it with adapter deployment configuration outside the request contract:

```bash
python3 <skill-dir>/scripts/translation_executor.py run \
  --request <request.json> \
  --codex-home <dedicated-codex-home> \
  --codex-executable codex
```

`--codex-home` is mandatory. The executor rejects the ordinary `~/.codex` and
an inherited `CODEX_HOME`, gives Codex a separate temporary `HOME`, strips the
parent environment to a small allowlist, runs in an isolated non-repository
directory with a read-only sandbox, ignores user configuration and rules, and
uses an ephemeral session. The adapter disables Codex's shell tool and web
search and uses a never-escalate approval policy, so subtitle prompt injection
cannot turn translation into host inspection. Provision authentication directly
in the dedicated home; never copy or inspect the interactive home.

Progress is append-only JSONL with monotonic `sequence`. Events are
`attempt_started`, `batch_started`, `batch_succeeded`, `attempt_succeeded`,
`attempt_failed`, or `attempt_cancelled`. The process writes exactly one final
result object to stdout and exits with:

| Exit | Failure Class | Meaning |
|---:|---|---|
| 0 | `null` | Complete attempt promoted |
| 20 | `authentication` | Codex authentication unavailable |
| 21 | `quota_exhausted` | plan/rate/quota limit |
| 22 | `provider_unavailable` | executable/service/process unavailable |
| 23 | `timeout` | batch deadline exceeded |
| 24 | `invalid_structure` | malformed, incomplete, reordered, or token-damaged output |
| 25 | `cancelled` | cooperative cancellation observed |
| 26 | `software_error` | invalid request/configuration or executor defect |

Retries remain inside the same attempt and Provider. Each retry receives the
same source-locked batch. Cue IDs, order, and protected URLs, timestamps,
hashtags, handles, email addresses, model identifiers, and numerals must match
before a batch enters staging.

No batch file is written to the formal `translation-output` directory during
execution. Only after every batch passes both adapter validation and the
subtitle pipeline's complete-ledger validation is the staging directory
atomically promoted. A Provider switch therefore requires a new attempt; files
from failed or cancelled attempts are diagnostic and can never be rendered as
formal translation.

The attempt-local `execution-manifest.json` records request/source hashes,
Provider identity, batch outcomes, durations, exit statuses, and output hashes.
It intentionally stores no prompt, subtitle payload, stderr, credentials, or
secret-bearing environment and is not part of the Controller boundary.
Before promotion it is durably checkpointed as `ready_to_promote`. Once the
formal directory exists, a later progress or diagnostic-sink failure cannot
retroactively change the final result to unpromoted failure.

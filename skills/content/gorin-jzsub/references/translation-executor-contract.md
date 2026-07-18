# Non-interactive Translation Executor contract

Use `translation_executor.py` for exactly one complete Source Transcript
attempt. V1 supports the `codex` and `openai-compatible` adapters. The request and every progress/final
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

For one paid API Attempt, set `provider.adapter` to `openai-compatible`, choose
exactly one `provider.service` (`deepseek` or `openai`), and provide
`paid_attempt`, `quality`, and the closed circuit state in the request. Pass a
deployment config separately:

```json
{
  "paid_attempt": {
    "media_job_id": "job-123",
    "ordinal": 1,
    "reservation": {
      "id": "reservation-123",
      "max_input_tokens": 50000,
      "max_output_tokens": 20000
    },
    "additional_attempt_approval": null
  },
  "quality": {
    "rules_version": "deterministic-v1",
    "max_repairs": 1,
    "high_assurance_review": false
  },
  "circuit_breaker": {"state": "closed"}
}
```

```json
{
  "schema_version": "1.0.0",
  "service": "deepseek",
  "base_url": "https://api.deepseek.com/v1",
  "credential_env": "TRANSLATION_API_KEY_REF"
}
```

```bash
python3 <skill-dir>/scripts/translation_executor.py run \
  --request <api-request.json> \
  --api-config <api-config.json>
```

The config stores a credential environment-variable name, never its value.
The selected service must match the request. Token reservation, paid Attempt
ordinal, second-Attempt approval evidence, and circuit state are checked before
the credential is resolved or any HTTP request is sent. Authentication and
shared configuration failures open the capability circuit and are never
retried inside the Attempt.

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
| 26 | `software_error` | invalid request or executor defect |
| 27 | `quality_rejected` | deterministic quality risk remains after repair |
| 28 | `budget_exhausted` | paid reservation or approval is insufficient |
| 29 | `configuration` | shared Provider config/credential/circuit failure |

Retries remain inside the same attempt and Provider. Each retry receives the
same source-locked batch. Cue IDs, order, and protected URLs, timestamps,
hashtags, handles, email addresses, model identifiers, and numerals must match
before a batch enters staging.

After structural validation, `deterministic-v1` rejects empty/copy/refusal,
repetition, abnormal length, target-language mismatch, and protected-token
damage. One complete batch repair may run with the same Provider. A remaining
risk returns `needs_attention` with `quality_rejected`; it is never promoted.
The Execution Manifest identifies the sole Provider for all formal cue text and
records that optional High Assurance Review has zero translation contribution.
When High Assurance is requested, its evidence names a different reviewer
Provider, a separate Review Attempt and reservation, `pass`/`reject`, reviewed
cue IDs, and issue locations. The reviewed IDs must cover the Executor's
deterministic per-batch sample and every cue flagged before repair. Review and
translation Attempt/reservation identities must differ, and the contract has
no field through which reviewer text can enter formal output. A review rejection is
`quality_rejected`. Codex requests that predate the quality field receive the
same deterministic defaults, so omission cannot bypass the gate.

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

# Eval System Schemas

This document defines the JSON schemas used by the eval runner and review generator.

---

## evals.json

Input file for `run_eval.py`. Contains test cases to evaluate skill behavior.

```json
{
  "cases": [
    {
      "id": "eval-001",
      "prompt": "Create a new skill for summarizing PDF documents.",
      "expected": "keyword or regex:pattern",
      "context": "Optional human-readable description of what this case tests"
    }
  ]
}
```

| Field      | Type           | Required | Description |
|------------|----------------|----------|-------------|
| `cases`    | array          | Yes      | List of eval cases |
| `id`       | string         | Yes      | Unique case identifier (e.g. `eval-001`) |
| `prompt`   | string         | Yes      | The user prompt sent to the LLM |
| `expected` | string or list | Yes      | Grading criteria. String: case-insensitive substring match. List: ANY element match. `regex:...`: regex pattern match |
| `context`  | string         | No       | Human-readable description of the test case purpose |

---

## eval_metadata.json

Per-case output written to `<workspace>/iteration-N/eval-<id>/eval_metadata.json`.

```json
{
  "id": "eval-001",
  "prompt": "Create a new skill for summarizing PDF documents.",
  "expected": ["skill", "SKILL.md"],
  "with_skill_output": "To create a skill for summarizing PDF documents...",
  "without_skill_output": "I can help you summarize PDF documents...",
  "grading": {
    "passed": true,
    "notes": "matched list item: 'skill'"
  },
  "tokens_with": 156,
  "tokens_without": 89,
  "time_with_ms": 2340,
  "time_without_ms": 1890
}
```

| Field               | Type   | Description |
|---------------------|--------|-------------|
| `id`                | string | Case identifier |
| `prompt`            | string | Original prompt |
| `expected`          | any    | Original expected criteria |
| `with_skill_output` | string | LLM response when skill SKILL.md was the system prompt |
| `without_skill_output` | string | LLM response with generic system prompt |
| `grading`           | object | Grading result (see `grading.json` below) |
| `tokens_with`       | int    | Prompt tokens used for the with-skill call |
| `tokens_without`    | int    | Prompt tokens used for the without-skill call |
| `time_with_ms`      | int    | Wall-clock time for with-skill call (milliseconds) |
| `time_without_ms`   | int    | Wall-clock time for without-skill call (milliseconds) |

---

## grading.json

Embedded inside `eval_metadata.json` under the `grading` key.

```json
{
  "passed": true,
  "notes": "matched list item: 'skill'"
}
```

| Field    | Type   | Description |
|----------|--------|-------------|
| `passed` | bool   | Whether the with-skill output matched the expected criteria |
| `notes`  | string | Human-readable explanation of how grading was determined |

---

## benchmark.json

Summary written to `<workspace>/iteration-N/benchmark.json`.

```json
{
  "timestamp": "2026-04-11T23:45:00+0800",
  "iteration": 1,
  "model": "gpt-4o-mini",
  "total_cases": 3,
  "pass_rate": 0.6667,
  "avg_tokens_with": 145.3,
  "avg_tokens_without": 87.0,
  "avg_time_with_ms": 2100.5,
  "avg_time_without_ms": 1750.0,
  "per_case": [
    {
      "id": "eval-001",
      "passed": true,
      "tokens_with": 156,
      "tokens_without": 89,
      "time_with_ms": 2340,
      "time_without_ms": 1890
    }
  ]
}
```

| Field              | Type   | Description |
|--------------------|--------|-------------|
| `timestamp`        | string | ISO 8601 timestamp of the run |
| `iteration`        | int    | Iteration number |
| `model`            | string | LLM model used |
| `total_cases`      | int    | Number of cases evaluated |
| `pass_rate`        | float  | Fraction of cases that passed (0.0–1.0) |
| `avg_tokens_with`  | float  | Average prompt tokens across all with-skill calls |
| `avg_tokens_without` | float | Average prompt tokens across all without-skill calls |
| `avg_time_with_ms` | float  | Average wall-clock time for with-skill calls (ms) |
| `avg_time_without_ms` | float | Average wall-clock time for without-skill calls (ms) |
| `per_case`         | array  | Per-case summary (subset of eval_metadata fields) |

---

## feedback.json

Downloaded from the review page's "Download feedback.json" button.

```json
{
  "timestamp": "2026-04-11T23:50:00+0800",
  "per_case": [
    {
      "id": "eval-001",
      "feedback": "The with-skill output correctly suggested a SKILL.md structure but missed the trigger patterns section."
    }
  ]
}
```

| Field      | Type   | Description |
|------------|--------|-------------|
| `timestamp` | string | ISO 8601 timestamp when feedback was downloaded |
| `per_case` | array  | List of case feedback entries (only cases with non-empty feedback) |
| `id`       | string | Case identifier |
| `feedback` | string | Human reviewer feedback text |

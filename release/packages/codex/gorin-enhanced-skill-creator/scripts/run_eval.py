#!/usr/bin/env python3
"""Eval Runner: Compare LLM outputs with and without a skill.

Reads evals.json, runs each test case against an LLM twice (with skill system
prompt, without skill system prompt), grades responses, and writes per-case
metadata plus a benchmark summary.

Usage:
    python3 run_eval.py --evals PATH --workspace PATH [--skill-path PATH] \
                        --iteration INT [--model STR] [--dry-run]

Exit codes:
    0 — all cases passed
    1 — catastrophic/setup failure
    2 — partial failures (one or more cases failed or errored)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path


def load_evals(path: str) -> list[dict]:
    """Load and validate eval cases from evals.json."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cases = data.get("cases", [])
    if not cases:
        raise ValueError("evals.json contains no cases")
    for case in cases:
        if "id" not in case or "prompt" not in case or "expected" not in case:
            raise ValueError(f"case missing required fields (id/prompt/expected): {case}")
    return cases


def sanitize_case_id(raw_id: object, index: int) -> str:
    """Sanitize case IDs before using them in filesystem paths."""
    text = str(raw_id or "")
    text = text.replace("/", "").replace("\\", "").replace("..", "")
    text = re.sub(r"[^A-Za-z0-9_-]+", "-", text).strip("-_")
    return text or f"eval-fallback-{index}"


def grade(response: str, expected) -> dict:
    """Grade a response against expected criteria.

    Args:
        response: The with_skill LLM response text.
        expected: String (substring match), list (ANY match),
                  or "regex:..." pattern.

    Returns:
        {"passed": bool, "notes": str}
    """
    resp_lower = response.lower()

    if isinstance(expected, list):
        for item in expected:
            if item.lower() in resp_lower:
                return {"passed": True, "notes": f"matched list item: '{item}'"}
        return {"passed": False, "notes": f"no list item matched in response"}

    if isinstance(expected, str):
        if expected.startswith("regex:"):
            pattern = expected[len("regex:"):]
            try:
                if re.search(pattern, response, re.IGNORECASE | re.DOTALL):
                    return {"passed": True, "notes": f"regex matched: {pattern}"}
                else:
                    return {"passed": False, "notes": f"regex did not match: {pattern}"}
            except re.error as e:
                return {"passed": False, "notes": f"invalid regex '{pattern}': {e}"}

        # Simple substring match
        if expected.lower() in resp_lower:
            return {"passed": True, "notes": f"substring matched: '{expected}'"}
        else:
            return {"passed": False, "notes": f"substring not found: '{expected}'"}

    return {"passed": False, "notes": f"unexpected expected type: {type(expected)}"}


def call_llm(system: str, user: str, model: str, base_url: str | None) -> tuple[str, int]:
    """Call OpenAI-compatible API. Returns (response_text, prompt_tokens)."""
    from openai import OpenAI

    kwargs: dict = {"api_key": os.environ.get("OPENAI_API_KEY", "")}
    if base_url:
        kwargs["base_url"] = base_url

    client = OpenAI(**kwargs)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
        max_tokens=2048,
    )

    text = resp.choices[0].message.content or ""
    tokens = resp.usage.prompt_tokens if resp.usage else 0
    return text, tokens


def run_single_case(case: dict, skill_system: str, model: str,
                    base_url: str | None) -> dict:
    """Run a single eval case (with + without skill)."""
    prompt = case["prompt"]
    expected = case["expected"]

    # With skill
    t0 = time.perf_counter()
    with_skill_output, tokens_with = call_llm(skill_system, prompt, model, base_url)
    time_with_ms = round((time.perf_counter() - t0) * 1000)

    # Without skill
    t1 = time.perf_counter()
    without_skill_output, tokens_without = call_llm(
        "You are a helpful assistant.", prompt, model, base_url
    )
    time_without_ms = round((time.perf_counter() - t1) * 1000)

    grading = grade(with_skill_output, expected)
    baseline_grading = grade(without_skill_output, expected)

    return {
        "id": case["id"],
        "prompt": prompt,
        "expected": expected,
        "with_skill_output": with_skill_output,
        "without_skill_output": without_skill_output,
        "grading": grading,
        "baseline_grading": baseline_grading,
        "baseline_better": baseline_grading["passed"] and tokens_without < tokens_with,
        "tokens_with": tokens_with,
        "tokens_without": tokens_without,
        "time_with_ms": time_with_ms,
        "time_without_ms": time_without_ms,
    }


def main():
    parser = argparse.ArgumentParser(description="Eval runner: with-skill vs without-skill")
    parser.add_argument("--evals", required=True, help="Path to evals.json")
    parser.add_argument("--workspace", required=True,
                        help="Workspace root for output files")
    parser.add_argument("--skill-path", default="./SKILL.md",
                        help="Path to SKILL.md file for system prompt (default: ./SKILL.md)")
    parser.add_argument("--iteration", required=True, type=int,
                        help="Iteration number (creates iteration-N/ subdirectory)")
    parser.add_argument("--model", default="gpt-4o-mini",
                        help="LLM model name (default: gpt-4o-mini)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print case list and exit without calling API")
    args = parser.parse_args()

    evals_path = Path(args.evals)
    if not evals_path.is_file():
        print(f"Error: evals file not found: {evals_path}", file=sys.stderr)
        sys.exit(1)

    skill_path = Path(args.skill_path)
    if not skill_path.is_file():
        print(f"Error: skill path not found: {skill_path}", file=sys.stderr)
        sys.exit(1)

    try:
        cases = load_evals(str(evals_path))
        skill_system = skill_path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    base_url = os.environ.get("OPENAI_BASE_URL")
    iteration_dir = Path(args.workspace) / f"iteration-{args.iteration}"

    if args.dry_run:
        print(f"Dry run: {len(cases)} cases, model={args.model}")
        print(f"Skill: {skill_path}  ({len(skill_system)} chars)")
        print(f"Workspace: {iteration_dir}\n")
        for index, case in enumerate(cases, start=1):
            ctx = case.get("context", "")
            display_id = sanitize_case_id(case.get("id"), index)
            print(f"  [{display_id}] expected={case['expected']!r}")
            print(f"         prompt: {case['prompt'][:100]}{'...' if len(case['prompt']) > 100 else ''}")
            if ctx:
                print(f"         context: {ctx[:80]}{'...' if len(ctx) > 80 else ''}")
        sys.exit(0)

    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is required (set --dry-run to skip API calls)",
              file=sys.stderr)
        sys.exit(1)

    try:
        from openai import APIError
    except ImportError:
        print("Error: 'openai' package not installed. Run: pip install openai", file=sys.stderr)
        sys.exit(1)

    print(f"Running {len(cases)} cases with model={args.model}...")
    iteration_dir.mkdir(parents=True, exist_ok=True)

    per_case_results = []
    partial_failures = False

    for index, case in enumerate(cases, start=1):
        safe_case_id = sanitize_case_id(case.get("id"), index)
        print(f"  [{safe_case_id}] ...", end=" ", flush=True)
        try:
            result = run_single_case(case, skill_system, args.model, base_url)
            case_dir = iteration_dir / f"eval-{safe_case_id}"
            case_dir.mkdir(parents=True, exist_ok=True)

            (case_dir / "with_skill_output.txt").write_text(
                result["with_skill_output"], encoding="utf-8"
            )
            (case_dir / "without_skill_output.txt").write_text(
                result["without_skill_output"], encoding="utf-8"
            )
            meta = {k: v for k, v in result.items()}
            meta["id"] = safe_case_id
            (case_dir / "eval_metadata.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
            )

            passed = result["grading"]["passed"]
            baseline_passed = result["baseline_grading"]["passed"]
            if not passed:
                partial_failures = True
            per_case_results.append({
                "id": safe_case_id,
                "passed": passed,
                "baseline_passed": baseline_passed,
                "baseline_better": result["baseline_better"],
                "tokens_with": result["tokens_with"],
                "tokens_without": result["tokens_without"],
                "time_with_ms": result["time_with_ms"],
                "time_without_ms": result["time_without_ms"],
            })
            print("PASS" if passed else "FAIL")
        except (json.JSONDecodeError, APIError, Exception) as exc:
            partial_failures = True
            print("ERROR")
            print(f"Error in case '{safe_case_id}': {exc}", file=sys.stderr)
            case_dir = iteration_dir / f"eval-{safe_case_id}"
            case_dir.mkdir(parents=True, exist_ok=True)
            meta = {
                "id": safe_case_id,
                "prompt": case.get("prompt", ""),
                "expected": case.get("expected"),
                "with_skill_output": "",
                "without_skill_output": "",
                "grading": {"passed": False, "notes": f"case error: {exc}"},
                "baseline_grading": {"passed": False, "notes": "not available due to case error"},
                "baseline_better": False,
                "tokens_with": 0,
                "tokens_without": 0,
                "time_with_ms": 0,
                "time_without_ms": 0,
                "error": str(exc),
            }
            (case_dir / "eval_metadata.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            per_case_results.append({
                "id": safe_case_id,
                "passed": False,
                "baseline_passed": False,
                "baseline_better": False,
                "tokens_with": 0,
                "tokens_without": 0,
                "time_with_ms": 0,
                "time_without_ms": 0,
            })

    total = len(per_case_results)
    passed_count = sum(1 for r in per_case_results if r["passed"])
    baseline_pass_count = sum(1 for r in per_case_results if r.get("baseline_passed"))
    benchmark = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "iteration": args.iteration,
        "model": args.model,
        "total_cases": total,
        "pass_rate": round(passed_count / total, 4) if total > 0 else 0,
        "baseline_pass_rate": round(baseline_pass_count / total, 4) if total > 0 else 0,
        "avg_tokens_with": round(sum(r["tokens_with"] for r in per_case_results) / total, 1) if total > 0 else 0,
        "avg_tokens_without": round(sum(r["tokens_without"] for r in per_case_results) / total, 1) if total > 0 else 0,
        "avg_time_with_ms": round(sum(r["time_with_ms"] for r in per_case_results) / total, 1) if total > 0 else 0,
        "avg_time_without_ms": round(sum(r["time_without_ms"] for r in per_case_results) / total, 1) if total > 0 else 0,
        "per_case": per_case_results,
    }
    benchmark_path = iteration_dir / "benchmark.json"
    benchmark_path.write_text(json.dumps(benchmark, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nBenchmark: {passed_count}/{total} passed ({benchmark['pass_rate']:.0%})")
    print(f"Baseline pass rate: {benchmark['baseline_pass_rate']:.0%}")
    print(f"Output: {iteration_dir}")

    sys.exit(2 if partial_failures else 0)


if __name__ == "__main__":
    main()

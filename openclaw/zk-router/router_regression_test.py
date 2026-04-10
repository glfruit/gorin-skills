#!/usr/bin/env python3
"""Router regression test for zk-router/router.py."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def run_router(router_py: Path, text: str, source_context: str) -> dict:
    p = subprocess.run(
        ["python3", str(router_py), text, source_context],
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "router run failed")
    return json.loads((p.stdout or "").strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--router", default=str(Path(__file__).resolve().parent / "router.py"))
    ap.add_argument("--cases", default=str(Path(__file__).resolve().parent / "router_regression_cases.json"))
    args = ap.parse_args()

    router = Path(args.router).expanduser()
    cases_path = Path(args.cases).expanduser()

    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    total = len(cases)
    ok = 0
    details = []

    for i, c in enumerate(cases, 1):
        got = run_router(router, c["input"], c.get("source_context", "user"))
        type_ok = got.get("type", "") == c.get("expect_type", "")
        subtype_ok = got.get("subtype", "") == c.get("expect_subtype", "")
        pass_case = type_ok and subtype_ok
        if pass_case:
            ok += 1
        details.append(
            {
                "id": i,
                "pass": pass_case,
                "expect": {"type": c.get("expect_type", ""), "subtype": c.get("expect_subtype", "")},
                "got": {"type": got.get("type", ""), "subtype": got.get("subtype", "")},
                "source_context": c.get("source_context", "user"),
                "input": c.get("input", "")[:120],
            }
        )

    acc = round(ok * 100.0 / total, 2) if total else 0.0
    print(
        json.dumps(
            {
                "status": "ok",
                "total": total,
                "passed": ok,
                "failed": total - ok,
                "accuracy_percent": acc,
                "target_percent": 95,
                "target_passed": acc >= 95,
                "details": details,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Benchmark dedup lookup: index-first vs full scan."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time
from pathlib import Path


def run(cmd: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def bench_query_index(index_path: Path, source_url: str, title: str, rounds: int) -> list[float]:
    times = []
    cmd = [
        "python3",
        str(Path(__file__).resolve().parent / "dedup_index.py"),
        "query",
        "--index",
        str(index_path),
        "--source-url",
        source_url,
        "--title",
        title,
    ]
    for _ in range(rounds):
        t0 = time.perf_counter()
        rc, out, _ = run(cmd)
        dt = (time.perf_counter() - t0) * 1000
        if rc != 0:
            raise RuntimeError(f"index query failed: {out}")
        times.append(dt)
    return times


def bench_scan_lookup(vault: Path, source_url: str, title: str, rounds: int) -> list[float]:
    needle_url = f'source_url: "{source_url}"' if source_url else ""
    needle_title = f'title: "{title}"' if title else ""
    files = [p for p in vault.rglob("*.md") if p.is_file() and not str(p.relative_to(vault)).startswith(".archive/")]

    times = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        found = 0
        for p in files:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if needle_url and needle_url in text:
                found += 1
                continue
            if needle_title and needle_title in text:
                found += 1
        _ = found
        dt = (time.perf_counter() - t0) * 1000
        times.append(dt)
    return times


def summary(xs: list[float]) -> dict:
    return {
        "min_ms": round(min(xs), 2),
        "p50_ms": round(statistics.median(xs), 2),
        "avg_ms": round(sum(xs) / len(xs), 2),
        "max_ms": round(max(xs), 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--index", required=True)
    ap.add_argument("--source-url", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--rounds", type=int, default=5)
    args = ap.parse_args()

    vault = Path(args.vault).expanduser()
    index_path = Path(args.index).expanduser()

    if not index_path.exists():
        rc, out, err = run([
            "python3",
            str(Path(__file__).resolve().parent / "dedup_index.py"),
            "build",
            "--vault",
            str(vault),
            "--output",
            str(index_path),
        ])
        if rc != 0:
            raise SystemExit(f"index build failed: {out}\n{err}")

    scan_times = bench_scan_lookup(vault, args.source_url, args.title, args.rounds)
    index_times = bench_query_index(index_path, args.source_url, args.title, args.rounds)

    s_scan = summary(scan_times)
    s_index = summary(index_times)

    improvement = 0.0
    if s_scan["avg_ms"] > 0:
        improvement = round((1 - (s_index["avg_ms"] / s_scan["avg_ms"])) * 100, 2)

    print(
        json.dumps(
            {
                "status": "ok",
                "rounds": args.rounds,
                "scan": s_scan,
                "index": s_index,
                "improvement_avg_percent": improvement,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

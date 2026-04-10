#!/usr/bin/env python3
"""Dedup index builder/query tool for zk-router (Phase 3 MVP)."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path


def parse_frontmatter_text(text: str) -> dict[str, str]:
    lines = (text or "").splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}
    end_idx = None
    for i in range(1, min(len(lines), 120)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}

    meta: dict[str, str] = {}
    for ln in lines[1:end_idx]:
        if ":" not in ln:
            continue
        k, v = ln.split(":", 1)
        meta[k.strip()] = v.strip().strip('"')
    return meta


def iter_md_files(vault: Path):
    for p in vault.rglob("*.md"):
        if not p.is_file():
            continue
        rel = str(p.relative_to(vault))
        if rel.startswith(".archive/"):
            continue
        yield p


def build_index(vault: Path) -> dict:
    by_source_url: dict[str, list[str]] = {}
    by_title: dict[str, list[str]] = {}

    scanned = 0
    indexed = 0

    for p in iter_md_files(vault):
        scanned += 1
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        fm = parse_frontmatter_text(text)
        source_url = str(fm.get("source_url", "")).strip()
        title = str(fm.get("title", "")).strip()
        rel = str(p.relative_to(vault))

        if source_url:
            by_source_url.setdefault(source_url, []).append(rel)
        if title:
            by_title.setdefault(title, []).append(rel)
        if source_url or title:
            indexed += 1

    # 稳定顺序
    for d in (by_source_url, by_title):
        for k in list(d.keys()):
            d[k] = sorted(set(d[k]))

    return {
        "version": 1,
        "generated_at": int(time.time()),
        "vault": str(vault),
        "scanned_files": scanned,
        "indexed_files": indexed,
        "by_source_url": by_source_url,
        "by_title": by_title,
    }


def query_index(index: dict, source_url: str, title: str) -> dict:
    by_source_url = index.get("by_source_url", {}) or {}
    by_title = index.get("by_title", {}) or {}

    candidates = []
    seen = set()
    for rel in by_source_url.get(source_url, []) if source_url else []:
        if rel not in seen:
            seen.add(rel)
            candidates.append(rel)
    for rel in by_title.get(title, []) if title else []:
        if rel not in seen:
            seen.add(rel)
            candidates.append(rel)

    return {
        "status": "ok",
        "source_matches": by_source_url.get(source_url, []) if source_url else [],
        "title_matches": by_title.get(title, []) if title else [],
        "candidates": candidates,
    }


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/query zk dedup index")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build")
    p_build.add_argument("--vault", required=True)
    p_build.add_argument("--output", required=True)

    p_query = sub.add_parser("query")
    p_query.add_argument("--index", required=True)
    p_query.add_argument("--source-url", default="")
    p_query.add_argument("--title", default="")

    args = parser.parse_args()

    if args.cmd == "build":
        vault = Path(args.vault).expanduser()
        out = Path(args.output).expanduser()
        if not vault.exists() or not vault.is_dir():
            print(json.dumps({"status": "error", "error": f"vault not found: {vault}"}, ensure_ascii=False))
            return 1
        data = build_index(vault)
        save_json(out, data)
        print(json.dumps({"status": "ok", "output": str(out), "indexed_files": data.get("indexed_files", 0)}, ensure_ascii=False))
        return 0

    if args.cmd == "query":
        idx = Path(args.index).expanduser()
        if not idx.exists():
            print(json.dumps({"status": "error", "error": f"index not found: {idx}"}, ensure_ascii=False))
            return 1
        try:
            data = load_json(idx)
        except Exception as e:
            print(json.dumps({"status": "error", "error": f"index parse failed: {e}"}, ensure_ascii=False))
            return 1

        print(json.dumps(query_index(data, args.source_url, args.title), ensure_ascii=False))
        return 0

    print(json.dumps({"status": "error", "error": "unknown command"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

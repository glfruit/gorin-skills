#!/usr/bin/env python3
"""Relation discovery for zk literature notes (Phase 2 MVP)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were", "have", "has",
    "了", "和", "是", "在", "与", "及", "对", "中", "为", "将", "一个", "我们", "你们", "他们",
    "研究", "分析", "问题", "方法", "系统", "模型", "数据", "实践", "发展", "趋势",
}


def extract_keywords(text: str, limit: int = 40) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,8}", text or "")
    freq: dict[str, int] = {}
    for token in tokens:
        t = token.strip().lower()
        if not t or t in STOPWORDS:
            continue
        if t.isdigit():
            continue
        freq[t] = freq.get(t, 0) + 1
    ranked = sorted(freq.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))
    return [k for k, _ in ranked[:limit]]


def iter_candidate_files(vault: Path, current_note: Path | None):
    roots = [
        vault / "Zettels/3-Permanent",
        vault / "Zettels/2-Literature/Articles",
        vault / "Zettels/2-Literature/Papers",
        vault / "Zettels/2-Literature/Books",
    ]
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.md"):
            if not p.is_file():
                continue
            if current_note and p.resolve() == current_note.resolve():
                continue
            yield p


def score_file(path: Path, keywords: list[str], source_url: str = "", title: str = "") -> tuple[int, str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")[:12000]
    except Exception:
        return 0, "related"

    low = text.lower()
    score = 0

    if source_url and source_url in text:
        score += 8

    shared = 0
    for kw in keywords[:20]:
        if kw in low:
            shared += 1
    score += shared * 2

    if title:
        t = title.strip().lower()
        if t and t in low:
            score += 6

    contradict_markers = ["however", "but", "yet", "however,", "但", "然而", "相反", "质疑", "挑战"]
    has_contradict_marker = any(m in low for m in contradict_markers)

    relation = "related"
    if shared >= 12:
        relation = "cluster"
    elif has_contradict_marker and shared >= 4:
        relation = "contradicts"
    elif shared >= 8:
        relation = "supports"
    elif shared <= 2 and score >= 6:
        relation = "extends"

    return score, relation


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover related notes for literature capture")
    parser.add_argument("--vault", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--content-file", required=True)
    parser.add_argument("--current-note", default="")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    vault = Path(args.vault).expanduser()
    content_file = Path(args.content_file)
    current_note = Path(args.current_note).expanduser() if args.current_note else None

    if not vault.exists():
        print(json.dumps({"status": "error", "error": f"vault not found: {vault}"}, ensure_ascii=False))
        return 1
    if not content_file.exists():
        print(json.dumps({"status": "error", "error": f"content file not found: {content_file}"}, ensure_ascii=False))
        return 1

    content = content_file.read_text(encoding="utf-8", errors="ignore")
    keywords = extract_keywords(f"{args.title}\n{content}")

    candidates: list[dict] = []
    for p in iter_candidate_files(vault, current_note):
        score, relation = score_file(p, keywords, args.source_url, args.title)
        if score <= 0:
            continue
        candidates.append(
            {
                "path": str(p.relative_to(vault)),
                "score": score,
                "relation": relation,
            }
        )

    candidates.sort(key=lambda x: (-x["score"], x["path"]))
    related = candidates[: max(1, args.top_k)]

    print(
        json.dumps(
            {
                "status": "ok",
                "keywords": keywords[:15],
                "related": related,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

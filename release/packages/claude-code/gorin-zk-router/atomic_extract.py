#!/usr/bin/env python3
"""Atomic note extraction for zk literature notes (Phase 2 MVP)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", (line or "").strip())


def strip_frontmatter(text: str) -> str:
    lines = (text or "").splitlines()
    if len(lines) >= 3 and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1 :])
    return text or ""


def split_paragraphs(text: str) -> list[str]:
    text = strip_frontmatter(text)
    raw_parts = re.split(r"\n\s*\n+", text or "")
    parts = []
    for p in raw_parts:
        n = normalize_line(p)
        if len(n) < 40:
            continue
        if n.startswith("#") or n.startswith(">"):
            continue
        parts.append(n)
    return parts


def is_low_value_sentence(s: str) -> bool:
    bad_markers = [
        "引用格式",
        "作者简介",
        "基金项目",
        "文献标志码",
        "中图分类号",
        "文章编号",
        "通讯作者",
        "博士生导师",
        "硕士研究生",
    ]
    if any(m in s for m in bad_markers):
        return True
    # 过滤学术引用串
    if re.search(r"\[[JMDCP]\]", s):
        return True
    return False


def sentence_candidates(paragraph: str) -> list[str]:
    segs = re.split(r"(?<=[。！？.!?])\s+|[；;]", paragraph)
    out = []
    for s in segs:
        n = normalize_line(s)
        if 24 <= len(n) <= 180 and not is_low_value_sentence(n):
            out.append(n)
    return out


def build_atomic_title(text: str, idx: int) -> str:
    zh = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
    if zh:
        return f"{zh[0]}-原子观点-{idx}"
    en = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)
    if en:
        return f"{en[0]}-atomic-{idx}"
    return f"atomic-insight-{idx}"


def extract_atomic_points(content: str, n: int = 5) -> list[dict]:
    paras = split_paragraphs(content)
    picks: list[str] = []
    for para in paras:
        for s in sentence_candidates(para):
            if s not in picks:
                picks.append(s)
            if len(picks) >= n * 3:
                break
        if len(picks) >= n * 3:
            break

    result = []
    for i, text in enumerate(picks[:n], 1):
        result.append(
            {
                "title": build_atomic_title(text, i),
                "content": text,
                "confidence": "mvp",
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract atomic notes from a literature markdown file")
    parser.add_argument("--content-file", required=True)
    parser.add_argument("--max", type=int, default=5)
    args = parser.parse_args()

    content_file = Path(args.content_file)
    if not content_file.exists():
        print(json.dumps({"status": "error", "error": f"missing file: {content_file}"}, ensure_ascii=False))
        return 1

    text = content_file.read_text(encoding="utf-8", errors="ignore")
    points = extract_atomic_points(text, n=max(1, min(8, args.max)))

    print(json.dumps({"status": "ok", "count": len(points), "points": points}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

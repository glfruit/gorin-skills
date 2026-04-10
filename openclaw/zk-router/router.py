#!/usr/bin/env python3
"""ZK Router - Python implementation of routing heuristics."""

from __future__ import annotations

import json
import re
import sys


def has(pattern: str, text: str, flags: int = re.IGNORECASE) -> bool:
    return re.search(pattern, text, flags) is not None


def detect(input_text: str, source_context: str = "user") -> dict:
    score = 0
    detected_type = "fleeting"
    subtype = ""

    # Step 1: URL detection (+40)
    m = re.search(r"https?://\S+", input_text)
    if m:
        url = m.group(0)
        score += 40

        if has(r"(mp\.weixin\.qq\.com|zhihu\.com|csdn|juejin|medium|dev\.to)", url):
            detected_type = "literature"
            subtype = "articles"
        elif has(r"(arxiv\.org|pdf|researchgate|ieee|acm)", url):
            detected_type = "literature"
            subtype = "papers"
        elif has(r"(github\.com|gitlab\.com)", url):
            detected_type = "literature"
            subtype = "code"
        else:
            detected_type = "literature"
            subtype = "articles"

    # Step 2: keyword detection (+30)
    keyword_rules = [
        (r"(会议|讨论|和.*聊|复盘|纪要|与会|参会)", "meeting", "", 30),
        (r"(想法|灵感|突然想到|idea|闪念|想到)", "idea", "", 30),
        (r"(计划|plan|task|待办|TODO|安排)", "plan", "", 30),
        (r"(周总结|月回顾|复盘|review|总结)", "review", "", 30),
        (r"(决策|决定|选择|decision|确定)", "decision", "", 30),
        (r"(总结|摘要|summary|overview|归纳)", "summary", "", 30),
        (r"(问题|疑问|question|怎么|为什么|如何)", "question", "", 30),
        (r"(读书|看《|读后感|书籍|book)", "literature", "books", 30),
    ]

    for pattern, t, st, pts in keyword_rules:
        if has(pattern, input_text):
            if detected_type == "fleeting":
                detected_type = t
                if st:
                    subtype = st
            score += pts
            break

    # Step 3: content features
    content_len = len(input_text)
    if content_len > 1000:
        score += 20
        if detected_type == "fleeting":
            detected_type = "summary"

    if has(r"(^[0-9]+\.|^- |^#{1,6} )", input_text, flags=re.MULTILINE):
        score += 10

    # Step 4: source context
    if source_context == "daily-collector" and detected_type == "fleeting":
        detected_type = "literature"
        subtype = "articles"
        score += 10
    elif source_context == "edu-tl":
        if has(r"(会议|讨论)", input_text):
            detected_type = "meeting"
            score += 10

    return {
        "type": detected_type,
        "subtype": subtype,
        "score": score,
        "length": content_len,
    }


def main() -> int:
    input_text = sys.argv[1] if len(sys.argv) > 1 else ""
    source_context = sys.argv[2] if len(sys.argv) > 2 else "user"
    print(json.dumps(detect(input_text, source_context), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

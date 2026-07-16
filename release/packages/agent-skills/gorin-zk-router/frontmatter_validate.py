#!/usr/bin/env python3
"""Frontmatter validator for zk notes (Phase 2 MVP)."""

from __future__ import annotations

import argparse
import json


REQUIRED_BY_TYPE = {
    "literature": ["title", "type", "date", "source_url"],
    "permanent": ["title", "type", "date"],
    "idea": ["title", "type", "date"],
    "meeting": ["title", "type", "date"],
    "plan": ["title", "type", "date"],
    "review": ["title", "type", "date"],
    "decision": ["title", "type", "date"],
    "summary": ["title", "type", "date"],
    "question": ["title", "type", "date"],
    "fleeting": ["title", "type", "date"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate frontmatter fields")
    parser.add_argument("--note-type", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--date", default="")
    parser.add_argument("--source-url", default="")
    args = parser.parse_args()

    note_type = args.note_type.strip() or "fleeting"
    required = REQUIRED_BY_TYPE.get(note_type, REQUIRED_BY_TYPE["fleeting"])

    values = {
        "title": args.title.strip(),
        "type": note_type,
        "date": args.date.strip(),
        "source_url": args.source_url.strip(),
    }

    missing = [k for k in required if not values.get(k)]
    if missing:
        print(json.dumps({"status": "error", "code": "FM_MISSING_FIELDS", "missing": missing}, ensure_ascii=False))
        return 1

    print(json.dumps({"status": "ok", "note_type": note_type, "required": required}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

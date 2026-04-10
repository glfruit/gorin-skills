#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import json
import re
import sys

INBOX_DIR = Path.home() / "pkm" / "atlas" / "0-Inbox"
DATE_KEYS = ("created", "date")
TITLE_KEY = "title"
DATE_PATTERNS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.DOTALL)
    if not match:
        return {}
    data = {}
    for line in match.group(1).splitlines():
        key_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line.strip())
        if not key_match:
            continue
        key = key_match.group(1).strip().lower()
        value = key_match.group(2).strip().strip("\"'")
        data[key] = value
    return data


def parse_date(value: str):
    if not value:
        return None
    text = value.strip().strip("\"'")
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).replace(tzinfo=None)
    except ValueError:
        pass
    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", text)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            return None
    return None


def extract_title(path: Path, text: str, frontmatter: dict) -> str:
    title = frontmatter.get(TITLE_KEY, "").strip()
    if title:
        return title
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                return heading
    return path.stem


def resolve_created_at(path: Path, frontmatter: dict) -> datetime:
    for key in DATE_KEYS:
        parsed = parse_date(frontmatter.get(key, ""))
        if parsed:
            return parsed
    return datetime.fromtimestamp(path.stat().st_mtime)


def should_promote(title: str, text: str, days_old: int) -> bool:
    lowered = text.lower()
    signals = 0
    if days_old >= 14:
        signals += 1
    if len(text.splitlines()) >= 8:
        signals += 1
    if len(text) >= 400:
        signals += 1
    if any(token in lowered for token in ("总结", "原则", "framework", "insight", "idea", "pattern", "workflow", "lesson")):
        signals += 1
    if re.search(r"\b(todo|待办|临时|inbox|draft)\b", lowered):
        signals -= 1
    if len(title) >= 12:
        signals += 1
    return signals >= 2


def build_note_record(path: Path) -> dict:
    text = read_text(path)
    frontmatter = extract_frontmatter(text)
    created_at = resolve_created_at(path, frontmatter)
    now = datetime.now()
    age_days = max(0, (now - created_at).days)
    return {
        "path": str(path),
        "title": extract_title(path, text, frontmatter),
        "days": age_days,
        "created_at": created_at,
        "text": text,
    }


def main() -> int:
    promote_mode = "--promote" in sys.argv[1:]
    notes = []
    if INBOX_DIR.exists():
        for path in sorted(INBOX_DIR.rglob("*.md")):
            if path.is_file():
                notes.append(build_note_record(path))

    stale_7d = [
        {"title": note["title"], "days": note["days"]}
        for note in notes
        if note["days"] > 7
    ]
    stale_30d = [note for note in notes if note["days"] > 30]

    output = (
        "ATLAS_INBOX_PATROL "
        f"total={len(notes)} "
        f"stale_7d={len(stale_7d)} "
        f"stale_30d={len(stale_30d)} "
        f"notes={json.dumps(stale_7d, ensure_ascii=False)}"
    )

    if promote_mode:
        suggestions = []
        for note in notes:
            if should_promote(note["title"], note["text"], note["days"]):
                suggestions.append({"title": note["title"], "days": note["days"], "suggest": "review_for_3-Permanent"})
        output += f" promote={json.dumps(suggestions, ensure_ascii=False)}"

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

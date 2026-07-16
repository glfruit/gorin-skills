#!/usr/bin/env python3
"""quick-validate.py — Fast pre-check for skill structure before full validation."""
import re
import sys
from pathlib import Path


def fail(msg: str) -> None:
    print(f"QUICK_VALIDATE_FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def pass_check(msg: str) -> None:
    print(f"QUICK_VALIDATE_PASS: {msg}")


def main() -> None:
    if len(sys.argv) < 2:
        fail("Usage: quick_validate.py <skill-directory>")

    skill_dir = Path(sys.argv[1]).resolve()
    skill_md = skill_dir / "SKILL.md"

    if not skill_dir.is_dir():
        fail(f"Directory does not exist: {skill_dir}")
    if not skill_md.is_file():
        fail("SKILL.md not found")

    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()

    if len(lines) > 500:
        fail(f"SKILL.md is {len(lines)} lines (max 500)")

    if not lines or lines[0].strip() != "---":
        fail("Missing YAML frontmatter start")

    if not re.search(r"^name:", text, re.MULTILINE):
        fail("Missing name field")
    if not re.search(r"^description:", text, re.MULTILINE):
        fail("Missing description field")

    flags = re.IGNORECASE | re.MULTILINE

    if not re.search(r"^#+ .*When NOT to Use", text, flags):
        fail("Missing When NOT to Use section")
    if not re.search(r"^#+ .*Error Handling", text, flags):
        fail("Missing Error Handling section")
    if not re.search(r"^#+ .*Internal Acceptance", text, flags):
        fail("Missing Internal Acceptance section")
    if not re.search(r"^#+ .*(Delivery Contract|Delivery Rule)", text, flags):
        fail("Missing Delivery Contract / Delivery Rule section")
    if not re.search(r"^#+ .*Gotchas", text, flags):
        fail("Missing Gotchas section (mandatory)")

    # Check for placeholder text
    placeholder_pattern = re.compile(
        r"TODO|FIXME|placeholder|Step one|example\.com|your .* here", re.IGNORECASE
    )
    exclusion_pattern = re.compile(
        r"never placeholder|No placeholder text|not.*placeholder|no.?placeholder"
        r"|not \"example\\.com\""
        r"|Generated SKILL.md had|placeholder templates"
        r"|无.?placeholder",
        re.IGNORECASE,
    )
    for line in lines:
        if placeholder_pattern.search(line) and not exclusion_pattern.search(line):
            fail("Found likely placeholder text")
            break

    pass_check("basic structure, boundary sections, and delivery sections present")


if __name__ == "__main__":
    main()

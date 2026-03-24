#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="${1:?Usage: quick-validate.sh <skill-directory>}"
SKILL_DIR="${SKILL_DIR%/}"
SKILL_MD="$SKILL_DIR/SKILL.md"

fail() {
  echo "QUICK_VALIDATE_FAIL: $1" >&2
  exit 1
}

pass() {
  echo "QUICK_VALIDATE_PASS: $1"
}

[[ -d "$SKILL_DIR" ]] || fail "Directory does not exist: $SKILL_DIR"
[[ -f "$SKILL_MD" ]] || fail "SKILL.md not found"

line_count=$(wc -l < "$SKILL_MD" | tr -d ' ')
[[ "$line_count" -le 500 ]] || fail "SKILL.md is ${line_count} lines (max 500)"

head -1 "$SKILL_MD" | grep -q '^---$' || fail "Missing YAML frontmatter start"
grep -q '^name:' "$SKILL_MD" || fail "Missing name field"
grep -q '^description:' "$SKILL_MD" || fail "Missing description field"

grep -qiE '^#+ .*When NOT to Use' "$SKILL_MD" || fail "Missing When NOT to Use section"
grep -qiE '^#+ .*Error Handling' "$SKILL_MD" || fail "Missing Error Handling section"
grep -qiE '^#+ .*Internal Acceptance' "$SKILL_MD" || fail "Missing Internal Acceptance section"
grep -qiE '^#+ .*(Delivery Contract|Delivery Rule)' "$SKILL_MD" || fail "Missing Delivery Contract / Delivery Rule section"

if grep -inE 'TODO|FIXME|placeholder|Step one|example\.com|your .* here' "$SKILL_MD" \
  | grep -ivE 'never placeholder|No placeholder text|not "example\.com"|Generated SKILL.md had|placeholder templates' \
  | head -1 | grep -q .; then
  fail "Found likely placeholder text"
fi

pass "basic structure, boundary sections, and delivery sections present"
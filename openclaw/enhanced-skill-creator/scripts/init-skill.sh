#!/usr/bin/env bash
set -euo pipefail

# init-skill.sh — Initialize a new skill scaffold from the enhanced template
# Usage: bash init-skill.sh <skill-name> <output-dir> [resources]
# Example: bash init-skill.sh my-skill /tmp/skills scripts,references,assets

SKILL_NAME="${1:?Usage: bash init-skill.sh <skill-name> <output-dir> [resources]}"
OUTPUT_DIR="${2:?Usage: bash init-skill.sh <skill-name> <output-dir> [resources]}"
RESOURCES="${3:-scripts,references,assets}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$SKILL_ROOT/config/skill-template.md"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "Template not found: $TEMPLATE" >&2
  exit 1
fi

if [[ ! "$SKILL_NAME" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
  echo "Invalid skill name: $SKILL_NAME" >&2
  echo "Use lowercase letters, digits, and hyphens only." >&2
  exit 1
fi

TARGET_DIR="$OUTPUT_DIR/$SKILL_NAME"
if [[ -e "$TARGET_DIR" ]]; then
  echo "Target already exists: $TARGET_DIR" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"
cp "$TEMPLATE" "$TARGET_DIR/SKILL.md"

# Create requested resource dirs
IFS=',' read -r -a resource_dirs <<< "$RESOURCES"
for dir in "${resource_dirs[@]}"; do
  dir="$(echo "$dir" | xargs)"
  [[ -z "$dir" ]] && continue
  mkdir -p "$TARGET_DIR/$dir"
done

# Replace obvious placeholders with skill name defaults
python3 - "$TARGET_DIR/SKILL.md" "$SKILL_NAME" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
name = sys.argv[2]
text = path.read_text(encoding='utf-8')
text = text.replace('{REPLACE: lowercase-hyphen-numbers-only, e.g. "my-cool-skill"}', name)
text = text.replace('{REPLACE: Skill Title}', name.replace('-', ' ').title())
path.write_text(text, encoding='utf-8')
PY

cat <<EOF
Initialized skill scaffold:
- path: $TARGET_DIR
- resources: $RESOURCES

Next steps:
1. Fill in SKILL.md frontmatter and sections
2. Add negative triggers in When NOT to Use
3. Add Error Handling details
4. Define the Internal Acceptance happy path
5. Add scripts/references/assets only if truly needed
6. Run: bash "$SKILL_ROOT/scripts/quick-validate.sh" "$TARGET_DIR"
7. Run: bash "$SKILL_ROOT/scripts/validate-skill.sh" "$TARGET_DIR"
8. Do not report completion to the user until the skill reaches integrated readiness.
EOF

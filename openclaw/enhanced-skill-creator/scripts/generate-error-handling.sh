#!/usr/bin/env bash
set -euo pipefail

# generate-error-handling.sh — Generate an Error Handling section draft for a skill
# Usage: bash generate-error-handling.sh <skill-directory>
# Output: Markdown section draft

SKILL_DIR="${1:?Usage: bash generate-error-handling.sh <skill-directory>}"
SKILL_DIR="${SKILL_DIR%/}"
SKILL_MD="$SKILL_DIR/SKILL.md"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATOR="$SCRIPT_DIR/validate-skill.sh"
STRUCTURE_SUGGESTER="$SCRIPT_DIR/suggest-structure.sh"

if [[ ! -d "$SKILL_DIR" ]]; then
  echo "Skill directory does not exist: $SKILL_DIR" >&2
  exit 1
fi

if [[ ! -f "$SKILL_MD" ]]; then
  echo "SKILL.md not found in: $SKILL_DIR" >&2
  exit 1
fi

VALIDATION_JSON="{}"
STRUCTURE_JSON="{}"
if [[ -x "$VALIDATOR" || -f "$VALIDATOR" ]]; then
  VALIDATION_JSON=$(bash "$VALIDATOR" "$SKILL_DIR" 2>/dev/null || echo '{}')
fi
if [[ -x "$STRUCTURE_SUGGESTER" || -f "$STRUCTURE_SUGGESTER" ]]; then
  STRUCTURE_JSON=$(bash "$STRUCTURE_SUGGESTER" "$SKILL_DIR" 2>/dev/null || echo '{}')
fi

python3 - "$SKILL_MD" "$VALIDATION_JSON" "$STRUCTURE_JSON" <<'PY'
import json
import re
import sys
from pathlib import Path

skill_md = Path(sys.argv[1])
validation = json.loads(sys.argv[2]) if sys.argv[2].strip() else {}
structure = json.loads(sys.argv[3]) if sys.argv[3].strip() else {}
text = skill_md.read_text(encoding='utf-8')

checks = {c.get('name'): c for c in validation.get('checks', [])}
structure_suggestions = structure.get('suggestions', {}) if isinstance(structure, dict) else {}

bullet = lambda s: f"- {s}"

missing_prereq = []
unsupported = []
script_failure = []
ambiguous = []
partial = []

if checks.get('resource_references_exist', {}).get('status') == 'fail':
    missing_prereq.append('If a referenced file in `references/`, `assets/`, or `scripts/` is missing, stop immediately and report the exact missing path.')
if checks.get('routing_safety_metadata', {}).get('status') == 'fail':
    unsupported.append('If metadata is too broad, collision-prone, or uses wildcard/catch-all patterns, narrow the description before packaging or publishing.')
if checks.get('workflow_numbering', {}).get('status') == 'fail':
    ambiguous.append('If the workflow lacks clear numbered steps or branch points, stop and rewrite the procedure before relying on it in execution.')
if checks.get('progressive_disclosure_signals', {}).get('status') == 'fail':
    unsupported.append('If SKILL.md is carrying dense rules or templates without resource files, move them into `references/`, `assets/`, or `scripts/` before expanding scope.')
if checks.get('no_hardcoded_paths', {}).get('status') == 'fail':
    script_failure.append('If a script depends on hardcoded machine-specific paths, replace them with relative paths, `$HOME`, or derived project paths before use.')
if checks.get('script_error_handling', {}).get('status') == 'fail':
    script_failure.append('If a helper script lacks strict shell error handling, add `set -euo pipefail` and descriptive stderr before relying on it.')
if checks.get('script_smoke_test', {}).get('status') == 'fail':
    script_failure.append('If a script fails syntax validation, do not continue; fix the script first and rerun validation.')

if structure_suggestions.get('references'):
    unsupported.append('If dense rules, tables, or taxonomies start bloating `SKILL.md`, relocate them into `references/` and keep only routing and high-level workflow in the main file.')
if structure_suggestions.get('assets'):
    partial.append('If output/config examples are long or reused, move them into `assets/` and reference them instead of duplicating them inline.')
if structure_suggestions.get('scripts'):
    partial.append('If repetitive parsing, extraction, validation, or conversion logic appears in prose, downshift it into a deterministic helper script and document when to run it.')

if 'credential' in text.lower() or 'auth' in text.lower() or 'api' in text.lower():
    missing_prereq.append('If credentials, tokens, or API access are required, verify they exist before execution and stop with a precise message if they are missing.')
if 'research' in text.lower():
    ambiguous.append('If fewer than three real examples or source-backed cases are available, stop and ask for better references instead of fabricating methodology.')

# Fallback defaults to keep the draft useful
if not missing_prereq:
    missing_prereq.append('If a required file, tool, credential, or environment variable is missing, stop immediately and report the exact prerequisite.')
if not unsupported:
    unsupported.append('If the input, configuration, or domain variant is unsupported, explain the failed assumption and stop unless a documented fallback exists.')
if not script_failure:
    script_failure.append('If a helper script or deterministic command fails, capture the exact failing step and stderr summary; do not silently continue.')
if not ambiguous:
    ambiguous.append('If the workflow would require guessing, pause and request clarification or add the missing rule before continuing.')
if not partial:
    partial.append('If only part of the workflow succeeds, summarize what completed, what failed, and what remains manual.')

print('## Error Handling\n')
print('### Missing Prerequisites')
for item in missing_prereq:
    print(bullet(item))
print('\n### Unsupported Input or Configuration')
for item in unsupported:
    print(bullet(item))
print('\n### Script or Tool Failure')
for item in script_failure:
    print(bullet(item))
print('\n### Ambiguous State')
for item in ambiguous:
    print(bullet(item))
print('\n### Partial Success')
for item in partial:
    print(bullet(item))
PY

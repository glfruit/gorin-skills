#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: package-skill.sh <skill-directory> [output-dir] [--acceptance-report <path>]" >&2
}

[[ $# -ge 1 ]] || { usage; exit 1; }

SKILL_DIR="$1"
shift
OUT_DIR="$(pwd)"
ACCEPTANCE_REPORT=""

if [[ $# -gt 0 && "$1" != --* ]]; then
  OUT_DIR="$1"
  shift
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --acceptance-report)
      ACCEPTANCE_REPORT="${2:?--acceptance-report requires a path}"
      shift 2
      ;;
    *)
      usage
      exit 1
      ;;
  esac
done

SKILL_DIR="${SKILL_DIR%/}"
SKILL_NAME="$(basename "$SKILL_DIR")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$SCRIPT_DIR/quick-validate.sh" "$SKILL_DIR"
bash "$SCRIPT_DIR/validate-skill.sh" "$SKILL_DIR" >/dev/null

if [[ -z "$ACCEPTANCE_REPORT" ]]; then
  ACCEPTANCE_REPORT="$SKILL_DIR/acceptance-report.md"
fi

[[ -f "$ACCEPTANCE_REPORT" ]] || { echo "Packaging blocked: missing acceptance report ($ACCEPTANCE_REPORT)" >&2; exit 1; }
grep -qE '(^|[[:space:]])Result:[[:space:]]+passed' "$ACCEPTANCE_REPORT" || { echo "Packaging blocked: acceptance report is not passing ($ACCEPTANCE_REPORT)" >&2; exit 1; }

mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/${SKILL_NAME}.skill"

SKILL_DIR_ENV="$SKILL_DIR" OUT_FILE_ENV="$OUT_FILE" python3 - <<'PY'
from pathlib import Path
import os
import zipfile
skill_dir = Path(os.environ['SKILL_DIR_ENV'])
out_file = Path(os.environ['OUT_FILE_ENV'])
exclude = {'acceptance-report.md', '.DS_Store'}
with zipfile.ZipFile(out_file, 'w', zipfile.ZIP_DEFLATED) as zf:
    for p in skill_dir.rglob('*'):
        if p.is_file() and p.name not in exclude and '__pycache__' not in p.parts:
            zf.write(p, p.relative_to(skill_dir.parent))
print(out_file)
PY

echo "Packaged skill: $OUT_FILE"

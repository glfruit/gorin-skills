#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run-acceptance.sh <skill-dir> --command '<cmd>' --artifact <path> [--artifact <path> ...] [--integration <text>]

Example:
  run-acceptance.sh ./sigma \
    --command 'openclaw run /sigma "Python decorators"' \
    --artifact ~/.openclaw/workspace-daily-learner/sigma/python-decorators/session.md \
    --artifact ~/.openclaw/workspace-daily-learner/sigma/learner-profile.md \
    --integration 'daily-learner route'
EOF
}

[[ $# -ge 1 ]] || { usage; exit 1; }

SKILL_DIR="$1"
shift
SKILL_DIR="${SKILL_DIR%/}"
SKILL_MD="$SKILL_DIR/SKILL.md"
[[ -f "$SKILL_MD" ]] || { echo "SKILL.md not found: $SKILL_MD" >&2; exit 1; }

COMMAND=""
INTEGRATION=""
declare -a ARTIFACTS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --command)
      COMMAND="${2:-}"
      shift 2
      ;;
    --artifact)
      ARTIFACTS+=("${2:-}")
      shift 2
      ;;
    --integration)
      INTEGRATION="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 1
      ;;
  esac
done

TIMESTAMP="$(date '+%Y-%m-%dT%H:%M:%S%z')"
SKILL_NAME="$(basename "$SKILL_DIR")"
REPORT="$SKILL_DIR/acceptance-report.md"
TMP_LOG="$(mktemp)"
RESULT="failed"
DETAIL=""
declare -a RESOLVED_ARTIFACTS=()

if ! grep -qiE '^#+ .*Internal Acceptance' "$SKILL_MD"; then
  DETAIL="Missing Internal Acceptance section in SKILL.md"
elif [[ -z "$COMMAND" ]]; then
  RESULT="blocked"
  DETAIL="No acceptance command provided"
elif [[ ${#ARTIFACTS[@]} -eq 0 ]]; then
  RESULT="blocked"
  DETAIL="No expected artifacts provided"
else
  set +e
  bash -lc "$COMMAND" >"$TMP_LOG" 2>&1
  CMD_EXIT=$?
  set -e

  if [[ $CMD_EXIT -ne 0 ]]; then
    RESULT="failed"
    DETAIL="Acceptance command exited with code $CMD_EXIT"
  else
    missing=""
    for artifact in "${ARTIFACTS[@]}"; do
      expanded="$artifact"
      if [[ "$expanded" == ~* ]]; then
        expanded="$HOME${expanded:1}"
      fi
      if [[ ! -e "$expanded" ]]; then
        missing+="$expanded\n"
      else
        RESOLVED_ARTIFACTS+=("$expanded")
      fi
    done
    if [[ -n "$missing" ]]; then
      RESULT="failed"
      DETAIL="Missing expected artifacts"
    else
      RESULT="passed"
      DETAIL="Command succeeded and all expected artifacts exist"
    fi
  fi
fi

cat > "$REPORT" <<EOF
# Internal Acceptance Report

- Skill: $SKILL_NAME
- Run at: $TIMESTAMP
- Result: $RESULT
- Integration point: ${INTEGRATION:-not provided}
- Command: 
  \
  $COMMAND
- Expected artifacts:
$(for artifact in "${ARTIFACTS[@]}"; do echo "  - $artifact"; done)
- Resolved artifact paths:
$(for artifact in "${RESOLVED_ARTIFACTS[@]}"; do echo "  - $artifact"; done)
- Detail: $DETAIL

## Command Output

\
$(cat "$TMP_LOG" 2>/dev/null || true)
\
EOF

rm -f "$TMP_LOG"

echo "$RESULT"
echo "Acceptance report: $REPORT"

case "$RESULT" in
  passed) exit 0 ;;
  blocked) exit 2 ;;
  *) exit 1 ;;
esac

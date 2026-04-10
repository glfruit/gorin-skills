#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${HOME}/.openclaw/lib:${PYTHONPATH:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3.13 "${SCRIPT_DIR}/log_watchdog.py" "$@"

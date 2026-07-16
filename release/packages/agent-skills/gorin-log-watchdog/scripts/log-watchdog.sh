#!/usr/bin/env bash
set -euo pipefail
OPENCLAW_HOME="${OPENCLAW_HOME:-${HOME}/.openclaw}"
export PYTHONPATH="${OPENCLAW_HOME}/lib:${PYTHONPATH:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3.13 "${SCRIPT_DIR}/log_watchdog.py" "$@"

#!/usr/bin/env bash
# Thin wrapper — migrated to Python (auto_fix_auth.py)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "${SCRIPT_DIR}/auto_fix_auth.py" "$@"

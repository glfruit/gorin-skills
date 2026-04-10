#!/bin/bash
# Thin wrapper per SCRIPT_POLICY.md
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/zk.py" "$@"

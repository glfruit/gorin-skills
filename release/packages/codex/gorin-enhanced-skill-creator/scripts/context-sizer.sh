#!/usr/bin/env bash
# Thin wrapper for context_sizer.py
set -euo pipefail
exec python3 "$(dirname "$0")/context_sizer.py" "$@"

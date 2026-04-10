#!/bin/bash
# thin wrapper (SCRIPT_POLICY)
exec python3 "$(dirname "$0")/router.py" "$@"

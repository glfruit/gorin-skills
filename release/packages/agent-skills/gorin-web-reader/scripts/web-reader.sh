#!/usr/bin/env bash
set -euo pipefail
# web-reader.sh — web_reader.py 的薄包装
# 用法:
#   bash web-reader.sh <url> [--browser] [--profile <name>] [--save <path>] [--json] [--max-chars <n>] [--timeout <s>]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/web_reader.py" "$@"

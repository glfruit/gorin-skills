#!/usr/bin/env bash
set -euo pipefail

# maybe-open.sh - Optionally open a generated HTML file in the local browser
# Usage:
#   maybe-open.sh <html-file>

HTML_FILE="${1:-}"

if [[ -z "$HTML_FILE" ]]; then
  echo "❌ 用法: maybe-open.sh <html-file>"
  exit 1
fi

if [[ ! -f "$HTML_FILE" ]]; then
  echo "❌ 文件不存在: $HTML_FILE"
  exit 1
fi

if command -v open >/dev/null 2>&1; then
  open "$HTML_FILE"
  echo "✅ 已打开: $HTML_FILE"
else
  echo "ℹ️ 当前环境没有 open 命令，请手动打开: $HTML_FILE"
fi

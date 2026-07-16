#!/usr/bin/env bash
# fetch-sources.sh — 从 sources.json 提取所有来源 URL，用于批量抓取
# Usage: bash fetch-sources.sh [--category <cat>] [--format urls|search]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/../config"
SOURCES_FILE="$CONFIG_DIR/sources.json"

CATEGORY="${1:---all}"
FORMAT="urls"

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --category) CATEGORY="$2"; shift 2 ;;
    --format) FORMAT="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: fetch-sources.sh [--category <cat>] [--format urls|search]"
      echo "Categories: en-twitter, en-podcast, en-blog, zh-wechat, zh-other, all"
      exit 0
      ;;
    *) shift ;;
  esac
done

if [[ ! -f "$SOURCES_FILE" ]]; then
  echo "ERROR: sources.json not found at $SOURCES_FILE" >&2
  exit 1
fi

# Check for jq
if ! command -v jq &>/dev/null; then
  echo "ERROR: jq required but not found" >&2
  exit 1
fi

extract_urls() {
  local cat="$1"
  jq -r --arg cat "$cat" '
    if $cat == "all" then
      .categories | to_entries[] | .value.sources[]?
    else
      .categories[$cat].sources[]?
    end
    | if .url then .url
      elif .url_pattern then .url_pattern
      elif .search_query then .search_query
      else empty
      end
  ' "$SOURCES_FILE"
}

extract_urls "$CATEGORY"

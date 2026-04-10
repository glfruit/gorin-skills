#!/bin/bash
# Outline API helper — lightweight wrapper for agents
# Usage: outline-api <method> [args...]

set -euo pipefail

# Load config
CONFIG="$HOME/.openclaw/shared/outline-config.json"
if [ ! -f "$CONFIG" ]; then
  echo "ERROR: Config not found: $CONFIG" >&2
  exit 1
fi

URL=$(python3 -c "import json; print(json.load(open('$CONFIG'))['url'])")
KEY=$(python3 -c "import json; print(json.load(open('$CONFIG'))['api_key'])")

outline_call() {
  local method="$1"
  shift
  local body="{}"
  
  case "$method" in
    auth.info)
      body="{}"
      ;;
    documents.list)
      local limit="${1:-25}"; local offset="${2:-0}"
      body="{\"limit\":$limit,\"offset\":$offset}"
      ;;
    documents.info)
      local id="$1"
      body="{\"id\":\"$id\"}"
      ;;
    documents.create)
      local title="" text="" collection_id="" publish="true"
      while [[ $# -gt 0 ]]; do
        case "$1" in
          --collection) collection_id="$2"; shift 2 ;;
          --title) title="$2"; shift 2 ;;
          --text) text="$2"; shift 2 ;;
          --no-publish) publish="false"; shift ;;
          *) shift ;;
        esac
      done
      body="{\"title\":\"$title\",\"text\":\"$text\",\"collectionId\":\"$collection_id\",\"publish\":$publish}"
      ;;
    documents.update)
      local id="$1"; shift
      local new_title="" new_text=""
      while [[ $# -gt 0 ]]; do
        case "$1" in
          --title) new_title="$2"; shift 2 ;;
          --text) new_text="$2"; shift 2 ;;
          *) shift ;;
        esac
      done
      body="{\"id\":\"$id\""
      [ -n "$new_title" ] && body+=",\"title\":\"$new_title\""
      [ -n "$new_text" ] && body+=",\"text\":\"$new_text\""
      body+="}"
      ;;
    documents.search)
      local query="$1"; local limit="${2:-25}"
      body="{\"query\":\"$query\",\"limit\":$limit}"
      ;;
    documents.delete)
      local id="$1"
      body="{\"id\":\"$id\"}"
      ;;
    collections.list)
      body="{\"limit\":100}"
      ;;
    collections.documents)
      local id="$1"
      body="{\"id\":\"$id\",\"limit\":100}"
      ;;
    *)
      # Pass-through for unknown methods
      body="{}"
      ;;
  esac

  curl -s -X POST "$URL/api/$method" \
    -H "Authorization: Bearer $KEY" \
    -H "Content-Type: application/json" \
    -d "$body"
}

outline_call "$@"

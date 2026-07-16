#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 --name gorin-example --domain engineering --description 'Bounded skill description.'" >&2
  exit 2
fi

exec node "$ROOT/scripts/gorin-skills.mjs" scaffold --root "$ROOT" "$@"

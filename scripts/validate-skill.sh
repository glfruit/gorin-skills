#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if (( $# > 0 )); then
  printf 'warning: per-directory validation is retired; validating the manifest-driven repository instead\n' >&2
fi

exec node "$repo_root/scripts/gorin-skills.mjs" validate --root "$repo_root"

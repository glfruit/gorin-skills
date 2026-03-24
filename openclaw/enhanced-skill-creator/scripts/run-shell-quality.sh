#!/usr/bin/env bash
set -euo pipefail

# run-shell-quality.sh — Unified shell quality checks for a skill's shell scripts
# Usage: bash run-shell-quality.sh <skill-directory>
# Output: JSON summary with bash -n and optional shellcheck results

SKILL_DIR="${1:?Usage: bash run-shell-quality.sh <skill-directory>}"
SKILL_DIR="${SKILL_DIR%/}"

if [[ ! -d "$SKILL_DIR" ]]; then
  echo '{"error":"Skill directory does not exist"}' >&2
  exit 1
fi

python3 - "$SKILL_DIR" <<'PY'
import json
import shutil
import subprocess
import sys
from pathlib import Path

skill_dir = Path(sys.argv[1])
scripts_dir = skill_dir / 'scripts'
script_files = sorted(scripts_dir.glob('*.sh')) if scripts_dir.exists() else []
findings = []
pass_count = 0
skip_count = 0
fail_count = 0

for script in script_files:
    proc = subprocess.run(['bash', '-n', str(script)], capture_output=True, text=True)
    if proc.returncode == 0:
        pass_count += 1
    else:
        fail_count += 1
        findings.append({
            'id': f'syntax::{script.name}',
            'severity': 'fail',
            'category': 'scripts',
            'message': f'bash -n failed for {script.name}',
            'detail': (proc.stderr or proc.stdout).strip(),
            'suggestedFix': 'Fix shell syntax before relying on the script.'
        })

shellcheck = shutil.which('shellcheck')
if shellcheck:
    for script in script_files:
        proc = subprocess.run([shellcheck, '-S', 'warning', str(script)], capture_output=True, text=True)
        if proc.returncode == 0:
            pass_count += 1
        else:
            fail_count += 1
            findings.append({
                'id': f'shellcheck::{script.name}',
                'severity': 'warn',
                'category': 'scripts',
                'message': f'shellcheck reported issues for {script.name}',
                'detail': '\n'.join((proc.stdout or proc.stderr).splitlines()[:8]),
                'suggestedFix': 'Address shellcheck warnings or justify them explicitly.'
            })
else:
    skip_count += 1
    findings.append({
        'id': 'shellcheck::missing',
        'severity': 'skip',
        'category': 'scripts',
        'message': 'shellcheck is not installed',
        'detail': 'Install with: brew install shellcheck',
        'suggestedFix': 'Install shellcheck for stronger shell lint coverage.'
    })

result = 'PASS'
if any(f['severity'] == 'fail' for f in findings):
    result = 'FAIL'
elif any(f['severity'] == 'warn' for f in findings):
    result = 'WARN'

print(json.dumps({
    'tool': 'run-shell-quality',
    'version': '0.1',
    'skillPath': str(skill_dir),
    'result': result,
    'summary': {
        'scriptCount': len(script_files),
        'pass': pass_count,
        'fail': fail_count,
        'skip': skip_count,
    },
    'findings': findings,
    'artifacts': {
        'shellcheckInstalled': bool(shellcheck)
    }
}, ensure_ascii=False))
PY

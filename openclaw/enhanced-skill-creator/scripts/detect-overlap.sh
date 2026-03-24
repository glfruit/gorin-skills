#!/usr/bin/env bash
set -euo pipefail

# detect-overlap.sh — Collision / overlap checker for skills
# Usage: bash detect-overlap.sh <skill-directory> [skills-root]
# Output: JSON summary of potentially overlapping skills with weighted scoring

SKILL_DIR="${1:?Usage: bash detect-overlap.sh <skill-directory> [skills-root]}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_SKILLS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILLS_ROOT="${2:-$DEFAULT_SKILLS_ROOT}"

SKILL_DIR="${SKILL_DIR%/}"
SKILLS_ROOT="${SKILLS_ROOT%/}"

if [[ ! -d "$SKILL_DIR" ]]; then
  echo '{"error":"Skill directory does not exist"}' >&2
  exit 1
fi

if [[ ! -f "$SKILL_DIR/SKILL.md" ]]; then
  echo '{"error":"SKILL.md not found in skill directory"}' >&2
  exit 1
fi

python3 - "$SKILL_DIR" "$SKILLS_ROOT" <<'PY'
import json
import re
import sys
from pathlib import Path

skill_dir = Path(sys.argv[1])
skills_root = Path(sys.argv[2])

STOPWORDS = {
    'the','a','an','and','or','to','of','for','with','when','use','it','this','that','is','are','be','as','on','in','at','by','from',
    'skill','skills','agent','agents','user','users','using','used','tool','tools','task','tasks','request','requests','assistant',
    'do','not','only','into','than','then','their','them','your','you','can','will','should','about','needs','want','wants','need'
}
GENERIC_TOKENS = {
    'create','build','make','help','update','manage','process','analyze','generate','improve','workflow','content','real','patterns'
}
NEGATIVE_TRIGGER_PATTERNS = [r"don't use", r"do not use", r"not for", r"avoid when", r"except when"]
CATCH_ALL_PATTERNS = [r'any request', r'all tasks', r'everything', r'general-purpose', r'use for all', r'anything']


def extract_frontmatter(path: Path):
    text = path.read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        return {}, text
    parts = text.split('\n---\n', 1)
    if len(parts) < 2:
        return {}, text
    fm = parts[0].splitlines()[1:]
    body = parts[1]
    data = {}
    for line in fm:
        if ':' not in line:
            continue
        k, v = line.split(':', 1)
        data[k.strip()] = v.strip().strip('"')
    return data, body


def tokenize(*parts):
    text = ' '.join([p for p in parts if p])
    tokens = re.findall(r'[a-z0-9][a-z0-9-]+', text.lower())
    return {t for t in tokens if t not in STOPWORDS and len(t) >= 3}


def has_negative_trigger(desc: str) -> bool:
    return any(re.search(p, desc, re.I) for p in NEGATIVE_TRIGGER_PATTERNS)


def has_catch_all(desc: str) -> bool:
    return any(re.search(p, desc, re.I) for p in CATCH_ALL_PATTERNS) or bool(re.search(r'(^|[^\w])\*($|[^\w])|\.\*', desc))


def load_skill(path: Path):
    fm, body = extract_frontmatter(path / 'SKILL.md')
    name = fm.get('name', path.name)
    desc = fm.get('description', '')
    tokens = tokenize(name, desc)
    specific_tokens = {t for t in tokens if t not in GENERIC_TOKENS}
    return {
        'path': str(path),
        'name': name,
        'description': desc,
        'tokens': tokens,
        'specific_tokens': specific_tokens,
        'has_negative': has_negative_trigger(desc),
        'has_catch_all': has_catch_all(desc),
        'body': body,
    }


def overlap_score(current, other):
    shared_all = current['tokens'] & other['tokens']
    shared_specific = current['specific_tokens'] & other['specific_tokens']
    shared_generic = {t for t in shared_all if t in GENERIC_TOKENS}

    union_specific = current['specific_tokens'] | other['specific_tokens']
    base = (len(shared_specific) / max(len(union_specific), 1)) if union_specific else 0.0
    generic_penalty = min(len(shared_generic) * 0.015, 0.06)
    risk_bonus = 0.0
    reasons = []

    if shared_specific:
        reasons.append(f"shared specific tokens: {', '.join(sorted(list(shared_specific))[:6])}")
    if shared_generic:
        reasons.append(f"shared generic tokens: {', '.join(sorted(list(shared_generic))[:6])}")

    if current['has_catch_all'] or other['has_catch_all']:
        risk_bonus += 0.08
        reasons.append('catch-all phrasing detected')
    if not current['has_negative']:
        risk_bonus += 0.04
        reasons.append('current skill lacks explicit negative triggers')
    if not other['has_negative']:
        risk_bonus += 0.02
        reasons.append('other skill lacks explicit negative triggers')
    if len(shared_specific) >= 3:
        risk_bonus += 0.05
    elif len(shared_specific) >= 2:
        risk_bonus += 0.03

    final = max(base - generic_penalty + risk_bonus, 0.0)
    return round(final, 3), sorted(shared_specific), sorted(shared_generic), reasons


current = load_skill(skill_dir)
results = []
all_skill_dirs = [p for p in skills_root.iterdir() if p.is_dir() and (p / 'SKILL.md').exists()]

for child in sorted(all_skill_dirs):
    if child.resolve() == skill_dir.resolve():
        continue
    other = load_skill(child)
    score, shared_specific, shared_generic, reasons = overlap_score(current, other)
    if score < 0.06 and len(shared_specific) < 1:
        continue
    risk = 'low'
    if score >= 0.28 or len(shared_specific) >= 4:
        risk = 'high'
    elif score >= 0.14 or len(shared_specific) >= 2:
        risk = 'medium'

    suggestion = None
    if risk in {'medium', 'high'}:
        suggestion = 'Add narrower domain nouns and explicit negative triggers to reduce collision risk.'

    results.append({
        'name': other['name'],
        'path': other['path'],
        'score': score,
        'risk': risk,
        'sharedSpecificTokens': shared_specific[:10],
        'sharedGenericTokens': shared_generic[:10],
        'reasons': reasons[:5],
        'description': other['description'],
        'suggestedFix': suggestion,
    })

results.sort(key=lambda x: (-x['score'], x['name']))
high = sum(1 for r in results if r['risk'] == 'high')
medium = sum(1 for r in results if r['risk'] == 'medium')

result = 'PASS'
if high > 0:
    result = 'FAIL'
elif medium > 0:
    result = 'WARN'

summary = {
    'tool': 'detect-overlap',
    'version': '0.2',
    'skillPath': str(skill_dir),
    'result': result,
    'summary': {
        'checkedAgainst': len(all_skill_dirs) - 1,
        'highRisk': high,
        'mediumRisk': medium,
        'lowRisk': sum(1 for r in results if r['risk'] == 'low'),
    },
    'findings': [
        {
            'id': f"collision::{r['name']}",
            'severity': 'fail' if r['risk'] == 'high' else ('warn' if r['risk'] == 'medium' else 'info'),
            'category': 'collision',
            'message': f"Potential overlap with {r['name']} (risk={r['risk']}, score={r['score']})",
            'detail': '; '.join(r['reasons']),
            'suggestedFix': r['suggestedFix'] or ''
        }
        for r in results[:10]
    ],
    'artifacts': {
        'overlaps': results[:10]
    }
}
print(json.dumps(summary, ensure_ascii=False))
PY

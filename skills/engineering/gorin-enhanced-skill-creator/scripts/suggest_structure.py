#!/usr/bin/env python3
"""suggest_structure.py — Basic structure suggestion engine for skills."""
import json
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print('{"error": "Usage: suggest_structure.py <skill-directory>"}', file=sys.stderr)
        sys.exit(1)

    skill_dir = Path(sys.argv[1].rstrip("/"))
    skill_md = skill_dir / "SKILL.md"

    if not skill_dir.is_dir():
        print('{"error": "Skill directory does not exist"}', file=sys.stderr)
        sys.exit(1)
    if not skill_md.is_file():
        print('{"error": "SKILL.md not found in skill directory"}', file=sys.stderr)
        sys.exit(1)

    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()

    suggestions = {'assets': [], 'scripts': [], 'references': []}

    # Asset suggestions: long fenced blocks or explicit output templates
    fenced_blocks = re.findall(r'```(json|yaml|yml|toml|xml|html|markdown|md)?\n(.*?)```', text, re.S | re.I)
    for lang, body in fenced_blocks:
        body_lines = len(body.strip().splitlines()) if body.strip() else 0
        if body_lines >= 12:
            ext = (lang.lower() if lang else 'txt').replace('markdown', 'md')
            if ext == 'yml':
                ext = 'yaml'
            suggestions['assets'].append({
                'reason': f'Found long {ext} fenced block ({body_lines} lines) that may be a reusable template',
                'suggestedPath': f'assets/template.{ext}'
            })
            break

    for idx, line in enumerate(lines, 1):
        lower = line.lower()
        if any(phrase in lower for phrase in ['output json', 'output structure', 'template', 'format as', 'report format', 'config template']):
            suggestions['assets'].append({
                'reason': f'Line {idx} suggests a repeatable output/config template',
                'suggestedPath': 'assets/output-template.md'
            })
            break

    # Script suggestions
    script_patterns = [
        ('parse', 'scripts/parse-input.sh'),
        ('extract', 'scripts/extract-data.sh'),
        ('validate', 'scripts/validate-input.sh'),
        ('convert', 'scripts/convert-format.sh'),
        ('transform', 'scripts/transform-data.sh'),
        ('grep', 'scripts/run-query.sh'),
        ('jq', 'scripts/run-query.sh'),
    ]
    seen_script_paths = set()
    for idx, line in enumerate(lines, 1):
        lower = line.lower()
        for needle, path in script_patterns:
            if needle in lower and path not in seen_script_paths:
                suggestions['scripts'].append({
                    'reason': f'Line {idx} mentions deterministic/repetitive operation: {needle}',
                    'suggestedPath': path
                })
                seen_script_paths.add(path)
                if len(seen_script_paths) >= 3:
                    break
        if len(seen_script_paths) >= 3:
            break

    # Reference suggestions
    if len(lines) > 220:
        suggestions['references'].append({
            'reason': f'SKILL.md is relatively long ({len(lines)} lines); dense rules may belong in references/',
            'suggestedPath': 'references/detailed-rules.md'
        })

    if text.count('|') >= 20:
        suggestions['references'].append({
            'reason': 'Detected multiple table rows; comparison matrices or taxonomies may fit better in references/',
            'suggestedPath': 'references/decision-tables.md'
        })

    for idx, line in enumerate(lines, 1):
        lower = line.lower()
        if any(phrase in lower for phrase in ['anti-pattern', 'pitfall', 'failure pattern', 'quality checklist', 'quality standard']):
            suggestions['references'].append({
                'reason': f'Line {idx} suggests detailed guidance/checklists that may be worth isolating',
                'suggestedPath': 'references/quality-guide.md'
            })
            break

    # De-duplicate by suggestedPath
    for key in suggestions:
        seen = set()
        deduped = []
        for item in suggestions[key]:
            path = item['suggestedPath']
            if path in seen:
                continue
            seen.add(path)
            deduped.append(item)
        suggestions[key] = deduped

    print(json.dumps({
        'skillPath': str(skill_md.parent),
        'lineCount': len(lines),
        'suggestions': suggestions
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

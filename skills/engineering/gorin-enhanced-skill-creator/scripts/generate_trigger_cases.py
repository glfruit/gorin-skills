#!/usr/bin/env python3
"""Generate trigger test case candidates for a skill.

Reads SKILL.md frontmatter and generates candidate positive/negative
test cases. Outputs a JSON template for human review.

Usage:
    python3 generate_trigger_cases.py <skill-dir> [--json] [--count N]
"""

import argparse
import json
import re
import sys
from pathlib import Path


def parse_frontmatter(skill_md: str) -> dict:
    """Extract YAML frontmatter from SKILL.md."""
    if not skill_md.startswith("---"):
        return {}
    end = skill_md.find("---", 3)
    if end == -1:
        return {}
    fm = skill_md[3:end].strip()
    result = {}
    for line in fm.split("\n"):
        line = line.strip()
        m = re.match(r'^(\w[\w-]*)\s*:\s*(.+)$', line)
        if m:
            key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
            result[key] = val
        m = re.match(r'^-\s+(.+)$', line)
        if m and result.get("_last_key"):
            lst = result.setdefault(result["_last_key"], [])
            if isinstance(lst, list):
                lst.append(m.group(1).strip().strip('"').strip("'"))
    result.pop("_last_key", None)
    return result


def extract_negative_section(skill_md: str) -> str:
    """Extract 'When NOT to Use' section."""
    negative = ""
    in_section = False
    for line in skill_md.split("\n"):
        if re.match(r'^##\s*(when\s+not|don\'t|negative)', line, re.I):
            in_section = True
            continue
        if in_section and line.startswith("##"):
            break
        if in_section:
            negative += line + "\n"
    return negative


def generate_cases(frontmatter: dict, negative_text: str, count: int = 3) -> list[dict]:
    """Generate candidate test cases from frontmatter."""
    name = frontmatter.get("name", "unknown")
    desc = frontmatter.get("description", "")
    triggers = frontmatter.get("triggers", [])
    if isinstance(triggers, str):
        triggers = [triggers]

    cases = []

    # Positive cases: exact trigger phrases
    for trigger in triggers[:count]:
        cases.append({
            "prompt": f"please {trigger}",
            "should_trigger": True,
            "note": f"exact trigger: '{trigger}'",
        })

    # Positive cases: natural language paraphrase of description
    desc_verbs = re.findall(r'\b(create|build|make|design|generate|write|review|search|analyze|convert|improve|refactor)\b', desc, re.I)
    desc_nouns = re.findall(r'\b(skill|report|note|email|image|document|code|workflow|pipeline)\b', desc, re.I)

    if desc_verbs and desc_nouns:
        for verb in desc_verbs[:2]:
            for noun in desc_nouns[:2]:
                cases.append({
                    "prompt": f"帮我{verb}一个{noun}",
                    "should_trigger": True,
                    "note": f"Chinese natural language paraphrase",
                })
                cases.append({
                    "prompt": f"I need to {verb} a {noun}",
                    "should_trigger": True,
                    "note": f"English natural language paraphrase",
                })

    # Negative cases: from "When NOT to Use" section
    neg_items = re.findall(r'^\s*[-*]\s+(.+)$', negative_text, re.MULTILINE)
    for item in neg_items[:count]:
        # Convert negative guidance into a test prompt
        prompt = re.sub(r'^(for|when|don\'t|do not)\s+', '', item, flags=re.I).strip()
        if prompt:
            cases.append({
                "prompt": prompt,
                "should_trigger": False,
                "note": f"from When NOT to Use: {item.strip()}",
            })

    # Generic negative cases
    generic_negatives = [
        f"edit the {name} configuration file",
        f"show me the current {name} settings",
        f"delete {name}",
    ]
    for neg in generic_negatives[:count]:
        cases.append({
            "prompt": neg,
            "should_trigger": False,
            "note": "generic operation (not creation/use)",
        })

    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--count", type=int, default=3,
                        help="Number of cases per category")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).resolve()
    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.exists():
        print(f"Error: No SKILL.md in {skill_dir}", file=sys.stderr)
        sys.exit(2)

    skill_md = skill_md_path.read_text(encoding="utf-8")
    fm = parse_frontmatter(skill_md)
    neg = extract_negative_section(skill_md)
    cases = generate_cases(fm, neg, args.count)

    output = {
        "skill": fm.get("name", skill_dir.name),
        "generated_cases": len(cases),
        "note": "AUTO-GENERATED — review and adjust before using for evaluation",
        "cases": cases,
    }

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"# Generated Trigger Cases for: {output['skill']}")
        print(f"# Total: {output['generated_cases']} cases")
        print(f"# ⚠️  Review before using — these are candidates, not validated cases")
        print()
        for i, c in enumerate(cases, 1):
            expect = "✅ TRIGGER" if c["should_trigger"] else "❌ SKIP"
            print(f"{i:2d}. [{expect}] {c['prompt']}")
            if c.get("note"):
                print(f"    Note: {c['note']}")


if __name__ == "__main__":
    main()

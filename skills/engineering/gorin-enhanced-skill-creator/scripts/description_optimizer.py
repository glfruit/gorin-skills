#!/usr/bin/env python3
"""Description Optimizer — checks skill description for routing efficiency.

Inspired by SkillReducer (arXiv:2603.29919) findings:
- 26.4% of skills lack descriptions entirely
- Overly verbose descriptions waste tokens in every routing call
- Description should contain ONLY routing-relevant content (domain, task type, keywords)
- Non-routing content (features, examples, philosophy) should live in body/references

Usage:
    python3 description_optimizer.py <skill-dir> [--json] [--strict]

Exit codes:
    0 — description is well-optimized
    1 — issues found (strict mode)
    2 — error (invalid dir, missing SKILL.md)
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ── Token estimation (same heuristic as context_sizer.py) ─────

CHARS_PER_TOKEN_EN = 4.0
CHARS_PER_TOKEN_CJK = 1.5

# ── Thresholds ───────────────────────────────────────────────

# Optimal description length in tokens (from SkillReducer empirical data)
IDEAL_MIN_TOKENS = 10
IDEAL_MAX_TOKENS = 50
WARN_MAX_TOKENS = 80

# ── Non-routing content patterns ──────────────────────────────

# These indicate content that helps humans but NOT the router
NON_ROUTING_PATTERNS = [
    # Usage examples in description
    (re.compile(r'\b(example|e\.g\.|for instance|such as)\b.*', re.I),
     "Usage example detected — move to body or references/"),
    # Feature lists (enumerated capabilities)
    (re.compile(r'^\s*[-•]\s+(supports?|provides?|includes?|offers?)\b', re.MULTILINE | re.I),
     "Feature list detected — keep only domain keywords"),
    # Philosophical/aspirational language
    (re.compile(r'\b(best practice|principled|robust|comprehensive|powerful)\b', re.I),
     "Aspirational language — not useful for routing"),
    # Redundant trigger words (already in triggers field)
    (re.compile(r'\b(when.*ask|when.*say|when.*request|triggered by|use when)\b', re.I),
     "Trigger description — duplicates triggers field"),
    # Full sentences explaining "why" (router only needs "what")
    (re.compile(r'\b(designed to|aims to|built for|purpose is to)\b', re.I),
     "Purpose statement — not routing-relevant"),
]


def estimate_tokens(text: str) -> int:
    """Estimate token count using the same heuristic as context_sizer.py."""
    if not text:
        return 0
    cjk_count = len(re.findall(
        r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', text
    ))
    total_chars = len(text)
    non_cjk_chars = total_chars - cjk_count
    return int(non_cjk_chars / CHARS_PER_TOKEN_EN + cjk_count / CHARS_PER_TOKEN_CJK)


def extract_frontmatter(path: Path):
    """Extract frontmatter dict and body from SKILL.md."""
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


def check_description(skill_dir: Path) -> dict:
    """Run all description quality checks."""
    skill_md = skill_dir / "SKILL.md"
    fm, body = extract_frontmatter(skill_md)
    name = fm.get('name', skill_dir.name)
    desc = fm.get('description', '')
    triggers = fm.get('triggers', '')

    issues = []
    suggestions = []

    # ── Check 1: Missing description ──
    if not desc.strip():
        issues.append({
            "severity": "fail",
            "check": "missing_description",
            "message": "No description found — router cannot match this skill",
            "suggestion": "Add a concise description (10-50 tokens) focused on domain and task type",
        })
        # Early return — no point checking quality of empty desc
        return {
            "tool": "description-optimizer",
            "skill": name,
            "path": str(skill_dir),
            "description": desc,
            "tokens": 0,
            "result": "FAIL",
            "issues": issues,
            "suggestions": ["Add a description to frontmatter"],
            "stats": {
                "hasDescription": False,
                "tokenCount": 0,
                "nonRoutingIssues": 0,
            },
        }

    # ── Check 2: Token count ──
    tokens = estimate_tokens(desc)

    if tokens < IDEAL_MIN_TOKENS:
        issues.append({
            "severity": "warn",
            "check": "too_short",
            "message": f"Description too short ({tokens} tokens) — may not provide enough routing signal",
            "suggestion": f"Expand to at least {IDEAL_MIN_TOKENS} tokens with domain-specific keywords",
        })
    elif tokens > WARN_MAX_TOKENS:
        issues.append({
            "severity": "warn" if tokens <= 120 else "fail",
            "check": "too_long",
            "message": f"Description verbose ({tokens} tokens, ideal {IDEAL_MIN_TOKENS}-{IDEAL_MAX_TOKENS}) — wastes routing tokens",
            "suggestion": "Remove non-routing content; keep only domain + task type keywords",
        })

    # ── Check 3: Non-routing content ──
    non_routing_count = 0
    for pattern, msg in NON_ROUTING_PATTERNS:
        matches = pattern.findall(desc)
        if matches:
            non_routing_count += len(matches)
            issues.append({
                "severity": "info",
                "check": "non_routing_content",
                "message": f"{msg} ({len(matches)} match(es))",
                "suggestion": "Remove from description; this content belongs in SKILL.md body",
            })

    # ── Check 4: Description vs body overlap ──
    # If >50% of description words also appear in the first 5 lines of body,
    # the description is probably repeating the body
    if body.strip():
        desc_words = set(re.findall(r'\b\w{3,}\b', desc.lower()))
        body_head = '\n'.join(body.strip().split('\n')[:5])
        body_words = set(re.findall(r'\b\w{3,}\b', body_head.lower()))
        if desc_words and body_words:
            overlap = desc_words & body_words
            overlap_ratio = len(overlap) / len(desc_words)
            if overlap_ratio > 0.6:
                issues.append({
                    "severity": "info",
                    "check": "body_overlap",
                    "message": f"Description has {overlap_ratio:.0%} word overlap with body heading — likely redundant",
                    "suggestion": "Keep description as a terse summary distinct from body content",
                })

    # ── Check 5: Trigger keywords coverage ──
    # Description should contain at least one keyword from triggers (if triggers exist)
    if triggers:
        trigger_words = set(re.findall(r'[\w-]+', triggers.lower()))
        trigger_content = [t for t in trigger_words if len(t) >= 3]
        if trigger_content:
            desc_lower = desc.lower()
            covered = [t for t in trigger_content if t in desc_lower]
            if not covered and len(trigger_content) >= 2:
                issues.append({
                    "severity": "warn",
                    "check": "trigger_mismatch",
                    "message": "No trigger keywords found in description — routing signal may be weak",
                    "suggestion": f"Include at least one keyword from triggers: {', '.join(trigger_content[:5])}",
                })

    # ── Determine result ──
    has_fail = any(i["severity"] == "fail" for i in issues)
    has_warn = any(i["severity"] == "warn" for i in issues)
    result = "PASS" if not has_fail and not has_warn else ("FAIL" if has_fail else "WARN")

    return {
        "tool": "description-optimizer",
        "skill": name,
        "path": str(skill_dir),
        "description": desc,
        "tokens": tokens,
        "result": result,
        "issues": issues,
        "suggestions": [i["suggestion"] for i in issues if i.get("suggestion")],
        "stats": {
            "hasDescription": True,
            "tokenCount": tokens,
            "idealRange": [IDEAL_MIN_TOKENS, IDEAL_MAX_TOKENS],
            "nonRoutingIssues": non_routing_count,
        },
    }


def format_human(report: dict) -> str:
    """Format report as human-readable text."""
    lines = []
    status_icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}[report["result"]]
    lines.append(f"{status_icon} Description Optimizer: {report['skill']}")
    lines.append(f"   Tokens: {report['tokens']} (ideal: {report['stats']['idealRange'][0]}-{report['stats']['idealRange'][1]})")

    if not report["stats"]["hasDescription"]:
        lines.append("   ❌ No description found")
        return "\n".join(lines)

    lines.append(f"   Description: \"{report['description'][:100]}{'...' if len(report['description']) > 100 else ''}\"")

    if report["issues"]:
        lines.append("")
        sev_icons = {"fail": "❌", "warn": "⚠️", "info": "💡"}
        for issue in report["issues"]:
            lines.append(f"   {sev_icons[issue['severity']]} {issue['message']}")
            if issue.get("suggestion"):
                lines.append(f"      → {issue['suggestion']}")
    else:
        lines.append("   ✅ Description is well-optimized for routing")

    if report["suggestions"]:
        lines.append("")
        lines.append("   Suggestions:")
        for s in report["suggestions"]:
            lines.append(f"      • {s}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Description quality optimizer for agent skills")
    parser.add_argument("skill_dir", help="Path to the skill directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--strict", action="store_true",
                        help="Exit with code 1 if issues found")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).resolve()
    if not skill_dir.is_dir():
        print(f"Error: {skill_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    if not (skill_dir / "SKILL.md").exists():
        print(f"Error: No SKILL.md found in {skill_dir}", file=sys.stderr)
        sys.exit(2)

    report = check_description(skill_dir)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_human(report))

    if args.strict and report["result"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()

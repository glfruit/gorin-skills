#!/usr/bin/env python3
"""Context Budget Sizer for Agent Skills.

Scans a skill directory, estimates token usage per file, calculates
quality density, and reports whether the skill is within budget.

Usage:
    python3 context_sizer.py <skill-dir> [--json] [--strict]

Exit codes:
    0 — within budget
    1 — over budget (strict mode only)
    2 — error (invalid dir, missing SKILL.md)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ── Token estimation ──────────────────────────────────────────

# Approximate chars per token for different content types.
# CJK characters are ~1.5 chars/token; ASCII prose ~4 chars/token.
# We use a blended average since most skills mix both.

CHARS_PER_TOKEN_EN = 4.0
CHARS_PER_TOKEN_CJK = 1.5


def estimate_tokens(text: str) -> int:
    """Estimate token count from text using a simple heuristic."""
    if not text:
        return 0

    cjk_count = len(re.findall(
        r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', text
    ))
    total_chars = len(text)
    non_cjk_chars = total_chars - cjk_count

    tokens_en = non_cjk_chars / CHARS_PER_TOKEN_EN
    tokens_cjk = cjk_count / CHARS_PER_TOKEN_CJK

    return int(tokens_en + tokens_cjk)


# ── Cost estimation ────────────────────────────────────────────

# Per-1K-token pricing (USD) for common models (approximate 2025 rates)
MODEL_PRICING = {
    "gpt-4o":          {"input": 2.50, "output": 10.00},
    "gpt-4o-mini":      {"input": 0.15, "output": 0.60},
    "claude-sonnet-4":  {"input": 3.00, "output": 15.00},
    "claude-haiku":     {"input": 0.80, "output": 4.00},
    "glm-4":           {"input": 0.14, "output": 0.14},
    "deepseek-v3":     {"input": 0.27, "output": 1.10},
}
DEFAULT_MODEL = "gpt-4o"


def estimate_cost(tokens: int, model: str = DEFAULT_MODEL) -> dict:
    """Estimate per-invocation cost for loading skill content into context.

    Args:
        tokens: Number of context tokens injected.
        model: Model identifier key from MODEL_PRICING.

    Returns:
        Dict with per_call and daily (100 calls) cost estimates.
    """
    pricing = MODEL_PRICING.get(model, MODEL_PRICING[DEFAULT_MODEL])
    per_1k = pricing["input"]  # skill content is input-side
    per_call = (tokens / 1000) * per_1k
    return {
        "model": model,
        "tokens": tokens,
        "per_call_usd": round(per_call, 4),
        "daily_100_calls_usd": round(per_call * 100, 2),
        "monthly_1000_calls_usd": round(per_call * 1000, 2),
    }


# ── Budget thresholds ─────────────────────────────────────────

DEFAULT_BUDGETS = {
    "SKILL.md": 2000,
    "scripts/": 2000,
    "references/": 4000,
    "assets/": 1000,
    "config/": 500,
    "evals/": 500,
    "total": 8000,
}


def get_budgets(skill_dir: Path) -> dict:
    """Load custom budgets from skill's .skill-meta.json if present, else defaults."""
    meta_path = skill_dir / ".skill-meta.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            custom = meta.get("context_budget", {})
            if custom:
                merged = dict(DEFAULT_BUDGETS)
                merged.update(custom)
                return merged
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_BUDGETS)


# ── File scanning ─────────────────────────────────────────────

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".archive", ".DS_Store"}
SKIP_EXTS = {".pyc", ".pyo", ".DS_Store", ".git", ".png", ".jpg", ".jpeg",
             ".gif", ".webp", ".ico", ".woff", ".woff2", ".ttf", ".eot"}


def scan_directory(skill_dir: Path) -> list[dict]:
    """Walk skill directory, return per-file token estimates."""
    files = []

    for root, dirs, filenames in os.walk(skill_dir):
        # Prune skipped dirs in-place
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for fname in filenames:
            fpath = Path(root) / fname
            ext = fpath.suffix.lower()
            if ext in SKIP_EXTS:
                continue

            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            rel_path = fpath.relative_to(skill_dir)
            tokens = estimate_tokens(text)
            chars = len(text)
            lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)

            files.append({
                "path": str(rel_path),
                "tokens": tokens,
                "chars": chars,
                "lines": lines,
                "category": _categorize(rel_path),
            })

    return sorted(files, key=lambda f: f["tokens"], reverse=True)


def _categorize(rel_path: Path) -> str:
    """Map file path to budget category."""
    parts = rel_path.parts
    if parts[0] == "SKILL.md":
        return "SKILL.md"
    if parts[0] in ("scripts",):
        return "scripts/"
    if parts[0] in ("references",):
        return "references/"
    if parts[0] in ("assets",):
        return "assets/"
    if parts[0] in ("config",):
        return "config/"
    if parts[0] in ("evals",):
        return "evals/"
    return "other"


# ── Quality density ───────────────────────────────────────────

# Patterns that indicate low-value / filler content
FILLER_PATTERNS = [
    re.compile(r'^\s*#+\s*(step\s+\d+|todo|placeholder|tbd|fixme|xxx)\b', re.I),
    re.compile(r'^\s*$', re.MULTILINE),                    # blank lines
    re.compile(r'^\s*```\s*$', re.MULTILINE),              # empty code fences
    re.compile(r'^\s*(//|#)\s*(note|warning|todo):', re.I), # comment noise
    re.compile(r'```[\s]*```', re.DOTALL),                  # empty code blocks
]


def calc_quality_density(text: str) -> float:
    """Estimate ratio of useful content to total content.

    Returns 0.0-1.0 where 1.0 means all content is high-value.
    """
    if not text.strip():
        return 0.0

    total_chars = len(text)
    if total_chars == 0:
        return 0.0

    # Count filler characters
    filler_chars = 0
    for pattern in FILLER_PATTERNS:
        for match in pattern.finditer(text):
            filler_chars += len(match.group(0))

    # Deduct excessive whitespace (more than 2 consecutive blank lines)
    excessive_blanks = re.findall(r'\n{3,}', text)
    for blank_run in excessive_blanks:
        filler_chars += len(blank_run) - 2  # allow 2 newlines (one blank line)

    useful_chars = max(total_chars - filler_chars, 0)
    return round(useful_chars / total_chars, 3)


# ── Report generation ─────────────────────────────────────────

def build_report(skill_dir: Path, files: list[dict], budgets: dict, cost_model: str = None) -> dict:
    """Build the full context budget report."""
    # Per-category aggregation
    categories: dict[str, dict] = {}
    for cat_key in list(budgets.keys()):
        categories[cat_key] = {"tokens": 0, "files": 0, "budget": budgets[cat_key]}

    for f in files:
        cat = f["category"]
        if cat in categories:
            categories[cat]["tokens"] += f["tokens"]
            categories[cat]["files"] += 1
        else:
            if "other" not in categories:
                categories["other"] = {"tokens": 0, "files": 0, "budget": None}
            categories["other"]["tokens"] += f["tokens"]
            categories["other"]["files"] += 1

    total_tokens = sum(f["tokens"] for f in files)

    # Overall quality density
    all_text = ""
    for f in files:
        fpath = skill_dir / f["path"]
        try:
            all_text += fpath.read_text(encoding="utf-8", errors="replace") + "\n"
        except OSError:
            pass

    density = calc_quality_density(all_text)

    # Per-file density for SKILL.md specifically
    skill_md_density = None
    for f in files:
        if f["category"] == "SKILL.md":
            fpath = skill_dir / f["path"]
            try:
                md_text = fpath.read_text(encoding="utf-8", errors="replace")
                skill_md_density = calc_quality_density(md_text)
            except OSError:
                pass
            break

    # Exclude categories with budget=0 from total (they run as subprocesses)
    excluded_tokens = sum(
        info["tokens"] for cat, info in categories.items()
        if info.get("budget") == 0
    )
    counted_tokens = total_tokens - excluded_tokens

    # Cost estimation (for context-loaded tokens only)
    cost_estimate = estimate_cost(counted_tokens, model=cost_model or DEFAULT_MODEL)

    # Violations
    violations = []
    for cat, info in categories.items():
        # budget=0 means "excluded from context" (subprocess), not "zero budget"
        if info.get("budget") is not None and info["budget"] > 0 and info["tokens"] > info["budget"]:
            violations.append({
                "category": cat,
                "tokens": info["tokens"],
                "budget": info["budget"],
                "over_by": info["tokens"] - info["budget"],
            })

    if counted_tokens > budgets.get("total", 999999):
        violations.append({
            "category": "total",
            "tokens": counted_tokens,
            "budget": budgets["total"],
            "over_by": counted_tokens - budgets["total"],
        })

    # Grade
    if not violations and density >= 0.7:
        grade = "A"
    elif not violations:
        grade = "B"
    elif len(violations) <= 2 and density >= 0.5:
        grade = "C"
    else:
        grade = "D"

    return {
        "skill": skill_dir.name,
        "total_tokens": total_tokens,
        "counted_tokens": counted_tokens,
        "excluded_tokens": excluded_tokens,
        "total_budget": budgets["total"],
        "quality_density": density,
        "skill_md_density": skill_md_density,
        "grade": grade,
        "within_budget": len(violations) == 0,
        "cost_estimate": cost_estimate,
        "categories": categories,
        "violations": violations,
        "top_files": [
            {"path": f["path"], "tokens": f["tokens"], "lines": f["lines"]}
            for f in files[:10]
        ],
    }


# ── Output formatting ─────────────────────────────────────────

def format_human(report: dict) -> str:
    """Format report as human-readable text."""
    lines = []
    lines.append(f"📊 Context Budget Report: {report['skill']}")
    excl = report.get('excluded_tokens', 0)
    counted = report.get('counted_tokens', report['total_tokens'])
    lines.append(f"   Context: {counted}/{report['total_budget']} tokens "
                 f"({'✅ within budget' if report['within_budget'] else '⚠️  OVER BUDGET'})")
    if excl > 0:
        lines.append(f"   (Excluded subprocess scripts: {excl} tokens)")
    lines.append(f"   Quality density: {report['quality_density']:.1%}")
    if report['skill_md_density'] is not None:
        lines.append(f"   SKILL.md density: {report['skill_md_density']:.1%}")
    lines.append(f"   Grade: {report['grade']}")
    cost = report.get('cost_estimate', {})
    if cost:
        lines.append(f"   💰 Est. cost per invocation: ${cost['per_call_usd']:.4f} "
                     f"(100 calls/day = ${cost['daily_100_calls_usd']:.2f}/day, "
                     f"model: {cost['model']})")
    lines.append("")

    # Category breakdown
    lines.append("   Category Breakdown:")
    for cat in ["SKILL.md", "scripts/", "references/", "assets/", "config/", "evals/", "other"]:
        info = report["categories"].get(cat)
        if info is None:
            continue
        if info["budget"] == 0:
            lines.append(f"      {cat:<14s} {info['tokens']:>5d} tokens (excluded from context) "
                         f"({info['files']} files)")
        elif info["budget"] is not None and info["tokens"] > info["budget"]:
            budget_str = str(info["budget"])
            lines.append(f"   ⚠️ {cat:<14s} {info['tokens']:>5d}/{budget_str:>5s} tokens "
                         f"({info['files']} files)")
        else:
            budget_str = str(info["budget"]) if info["budget"] is not None else "∞"
            lines.append(f"      {cat:<14s} {info['tokens']:>5d}/{budget_str:>5s} tokens "
                         f"({info['files']} files)")
    lines.append("")

    # Violations
    if report["violations"]:
        lines.append("   ⚠️  Budget Violations:")
        for v in report["violations"]:
            lines.append(f"      - {v['category']}: {v['tokens']} tokens "
                         f"(over by {v['over_by']})")
        lines.append("")

    # Top files
    if report["top_files"]:
        lines.append("   Top Files by Token Count:")
        for f in report["top_files"][:5]:
            lines.append(f"      {f['tokens']:>5d} tokens  {f['lines']:>4d} lines  {f['path']}")

    # Suggestions
    lines.append("")
    if not report["within_budget"]:
        lines.append("   💡 Suggestions:")
        if report["categories"].get("SKILL.md", {}).get("tokens", 0) > DEFAULT_BUDGETS["SKILL.md"]:
            lines.append("      - SKILL.md over budget: move detailed rules to references/")
        if report["categories"].get("references/", {}).get("tokens", 0) > DEFAULT_BUDGETS["references/"]:
            lines.append("      - references/ over budget: split into multiple focused docs")
        lines.append("      - Consider progressive disclosure: SKILL.md → references/ → scripts/")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Context budget sizer for agent skills")
    parser.add_argument("skill_dir", help="Path to the skill directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--strict", action="store_true",
                        help="Exit with code 1 if over budget")
    parser.add_argument("--budgets-only", action="store_true",
                        help="Only show the budget thresholds, don't scan")
    parser.add_argument("--model", default=None,
                        help=f"Model for cost estimation (default: {DEFAULT_MODEL}). "
                             f"Options: {', '.join(MODEL_PRICING.keys())}")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).resolve()
    if not skill_dir.is_dir():
        print(f"Error: {skill_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    # Skill must have SKILL.md
    if not (skill_dir / "SKILL.md").exists():
        print(f"Error: No SKILL.md found in {skill_dir}", file=sys.stderr)
        sys.exit(2)

    budgets = get_budgets(skill_dir)

    if args.budgets_only:
        if args.json:
            print(json.dumps(budgets, indent=2))
        else:
            print("Budget thresholds:")
            for cat, budget in budgets.items():
                print(f"  {cat:<14s} {budget:>5d} tokens")
        return

    files = scan_directory(skill_dir)
    report = build_report(skill_dir, files, budgets, cost_model=args.model if args.model else None)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_human(report))

    if args.strict and not report["within_budget"]:
        sys.exit(1)


if __name__ == "__main__":
    main()

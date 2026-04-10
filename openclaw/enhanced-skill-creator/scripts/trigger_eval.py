#!/usr/bin/env python3
"""Trigger Quality Evaluator for Agent Skills.

Evaluates whether a skill's frontmatter description and triggers correctly
match intended use cases. Uses rule-based matching (no external LLM needed).

Usage:
    python3 trigger_eval.py <skill-dir> [--cases <file>] [--json]

Exit codes:
    0 — all cases pass
    1 — failures found
    2 — error (invalid dir, missing SKILL.md, no test cases)
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ── Frontmatter parsing ───────────────────────────────────────

def parse_frontmatter(skill_md: str) -> dict:
    """Extract YAML frontmatter from SKILL.md content."""
    if not skill_md.startswith("---"):
        return {}

    end = skill_md.find("---", 3)
    if end == -1:
        return {}

    fm_text = skill_md[3:end].strip()
    result = {}

    for line in fm_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Simple key-value parsing (handles quoted strings)
        m = re.match(r'^(\w[\w-]*)\s*:\s*(.+)$', line)
        if m:
            key = m.group(1)
            val = m.group(2).strip().strip('"').strip("'")
            result[key] = val

        # Handle list items (triggers)
        m = re.match(r'^-\s+(.+)$', line)
        if m and result.get("_last_key"):
            lst = result.setdefault(result["_last_key"], [])
            if isinstance(lst, list):
                lst.append(m.group(1).strip().strip('"').strip("'"))

    result.pop("_last_key", None)
    return result


# ── Trigger matching ──────────────────────────────────────────

def normalize(text: str) -> str:
    """Normalize text for matching."""
    text = text.lower().strip()
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    return text


def extract_keywords(description: str) -> set[str]:
    """Extract significant keywords from description."""
    # Remove common stop words
    stop_words = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "shall", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below", "between", "and", "but", "or",
        "not", "no", "nor", "so", "yet", "both", "either", "neither", "each",
        "every", "all", "any", "few", "more", "most", "other", "some", "such",
        "than", "too", "very", "just", "about", "also", "then", "when", "how",
        "what", "which", "who", "whom", "this", "that", "these", "those",
        "it", "its", "use", "using", "used", "make", "help", "helps",
        "user", "agent", "task", "want", "needs", "need",
    }
    words = set(re.findall(r'[a-z]{2,}', normalize(description)))
    return words - stop_words


def match_trigger(prompt: str, frontmatter: dict) -> tuple[bool, str]:
    """Determine if a prompt should trigger this skill.

    Returns (should_trigger, reason).
    """
    prompt_norm = normalize(prompt)
    desc = normalize(frontmatter.get("description", ""))
    triggers = frontmatter.get("triggers", [])
    if isinstance(triggers, str):
        triggers = [triggers]

    # Check for explicit trigger phrase match
    for trigger in triggers:
        trigger_norm = normalize(trigger)
        if trigger_norm in prompt_norm:
            return True, f"exact trigger match: '{trigger}'"

    # Check for bilingual action+target pattern
    # Chinese: 创建/新建/设计 + skill/技能/技巧 → should trigger
    # Allow optional 的/一个/一个新 between action and target
    action_zh = re.findall(r'(?:创建|新建|设计|构建|开发|制作|编写|生成)(?:一个|一个新|一个新)?(?:的)?(?:skill|技能|技巧)', prompt_norm)
    if not action_zh:
        # Also try: action + ... + skill (with intervening words)
        if re.search(r'(?:创建|新建|设计|构建|开发|制作|编写|生成).{0,10}?(?:skill|技能|技巧)', prompt_norm):
            action_zh = True
    if action_zh:
        return True, f"Chinese action+target match: {action_zh}"

    # English partial: any trigger word + "skill"
    trigger_actions = {"create", "build", "make", "design", "new"}
    prompt_words_set = set(re.findall(r'[a-z]{2,}', prompt_norm))
    if "skill" in prompt_words_set and trigger_actions & prompt_words_set:
        return True, f"English action+skill match: {trigger_actions & prompt_words_set} + skill"

    # Check if any trigger word appears (even without 'skill' next to it)
    for trigger in triggers:
        trigger_word = trigger.split()[0]  # e.g., 'create', 'build'
        if trigger_word in prompt_words_set and "skill" in prompt_words_set:
            return True, f"trigger word '{trigger_word}' + 'skill' in prompt"

    # Check for keyword overlap with description
    desc_keywords = extract_keywords(desc)
    prompt_words = set(re.findall(r'[a-z]{2,}', prompt_norm))

    # Match on significant keyword overlap (≥40% of description keywords)
    overlap = desc_keywords & prompt_words
    if len(desc_keywords) > 0 and len(overlap) >= max(2, len(desc_keywords) * 0.4):
        return True, f"keyword overlap ({len(overlap)}/{len(desc_keywords)}): {overlap}"

    # Check for Chinese character overlap in description
    desc_cjk = set(re.findall(r'[\u4e00-\u9fff]{2,}', desc))
    prompt_cjk = set(re.findall(r'[\u4e00-\u9fff]{2,}', prompt_norm))
    cjk_overlap = desc_cjk & prompt_cjk
    if len(desc_cjk) > 0 and len(cjk_overlap) >= max(1, len(desc_cjk) * 0.3):
        return True, f"CJK keyword overlap ({len(cjk_overlap)}/{len(desc_cjk)}): {cjk_overlap}"

    return False, "no trigger or keyword match"


def check_negative_trigger(prompt: str, skill_md: str) -> bool:
    """Check if the prompt matches a negative trigger pattern in the skill.

    Returns True if the prompt should be BLOCKED (negative trigger matched).
    """
    # Look for "When NOT to Use" or "Don't use" sections
    negative_section = ""
    in_negative = False
    for line in skill_md.split("\n"):
        if re.match(r'^##\s*(when\s+not|don\'t|negative|anti)', line, re.I):
            in_negative = True
            continue
        if in_negative and line.startswith("##"):
            break
        if in_negative:
            negative_section += line + "\n"

    if not negative_section:
        return False

    # Check if prompt matches negative patterns
    prompt_norm = normalize(prompt)
    negative_patterns = re.findall(r'[\u4e00-\u9fff]{2,}|[a-z]{3,}', normalize(negative_section))

    # Only block if strong overlap with negative section
    prompt_words = set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-z]{3,}', prompt_norm))
    neg_set = set(negative_patterns)
    overlap = prompt_words & neg_set

    # Require ≥3 keyword matches with negative section to block
    # AND the overlap must be a significant portion of the negative keywords
    if len(overlap) >= 3 and len(overlap) >= len(neg_set) * 0.3:
        return True

    return False


# ── Test case handling ─────────────────────────────────────────

def load_cases(skill_dir: Path, cases_file: str = None, split: str = None) -> list[dict]:
    """Load test cases from file or auto-discover from skill directory.

    Args:
        split: Optional filter - 'train', 'dev', or 'holdout'. Returns all if None.
    """
    if cases_file:
        path = Path(cases_file)
        if not path.exists():
            print(f"Error: cases file not found: {cases_file}", file=sys.stderr)
            sys.exit(2)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cases = data.get("cases", [])
    else:
        # Auto-discover
        candidates = [
            skill_dir / "evals" / "trigger_cases.json",
            skill_dir / "tests" / "trigger_cases.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cases = data.get("cases", [])
                break
        else:
            return []

    # Filter by split if requested
    if split:
        cases = [c for c in cases if c.get("split") == split]

    return cases


# ── Evaluation ─────────────────────────────────────────────────

def evaluate_cases(
    cases: list[dict], frontmatter: dict, skill_md: str
) -> dict:
    """Run all test cases and produce evaluation report."""
    results = []
    tp = fp = fn = tn = 0

    for case in cases:
        prompt = case["prompt"]
        expected = case["should_trigger"]
        note = case.get("note", "")

        triggered, reason = match_trigger(prompt, frontmatter)

        # Check negative triggers (can override positive match)
        blocked = check_negative_trigger(prompt, skill_md)
        if blocked and triggered:
            triggered = False
            reason += " [blocked by negative trigger]"

        correct = triggered == expected

        if expected and triggered:
            tp += 1
        elif not expected and triggered:
            fp += 1
        elif expected and not triggered:
            fn += 1
        else:
            tn += 1

        results.append({
            "prompt": prompt,
            "expected": expected,
            "actual": triggered,
            "correct": correct,
            "reason": reason,
            "note": note,
        })

    total = len(cases)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "total": total,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "all_correct": fp == 0 and fn == 0,
        "results": results,
    }


# ── Output formatting ─────────────────────────────────────────

def format_human(report: dict) -> str:
    """Format report as human-readable text."""
    lines = []
    status = "✅ ALL PASS" if report["all_correct"] else "❌ FAILURES FOUND"
    lines.append(f"🎯 Trigger Eval Report: {status}")
    lines.append(f"   Cases: {report['total']}  "
                 f"TP={report['tp']} FP={report['fp']} "
                 f"FN={report['fn']} TN={report['tn']}")
    lines.append(f"   Precision: {report['precision']:.1%}  "
                 f"Recall: {report['recall']:.1%}  "
                 f"F1: {report['f1']:.1%}")
    lines.append("")

    for r in report["results"]:
        icon = "✅" if r["correct"] else "❌"
        expect_str = "TRIGGER" if r["expected"] else "SKIP"
        actual_str = "TRIGGER" if r["actual"] else "SKIP"
        lines.append(f"   {icon} [{expect_str}] → [{actual_str}] {r['prompt']}")
        if not r["correct"]:
            lines.append(f"      Reason: {r['reason']}")
            if r["note"]:
                lines.append(f"      Note: {r['note']}")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Trigger quality evaluator")
    parser.add_argument("skill_dir", help="Path to the skill directory")
    parser.add_argument("--cases", help="Path to test cases JSON file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--split", choices=["train", "dev", "holdout"],
                        help="Evaluate only on a specific split")
    parser.add_argument("--regression", action="store_true",
                        help="Compare against regression baseline")
    parser.add_argument("--save-baseline", action="store_true",
                        help="Save results as regression baseline")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).resolve()
    if not skill_dir.is_dir():
        print(f"Error: {skill_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.exists():
        print(f"Error: No SKILL.md found in {skill_dir}", file=sys.stderr)
        sys.exit(2)

    skill_md = skill_md_path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(skill_md)

    cases = load_cases(skill_dir, args.cases, split=args.split)
    if not cases:
        split_msg = f" (split={args.split})" if args.split else ""
        print(f"No test cases found{split_msg}. Create evals/trigger_cases.json or use --cases.",
              file=sys.stderr)
        sys.exit(2)

    report = evaluate_cases(cases, frontmatter, skill_md)
    report["split"] = args.split or "all"

    # Regression check
    if args.regression:
        baseline_path = skill_dir / "evals" / "regression-baseline.json"
        if baseline_path.exists():
            with open(baseline_path, "r", encoding="utf-8") as f:
                baseline = json.load(f)
            baseline_f1 = baseline.get("f1", 0)
            delta = report["f1"] - baseline_f1
            report["regression"] = {
                "baseline_f1": baseline_f1,
                "current_f1": report["f1"],
                "delta": round(delta, 3),
                "regressed": delta < -0.05,
            }
        else:
            report["regression"] = {"error": "No baseline found at evals/regression-baseline.json"}

    # Save baseline
    if args.save_baseline:
        baseline_dir = skill_dir / "evals"
        baseline_dir.mkdir(exist_ok=True)
        baseline_path = baseline_dir / "regression-baseline.json"
        baseline_data = {
            "f1": report["f1"],
            "precision": report["precision"],
            "recall": report["recall"],
            "total": report["total"],
            "tp": report["tp"], "fp": report["fp"],
            "fn": report["fn"], "tn": report["tn"],
        }
        with open(baseline_path, "w", encoding="utf-8") as f:
            json.dump(baseline_data, f, indent=2, ensure_ascii=False)
        report["baseline_saved"] = str(baseline_path)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_human(report))
        # Show regression info
        if "regression" in report:
            reg = report["regression"]
            if "error" in reg:
                print(f"\n   ⚠️ Regression: {reg['error']}")
            else:
                delta_str = f"{reg['delta']:+.1%}"
                icon = "✅" if not reg["regressed"] else "⚠️ REGRESSED"
                print(f"\n   {icon} Regression: baseline F1={reg['baseline_f1']:.1%} → current {reg['current_f1']:.1%} ({delta_str})")
        if "baseline_saved" in report:
            print(f"\n   📁 Baseline saved to: {report['baseline_saved']}")

    if not report["all_correct"]:
        sys.exit(1)


if __name__ == "__main__":
    main()

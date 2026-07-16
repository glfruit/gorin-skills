#!/usr/bin/env python3
"""Governance Health Check for Agent Skills.

Evaluates a skill's lifecycle governance: metadata completeness,
readiness evidence, review cadence, and known issues.

Usage:
    python3 governance_check.py <skill-dir> [--json] [--require-manifest]

Exit codes:
    0 — governance OK
    1 — governance issues found (strict mode)
    2 — error
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ── Scoring ────────────────────────────────────────────────────

# Each check returns (passed: bool, points: int, max_points: int, message: str)

def check_skill_md_exists(skill_dir: Path) -> tuple:
    if (skill_dir / "SKILL.md").exists():
        return True, 5, 5, "SKILL.md exists"
    return False, 0, 5, "SKILL.md missing"


def check_frontmatter(skill_dir: Path) -> tuple:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return False, 0, 10, "SKILL.md not found"

    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False, 0, 10, "No YAML frontmatter"

    end = content.find("---", 3)
    if end == -1:
        return False, 0, 10, "Frontmatter not closed"

    fm = content[3:end]
    checks = {
        "name": bool(re.search(r'^name\s*:', fm, re.M)),
        "description": bool(re.search(r'^description\s*:', fm, re.M)),
    }

    score = sum(checks.values()) * 5
    missing = [k for k, v in checks.items() if not v]
    if missing:
        return False, score, 10, f"Missing frontmatter fields: {', '.join(missing)}"
    return True, 10, 10, "Frontmatter complete (name + description)"


def check_skill_meta(skill_dir: Path) -> tuple:
    meta_path = skill_dir / ".skill-meta.json"
    if not meta_path.exists():
        return False, 0, 15, ".skill-meta.json missing (create with origin, version, description)"

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except json.JSONDecodeError as e:
        return False, 0, 15, f".skill-meta.json invalid JSON: {e}"

    required = ["origin", "version"]
    optional = ["description", "dependencies", "env_vars", "governance"]

    score = 0
    for field in required:
        if field in meta and meta[field]:
            score += 4
    for field in optional:
        if field in meta and meta[field]:
            score += 2

    score = min(score, 15)
    missing_req = [f for f in required if f not in meta or not meta[f]]

    if missing_req:
        return False, score, 15, f"Missing required fields: {', '.join(missing_req)}"
    return True, score, 15, ".skill-meta.json present with required fields"


def check_governance_meta(skill_dir: Path) -> tuple:
    meta_path = skill_dir / ".skill-meta.json"
    if not meta_path.exists():
        return False, 0, 15, "No .skill-meta.json"

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except json.JSONDecodeError:
        return False, 0, 15, "Invalid .skill-meta.json"

    gov = meta.get("governance", {})
    if not gov:
        return False, 5, 15, "No governance section in .skill-meta.json"

    score = 0
    fields = {
        "lifecycle": 3,
        "maturity_score": 3,
        "last_reviewed": 3,
        "review_cadence": 3,
        "promotion_evidence": 3,
    }

    present = []
    for field, points in fields.items():
        if field in gov and gov[field]:
            score += points
            present.append(field)

    missing = [f for f in fields if f not in present]
    if missing:
        return False, score, 15, f"Governance present but missing: {', '.join(missing)}"
    return True, 15, 15, "Governance metadata complete"


def check_manifest(skill_dir: Path, require: bool = False) -> tuple:
    manifest_path = skill_dir / "manifest.json"
    if not manifest_path.exists():
        if require:
            return False, 0, 10, "manifest.json required but missing"
        return True, 5, 10, "manifest.json optional, not present (OK for non-library skills)"

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return False, 0, 10, f"manifest.json invalid: {e}"

    required = ["name", "version"]
    score = sum(5 for f in required if f in manifest and manifest[f])
    missing = [f for f in required if f not in manifest or not manifest[f]]

    if missing:
        return False, score, 10, f"manifest.json missing: {', '.join(missing)}"
    return True, 10, 10, "manifest.json valid"


def check_readiness_evidence(skill_dir: Path) -> tuple:
    """Check if SKILL.md documents readiness level and has evidence."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return False, 0, 10, "No SKILL.md"

    content = skill_md.read_text(encoding="utf-8")

    # Check for readiness level mention
    readiness_found = bool(re.search(
        r'(scaffold|mvp|production-ready|integrated)', content, re.I
    ))

    # Check for Internal Acceptance section
    acceptance_found = bool(re.search(
        r'^##\s*(internal\s+acceptance|acceptance)', content, re.I | re.M
    ))

    # Check for Delivery Contract
    contract_found = bool(re.search(
        r'^##\s*(delivery\s+contract)', content, re.I | re.M
    ))

    score = 0
    if readiness_found:
        score += 3
    if acceptance_found:
        score += 4
    if contract_found:
        score += 3

    missing = []
    if not readiness_found:
        missing.append("readiness level")
    if not acceptance_found:
        missing.append("Internal Acceptance section")
    if not contract_found:
        missing.append("Delivery Contract section")

    if missing:
        return False, score, 10, f"Missing: {', '.join(missing)}"
    return True, 10, 10, "Readiness evidence complete"


def check_review_cadence(skill_dir: Path) -> tuple:
    """Check if governance metadata has current review date."""
    meta_path = skill_dir / ".skill-meta.json"
    if not meta_path.exists():
        return True, 5, 10, "No governance (OK for scaffold skills)"

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except json.JSONDecodeError:
        return True, 5, 10, "Cannot check review cadence"

    gov = meta.get("governance", {})
    last_reviewed = gov.get("last_reviewed", "")
    cadence = gov.get("review_cadence", "quarterly")

    if not last_reviewed:
        return False, 3, 10, "No last_reviewed date in governance"

    # Check if review is current
    try:
        review_date = datetime.fromisoformat(last_reviewed.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False, 3, 10, f"Invalid last_reviewed date: {last_reviewed}"

    now = datetime.now(timezone.utc)
    # Ensure review_date is timezone-aware
    if review_date.tzinfo is None:
        review_date = review_date.replace(tzinfo=timezone.utc)
    cadence_days = {"monthly": 35, "quarterly": 100, "biannually": 200, "annually": 400}
    max_days = cadence_days.get(cadence, 100)
    days_since = (now - review_date).days

    if days_since > max_days:
        return False, 5, 10, f"Review overdue ({days_since} days, cadence: {cadence})"
    return True, 10, 10, f"Review current ({days_since} days ago, cadence: {cadence})"


def check_structure(skill_dir: Path) -> tuple:
    """Basic structure check: has reasonable directory layout."""
    expected = []
    optional = ["scripts", "references", "assets", "config"]

    has_any = False
    for d in optional:
        if (skill_dir / d).is_dir():
            has_any = True

    if not has_any and not (skill_dir / "SKILL.md").exists():
        return False, 0, 5, "No structure: only SKILL.md with no supporting dirs"

    return True, 5, 5, "Has supporting directory structure"


# ── Report ─────────────────────────────────────────────────────

def run_checks(skill_dir: Path, require_manifest: bool = False) -> dict:
    """Run all governance checks and produce report."""
    checks = [
        ("SKILL.md exists", lambda: check_skill_md_exists(skill_dir)),
        ("Frontmatter", lambda: check_frontmatter(skill_dir)),
        ("Skill metadata", lambda: check_skill_meta(skill_dir)),
        ("Governance section", lambda: check_governance_meta(skill_dir)),
        ("Manifest", lambda: check_manifest(skill_dir, require_manifest)),
        ("Readiness evidence", lambda: check_readiness_evidence(skill_dir)),
        ("Review cadence", lambda: check_review_cadence(skill_dir)),
        ("Directory structure", lambda: check_structure(skill_dir)),
    ]

    results = []
    total_score = 0
    max_score = 0

    for name, check_fn in checks:
        passed, score, max_pts, message = check_fn()
        results.append({
            "check": name,
            "passed": passed,
            "score": score,
            "max": max_pts,
            "message": message,
        })
        total_score += score
        max_score += max_pts

    # Normalize to 0-100
    gov_score = round(total_score / max_score * 100) if max_score > 0 else 0

    # Grade
    if gov_score >= 90:
        grade = "A"
    elif gov_score >= 75:
        grade = "B"
    elif gov_score >= 60:
        grade = "C"
    else:
        grade = "D"

    return {
        "skill": skill_dir.name,
        "governance_score": gov_score,
        "grade": grade,
        "total_points": total_score,
        "max_points": max_score,
        "checks": results,
        "recommendations": _get_recommendations(results, gov_score),
    }


def _get_recommendations(results: list[dict], score: int) -> list[str]:
    """Generate actionable recommendations from failed checks."""
    recs = []
    for r in results:
        if r["passed"]:
            continue
        name = r["check"]
        msg = r["message"]

        if name == "Skill metadata":
            recs.append("Create .skill-meta.json with origin, version, description fields")
        elif name == "Governance section":
            recs.append("Add governance section to .skill-meta.json (lifecycle, maturity_score, last_reviewed, review_cadence)")
        elif name == "Manifest":
            recs.append("Create manifest.json with name, version (required for library skills)")
        elif name == "Readiness evidence":
            recs.append("Add readiness level + Internal Acceptance + Delivery Contract to SKILL.md")
        elif name == "Review cadence":
            recs.append("Update last_reviewed date in governance metadata")
        elif name == "Frontmatter":
            recs.append(f"Fix SKILL.md frontmatter: {msg}")

    return recs


def format_human(report: dict) -> str:
    lines = []
    lines.append(f"🏛️  Governance Report: {report['skill']}")
    lines.append(f"   Score: {report['governance_score']}/100 (Grade {report['grade']})")
    lines.append(f"   Points: {report['total_points']}/{report['max_points']}")
    lines.append("")

    for r in report["checks"]:
        icon = "✅" if r["passed"] else "❌"
        lines.append(f"   {icon} [{r['score']:2d}/{r['max']:2d}] {r['check']}: {r['message']}")

    if report["recommendations"]:
        lines.append("")
        lines.append("   💡 Recommendations:")
        for rec in report["recommendations"]:
            lines.append(f"      - {rec}")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Governance health check for agent skills")
    parser.add_argument("skill_dir", help="Path to the skill directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--require-manifest", action="store_true",
                        help="Require manifest.json (for library/governed skills)")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).resolve()
    if not skill_dir.is_dir():
        print(f"Error: {skill_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    report = run_checks(skill_dir, args.require_manifest)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_human(report))

    if report["governance_score"] < 60:
        sys.exit(1)


if __name__ == "__main__":
    main()

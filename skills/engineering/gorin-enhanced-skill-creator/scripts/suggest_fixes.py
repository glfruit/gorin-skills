#!/usr/bin/env python3
"""suggest_fixes.py — Generate low-risk auto-fix suggestions for common skill issues."""
import json
import re
import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print('{"error": "Usage: suggest_fixes.py <skill-directory>"}', file=sys.stderr)
        sys.exit(1)

    skill_dir = Path(sys.argv[1].rstrip("/"))
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.is_file():
        print('{"error": "SKILL.md not found"}', file=sys.stderr)
        sys.exit(1)

    script_dir = Path(__file__).resolve().parent

    # Run validator
    validation = {}
    try:
        proc = subprocess.run(
            [sys.executable, str(script_dir / "validate_skill.py"), str(skill_dir)],
            capture_output=True, text=True, timeout=30,
        )
        if proc.stdout.strip():
            validation = json.loads(proc.stdout)
    except Exception:
        pass

    # Run error handler generator
    err_draft = ""
    try:
        proc = subprocess.run(
            [sys.executable, str(script_dir / "generate_error_handling.py"), str(skill_dir)],
            capture_output=True, text=True, timeout=30,
        )
        err_draft = proc.stdout or ""
    except Exception:
        pass

    text = skill_md.read_text(encoding="utf-8")
    checks = {c.get("name"): c for c in validation.get("checks", [])}
    fixes = []

    if checks.get("routing_safety_metadata", {}).get("status") == "fail":
        fixes.append({
            "id": "fix-routing-safety-description",
            "type": "rewrite-frontmatter-description",
            "severity": "fail",
            "message": "Rewrite description to remove catch-all phrasing and add explicit negative trigger.",
            "draft": "Rewrite the description as: '<capability>. Use when ... Don't use it for ...'. Remove wildcard or general-purpose phrasing."
        })

    if checks.get("negative_triggers_section", {}).get("status") == "fail":
        fixes.append({
            "id": "add-when-not-to-use",
            "type": "insert-section",
            "severity": "warn",
            "message": "Add a When NOT to Use section with explicit negative triggers.",
            "draft": "## When NOT to Use\n\n- Don't use it for {adjacent but out-of-scope case}.\n- Don't use it when {simpler tool/process} is sufficient."
        })

    if checks.get("workflow_numbering", {}).get("status") == "fail":
        fixes.append({
            "id": "add-numbered-workflow",
            "type": "rewrite-workflow",
            "severity": "warn",
            "message": "Replace prose-only workflow with numbered steps.",
            "draft": "## Core Workflow\n\n1. Validate prerequisites.\n2. Read the required references or assets.\n3. Execute the main deterministic or procedural step.\n4. Validate output and report failures explicitly."
        })

    if checks.get("error_handling_section", {}).get("status") == "fail":
        fixes.append({
            "id": "add-error-handling",
            "type": "insert-section",
            "severity": "warn",
            "message": "Add an Error Handling section.",
            "draft": err_draft or "## Error Handling\n\n### Missing Prerequisites\n- Stop and report the missing prerequisite.\n"
        })

    if checks.get("progressive_disclosure_signals", {}).get("status") == "fail":
        fixes.append({
            "id": "add-resource-links",
            "type": "insert-guidance",
            "severity": "info",
            "message": "Add references to references/, assets/, or scripts/ where dense details or templates belong.",
            "draft": "Add resource references such as `references/guide.md`, `assets/template.md`, or `scripts/helper.sh` where appropriate."
        })

    # Non-blocking quality hints
    if "## Error Handling" in text and "## When NOT to Use" in text and re.search(r"(^|\n)1\. ", text):
        fixes.append({
            "id": "no-op-quality-state",
            "type": "info",
            "severity": "info",
            "message": "Core low-risk quality structures are already present.",
            "draft": ""
        })

    result = "PASS" if not [f for f in fixes if f["severity"] in ("fail", "warn")] else "WARN"
    print(json.dumps({
        "tool": "suggest-fixes",
        "version": "0.1",
        "skillPath": str(skill_md.parent),
        "result": result,
        "summary": {
            "fixCount": len(fixes),
            "actionable": len([f for f in fixes if f["severity"] in ("fail", "warn")])
        },
        "findings": fixes,
        "artifacts": {
            "draft": err_draft or None
        }
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

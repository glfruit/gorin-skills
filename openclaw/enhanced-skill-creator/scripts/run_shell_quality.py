#!/usr/bin/env python3
"""run_shell_quality.py — Unified shell quality checks for a skill's shell scripts."""
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print('{"error": "Usage: run_shell_quality.py <skill-directory>"}', file=sys.stderr)
        sys.exit(1)

    skill_dir = Path(sys.argv[1].rstrip("/"))

    if not skill_dir.is_dir():
        print('{"error": "Skill directory does not exist"}', file=sys.stderr)
        sys.exit(1)

    scripts_dir = skill_dir / "scripts"
    script_files = sorted(scripts_dir.glob("*.sh")) if scripts_dir.exists() else []
    findings = []
    pass_count = 0
    skip_count = 0
    fail_count = 0

    for script in script_files:
        proc = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
        if proc.returncode == 0:
            pass_count += 1
        else:
            fail_count += 1
            findings.append({
                "id": f"syntax::{script.name}",
                "severity": "fail",
                "category": "scripts",
                "message": f"bash -n failed for {script.name}",
                "detail": (proc.stderr or proc.stdout).strip(),
                "suggestedFix": "Fix shell syntax before relying on the script."
            })

    shellcheck = shutil.which("shellcheck")
    if shellcheck:
        for script in script_files:
            proc = subprocess.run([shellcheck, "-S", "warning", str(script)], capture_output=True, text=True)
            if proc.returncode == 0:
                pass_count += 1
            else:
                fail_count += 1
                findings.append({
                    "id": f"shellcheck::{script.name}",
                    "severity": "warn",
                    "category": "scripts",
                    "message": f"shellcheck reported issues for {script.name}",
                    "detail": "\n".join((proc.stdout or proc.stderr).splitlines()[:8]),
                    "suggestedFix": "Address shellcheck warnings or justify them explicitly."
                })
    else:
        skip_count += 1
        findings.append({
            "id": "shellcheck::missing",
            "severity": "skip",
            "category": "scripts",
            "message": "shellcheck is not installed",
            "detail": "Install with: brew install shellcheck",
            "suggestedFix": "Install shellcheck for stronger shell lint coverage."
        })

    result = "PASS"
    if any(f["severity"] == "fail" for f in findings):
        result = "FAIL"
    elif any(f["severity"] == "warn" for f in findings):
        result = "WARN"

    print(json.dumps({
        "tool": "run-shell-quality",
        "version": "0.1",
        "skillPath": str(skill_dir),
        "result": result,
        "summary": {
            "scriptCount": len(script_files),
            "pass": pass_count,
            "fail": fail_count,
            "skip": skip_count,
        },
        "findings": findings,
        "artifacts": {
            "shellcheckInstalled": bool(shellcheck)
        }
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

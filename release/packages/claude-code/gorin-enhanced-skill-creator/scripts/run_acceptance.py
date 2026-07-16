#!/usr/bin/env python3
"""run_acceptance.py — Run acceptance tests for a skill."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Run acceptance tests for a skill.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Example:
  run_acceptance.py ./sigma \\
    --command 'openclaw run /sigma "Python decorators"' \\
    --artifact ~/.openclaw/workspace-daily-learner/sigma/python-decorators/session.md \\
    --artifact ~/.openclaw/workspace-daily-learner/sigma/learner-profile.md \\
    --integration 'daily-learner route'
""",
    )
    parser.add_argument("skill_dir", help="Skill directory path")
    parser.add_argument("--command", default="", help="Acceptance command to run")
    parser.add_argument("--artifact", action="append", default=[], dest="artifacts", help="Expected artifact paths (repeatable)")
    parser.add_argument("--integration", default="", help="Integration point description")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).resolve()
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.is_file():
        print(f"SKILL.md not found: {skill_md}", file=sys.stderr)
        sys.exit(1)

    script_dir = Path(__file__).resolve().parent
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
    skill_name = skill_dir.name
    report_path = skill_dir / "acceptance-report.md"

    text = skill_md.read_text(encoding="utf-8")
    result = "failed"
    detail = ""
    resolved_artifacts = []

    if not re.search(r"^#+ .*Internal Acceptance", text, re.I):
        detail = "Missing Internal Acceptance section in SKILL.md"
    elif not args.command:
        result = "blocked"
        detail = "No acceptance command provided"
    elif not args.artifacts:
        result = "blocked"
        detail = "No expected artifacts provided"
    else:
        # Run the acceptance command
        cmd_output = ""
        try:
            proc = subprocess.run(
                ["bash", "-lc", args.command],
                capture_output=True, text=True, timeout=120,
            )
            cmd_output = proc.stdout or ""
            if proc.stderr:
                cmd_output += "\n" + proc.stderr
            if proc.returncode != 0:
                result = "failed"
                detail = f"Acceptance command exited with code {proc.returncode}"
            else:
                missing = []
                for artifact in args.artifacts:
                    expanded = os.path.expanduser(artifact)
                    if not os.path.exists(expanded):
                        missing.append(expanded)
                    else:
                        resolved_artifacts.append(expanded)
                if missing:
                    result = "failed"
                    detail = "Missing expected artifacts"
                else:
                    result = "passed"
                    detail = "Command succeeded and all expected artifacts exist"
        except subprocess.TimeoutExpired:
            result = "failed"
            detail = "Acceptance command timed out"
        except Exception as e:
            result = "failed"
            detail = str(e)

    # Write report
    report_lines = [
        "# Internal Acceptance Report",
        "",
        f"- Skill: {skill_name}",
        f"- Run at: {timestamp}",
        f"- Result: {result}",
        f"- Integration point: {args.integration or 'not provided'}",
        "- Command:",
        f"  ```",
        f"  {args.command}",
        f"  ```",
        "- Expected artifacts:",
    ]
    for artifact in args.artifacts:
        report_lines.append(f"  - {artifact}")
    report_lines.append("- Resolved artifact paths:")
    for artifact in resolved_artifacts:
        report_lines.append(f"  - {artifact}")
    report_lines.extend([
        f"- Detail: {detail}",
        "",
        "## Command Output",
        "",
        "```",
        cmd_output.strip(),
        "```",
        "",
    ])
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(result)
    print(f"Acceptance report: {report_path}")

    if result == "passed":
        sys.exit(0)
    elif result == "blocked":
        sys.exit(2)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""package_skill.py — Package a skill directory into a .skill zip file."""
import re
import subprocess
import sys
import zipfile
from pathlib import Path


def main():
    if len(sys.argv) < 1:
        print("Usage: package_skill.py <skill-directory> [output-dir] [--acceptance-report <path>]", file=sys.stderr)
        sys.exit(1)

    args = sys.argv[1:]
    if not args:
        print("Usage: package_skill.py <skill-directory> [output-dir] [--acceptance-report <path>]", file=sys.stderr)
        sys.exit(1)

    skill_dir = Path(args[0].rstrip("/"))
    args = args[1:]

    out_dir = Path.cwd()
    acceptance_report = ""

    # Parse optional positional output-dir then flags
    while args:
        if args[0].startswith("--"):
            break
        out_dir = Path(args[0])
        args = args[1:]
        break

    i = 0
    while i < len(args):
        if args[i] == "--acceptance-report":
            if i + 1 >= len(args):
                print("--acceptance-report requires a path", file=sys.stderr)
                sys.exit(1)
            acceptance_report = args[i + 1]
            i += 2
        else:
            print(f"Unknown arg: {args[i]}", file=sys.stderr)
            sys.exit(1)

    script_dir = Path(__file__).resolve().parent

    # Quick validate
    try:
        proc = subprocess.run(
            [sys.executable, str(script_dir / "quick_validate.py"), str(skill_dir)],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Quick validate failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Full validate (suppress output)
    try:
        subprocess.run(
            [sys.executable, str(script_dir / "validate_skill.py"), str(skill_dir)],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        pass

    skill_name = skill_dir.name

    if not acceptance_report:
        acceptance_report = skill_dir / "acceptance-report.md"

    acceptance_path = Path(acceptance_report)
    if not acceptance_path.is_file():
        print(f"Packaging blocked: missing acceptance report ({acceptance_report})", file=sys.stderr)
        sys.exit(1)

    report_text = acceptance_path.read_text(encoding="utf-8")
    if not re.search(r"(?:^|\s)Result:\s+passed", report_text):
        print(f"Packaging blocked: acceptance report is not passing ({acceptance_report})", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{skill_name}.skill"

    exclude = {"acceptance-report.md", ".DS_Store"}
    with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(skill_dir.rglob("*")):
            if p.is_file() and p.name not in exclude and "__pycache__" not in p.parts:
                zf.write(p, p.relative_to(skill_dir.parent))

    print(f"Packaged skill: {out_file}")


if __name__ == "__main__":
    main()

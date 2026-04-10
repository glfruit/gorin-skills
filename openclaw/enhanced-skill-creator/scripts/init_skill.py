#!/usr/bin/env python3
"""init_skill.py — Initialize a new skill scaffold from the enhanced template."""
import re
import shutil
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print("Usage: init_skill.py <skill-name> <output-dir> [resources]", file=sys.stderr)
        sys.exit(1)

    skill_name = sys.argv[1]
    output_dir = Path(sys.argv[2])
    resources = sys.argv[3] if len(sys.argv) > 3 else "scripts,references,assets"

    script_dir = Path(__file__).resolve().parent
    skill_root = script_dir.parent
    template = skill_root / "config" / "skill-template.md"

    if not template.is_file():
        print(f"Template not found: {template}", file=sys.stderr)
        sys.exit(1)

    if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", skill_name):
        print(f"Invalid skill name: {skill_name}", file=sys.stderr)
        print("Use lowercase letters, digits, and hyphens only.", file=sys.stderr)
        sys.exit(1)

    target_dir = output_dir / skill_name
    if target_dir.exists():
        print(f"Target already exists: {target_dir}", file=sys.stderr)
        sys.exit(1)

    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template, target_dir / "SKILL.md")

    # Create requested resource dirs
    for dir_name in resources.split(","):
        dir_name = dir_name.strip()
        if not dir_name:
            continue
        (target_dir / dir_name).mkdir(parents=True, exist_ok=True)

    # Replace obvious placeholders
    skill_md = target_dir / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    text = text.replace(
        "{REPLACE: lowercase-hyphen-numbers-only, e.g. \"my-cool-skill\"}",
        skill_name,
    )
    text = text.replace(
        "{REPLACE: Skill Title}",
        skill_name.replace("-", " ").title(),
    )
    skill_md.write_text(text, encoding="utf-8")

    print(
        f"Initialized skill scaffold:\n"
        f"- path: {target_dir}\n"
        f"- resources: {resources}\n"
        f"\n"
        f"Next steps:\n"
        f"1. Fill in SKILL.md frontmatter and sections\n"
        f"2. Add negative triggers in When NOT to Use\n"
        f"3. Add Error Handling details\n"
        f"4. Define the Internal Acceptance happy path\n"
        f"5. Add scripts/references/assets only if truly needed\n"
        f'6. Run: python3 "{script_dir}/quick_validate.py" "{target_dir}"\n'
        f'7. Run: python3 "{script_dir}/validate_skill.py" "{target_dir}"\n'
        f"8. Do not report completion to the user until the skill reaches integrated readiness."
    )


if __name__ == "__main__":
    main()

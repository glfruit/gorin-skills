#!/usr/bin/env python3
"""validate_skill.py — Structural validation for OpenClaw skills."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def check(name: str, status: str, detail: str = ""):
    results.append({"name": name, "status": status, "detail": detail})
    if status == "pass":
        state["pass"] += 1
    elif status == "fail":
        state["fail"] += 1


def output_json(directory: str) -> None:
    overall = "FAIL" if state["fail"] > 0 else "PASS"
    total = state["pass"] + state["fail"]
    print(
        json.dumps(
            {
                "directory": directory,
                "pass": state["pass"],
                "fail": state["fail"],
                "total": total,
                "result": overall,
                "checks": results,
            }
        )
    )


results = []
state = {"pass": 0, "fail": 0}


def main() -> None:
    global results, state
    results = []
    state = {"pass": 0, "fail": 0}

    if len(sys.argv) < 2:
        print(
            json.dumps(
                {"error": "Usage: validate_skill.py <skill-directory>"}
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    skill_dir = Path(sys.argv[1].rstrip("/"))
    skill_md = skill_dir / "SKILL.md"

    if not skill_dir.is_dir():
        print(
            json.dumps(
                {"error": f"Directory does not exist: {skill_dir}"}
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Check 1: SKILL.md exists ---
    if not skill_md.is_file():
        check("skill_md_exists", "fail", f"SKILL.md not found in {skill_dir}")
        output_json(str(skill_dir))
        sys.exit(1)
    check("skill_md_exists", "pass")

    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()

    # --- Check 2: Valid YAML frontmatter with name + description ---
    frontmatter = ""
    if lines and lines[0].strip() == "---":
        fm_lines = []
        for line in lines[1:]:
            if line.strip() == "---":
                break
            fm_lines.append(line)
        frontmatter = "\n".join(fm_lines)

    has_name = False
    has_desc = False
    name_value = ""
    desc_value = ""

    if frontmatter:
        for line in frontmatter.splitlines():
            m = re.match(r"^name:\s*(.*)", line)
            if m:
                name_value = m.group(1).strip().strip('"')
                has_name = bool(name_value)
            m = re.match(r"^description:\s*(.*)", line)
            if m:
                desc_value = m.group(1).strip().strip('"')
                has_desc = bool(desc_value)

    if has_name and has_desc:
        check("frontmatter_valid", "pass")
    else:
        missing = []
        if not has_name:
            missing.append("name")
        if not has_desc:
            missing.append("description")
        check("frontmatter_valid", "fail", f"Missing fields: {', '.join(missing)}")

    # --- Check 3: Name format ---
    if name_value:
        if re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", name_value):
            check("name_format", "pass")
        else:
            check("name_format", "fail", f"Name '{name_value}' must be lowercase-hyphen-numbers only")
    else:
        check("name_format", "fail", "No name field found")

    # --- Check 4: Description length ---
    if desc_value:
        desc_len = len(desc_value)
        if desc_len >= 50:
            check("description_length", "pass", f"{desc_len} characters")
        else:
            check("description_length", "fail", f"Description is {desc_len} chars, need >= 50")
    else:
        check("description_length", "fail", "No description field found")

    # --- Check 4b: Routing safety in metadata ---
    routing_issues = ""
    metadata_text = frontmatter
    if re.search(r"(^|[^a-zA-Z0-9])\*($|[^a-zA-Z0-9])|\.\*", metadata_text, re.I | re.M):
        routing_issues += "Wildcard pattern detected in frontmatter; "
    if re.search(r"any request|all tasks|everything|general-purpose assistant|use for all questions", metadata_text, re.I | re.M):
        routing_issues += "Catch-all phrasing detected in frontmatter; "
    if desc_value and not re.search(r"don't use|do not use|not for|avoid when|except when", desc_value, re.I | re.M):
        routing_issues += "Description lacks explicit negative trigger phrasing; "
    if routing_issues:
        check("routing_safety_metadata", "fail", routing_issues)
    else:
        check("routing_safety_metadata", "pass")

    # --- Check 5: At least 2 core sections ---
    section_names = [
        "Overview", "When to Use", "Core Workflow", "Quick Start", "Quick Reference",
        "Workflow", "When NOT to Use", "Common Mistakes", "Resources", "Error Handling",
        "核心功能", "快速开始", "使用方式", "工作流", "配置", "输出格式", "依赖", "错误处理",
        "Core Functionality", "Usage", "Configuration", "Output", "Dependencies",
    ]
    section_count = 0
    found_sections = []
    for section in section_names:
        if re.search(f"^#.*{re.escape(section)}", text, re.I | re.M):
            section_count += 1
            found_sections.append(section)
    if section_count >= 2:
        check("core_sections", "pass", f"Found: {', '.join(found_sections)}")
    else:
        found_str = ", ".join(found_sections) if found_sections else "none"
        check("core_sections", "fail", f"Only {section_count} core sections found (need >= 2). Found: {found_str}")

    # --- Check 5b: Numbered workflow ---
    step_matches = re.findall(r"(?:^|\s)(?:Step\s+\d+|\d+\.)", text)
    if step_matches:
        check("workflow_numbering", "pass", "Found numbered workflow steps")
    else:
        check("workflow_numbering", "fail", "Missing clear numbered workflow steps (e.g. Step 1 / 1.)")

    # --- Check 5c: Progressive disclosure signals ---
    pd_signals = re.findall(r"references/|assets/|scripts/", text)
    if pd_signals:
        check("progressive_disclosure_signals", "pass", "Found bundled resource references")
    else:
        check("progressive_disclosure_signals", "fail", "No references to references/, assets/, or scripts/ found in SKILL.md")

    # --- Check 6: No forbidden files at root ---
    forbidden = []
    for f in ("README.md", "INSTALL.md"):
        if (skill_dir / f).is_file():
            forbidden.append(f)
    if forbidden:
        check("no_forbidden_files", "fail", f"Forbidden files found: {', '.join(forbidden)}")
    else:
        check("no_forbidden_files", "pass")

    # --- Check 7: SKILL.md <= 500 lines ---
    line_count = len(lines)
    if line_count <= 500:
        check("size_constraint", "pass", f"{line_count} lines")
    else:
        check("size_constraint", "fail", f"SKILL.md is {line_count} lines, max 500")

    # --- Check 8: Scripts have shebang and are executable ---
    scripts_dir = skill_dir / "scripts"
    script_issues = ""
    if scripts_dir.is_dir():
        for script in sorted(scripts_dir.rglob("*.sh")) + sorted(scripts_dir.rglob("*.py")):
            if not script.is_file():
                continue
            bn = script.name
            first_line = ""
            try:
                first_line = script.read_text(encoding="utf-8").splitlines()[0]
            except (IndexError, Exception):
                pass
            if not first_line.startswith("#!"):
                script_issues += f"{bn}: missing shebang; "
            if not os.access(script, os.X_OK):
                script_issues += f"{bn}: not executable; "
    if script_issues:
        check("script_standards", "fail", script_issues)
    else:
        check("script_standards", "pass")

    # --- Check 9: No placeholder text ---
    placeholder_found = ""
    placeholder_patterns = [
        r"Step one",
        r"example\.com",
        r"placeholder",
        r"TODO",
        r"FIXME",
        r"lorem ipsum",
        r"your .* here",
    ]
    exclusion_patterns = [
        r"""['"`].*placeholder""",
        r"Before",
        r"After",
        r"Detection",
        r"search.*for",
        r"Anti-Pattern",
        r"Failure",
        r"Lesson",
        r"previous",
        r"检测",
        r"never.*placeholder",
        r"not.*placeholder",
        r"no.placeholder",
        r"无.?placeholder",  # Chinese: 无 placeholder
        r"- \[.\].*placeholder",
        r"- \[.\].*TODO",
    ]
    for pattern in placeholder_patterns:
        matches = []
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.I | re.M):
                excluded = False
                for exc in exclusion_patterns:
                    if re.search(exc, line, re.I | re.M):
                        excluded = True
                        break
                if not excluded:
                    matches.append(f"{i}:{line.rstrip()}")
        if matches:
            placeholder_found += matches[0] + "; "
    if placeholder_found:
        check("no_placeholder_text", "fail", placeholder_found[:200])
    else:
        check("no_placeholder_text", "pass")

    # --- Check 9b: Negative trigger section ---
    if re.search("^#+ .*When NOT to Use", text, re.I | re.M) or re.search("^#+ .*不.*使用", text, re.I | re.M):
        check("negative_triggers_section", "pass")
    else:
        check("negative_triggers_section", "fail", "Missing a clear 'When NOT to Use' section")

    # --- Check 9c: Error handling section ---
    if re.search("^#+ .*Error Handling", text, re.I | re.M) or re.search("^#+ .*错误处理", text, re.I | re.M):
        check("error_handling_section", "pass")
    else:
        check("error_handling_section", "fail", "Missing an 'Error Handling' section")

    # --- Check 9d: Internal Acceptance section ---
    if re.search("^#+ .*Internal Acceptance", text, re.I | re.M) or re.search("^#+ .*内部验收", text, re.I | re.M):
        check("internal_acceptance_section", "pass")
    else:
        check("internal_acceptance_section", "fail", "Missing an 'Internal Acceptance' section")

    # --- Check 9e: Delivery Contract section ---
    if re.search("^#+ .*(Delivery Contract|Delivery Rule)", text, re.I | re.M) or re.search("^#+ .*交付", text, re.I | re.M):
        check("delivery_contract_section", "pass")
    else:
        check("delivery_contract_section", "fail", "Missing a 'Delivery Contract' or 'Delivery Rule' section")

    # --- Check 9f: Gotchas section ---
    if re.search("^#+ .*Gotchas", text, re.I | re.M):
        check("gotchas_section", "pass")
    else:
        check("gotchas_section", "fail", "Missing 'Gotchas' section (mandatory — concrete failure points)")

    # --- Check 9f2: User-facing completion rule requires integrated ---
    has_integrated = bool(re.search(r"integrated", text, re.I | re.M))
    has_report_rule = bool(re.search(r"Do \*\*not\*\* report|do not report|only report .*integrated|unless .*integrated", text, re.I | re.M))
    if has_integrated and has_report_rule:
        check("integrated_completion_rule", "pass")
    else:
        check("integrated_completion_rule", "fail", "Missing explicit rule that only integrated skills may be reported complete to the user")

    # --- Check 10: Referenced resource files exist ---
    missing_refs = ""
    refs = re.findall(r"`((?:references|assets|scripts)/[^` ]+)`", text)
    for ref in refs:
        # Skip template paths with placeholders like {type}, {name}
        if "{" in ref or "}" in ref:
            continue
        if not (skill_dir / ref).exists():
            missing_refs += f"{ref}; "
    if missing_refs:
        check("resource_references_exist", "fail", f"Missing referenced resources: {missing_refs[:200]}")
    else:
        check("resource_references_exist", "pass")

    # --- Check 11: No hardcoded /Users/ paths in scripts ---
    hardcoded_found = ""
    if scripts_dir.is_dir():
        for script in sorted(scripts_dir.rglob("*.sh")) + sorted(scripts_dir.rglob("*.py")):
            if not script.is_file():
                continue
            bn = script.name
            try:
                s_lines = script.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception:
                continue
            for i, s_line in enumerate(s_lines, 1):
                if "/Users/" in s_line:
                    stripped = s_line.strip()
                    if stripped.startswith("#"):
                        continue
                    if "grep" in stripped and ("/Users/" in stripped):
                        continue
                    # Skip string literals containing the search pattern itself
                    if '"/Users/"' in s_line or "'/Users/'" in s_line or "r\"/Users/" in s_line:
                        continue
                    hardcoded_found += f"{bn}: {i}:{stripped[:80]}; "
                    break
            if len(hardcoded_found) > 200:
                break
    if hardcoded_found:
        check("no_hardcoded_paths", "fail", hardcoded_found[:200])
    else:
        check("no_hardcoded_paths", "pass")

    # --- Check 12: set -e in shell scripts ---
    set_flag_issues = ""
    if scripts_dir.is_dir():
        for script in sorted(scripts_dir.rglob("*.sh")):
            if not script.is_file():
                continue
            bn = script.name
            try:
                head_lines = script.read_text(encoding="utf-8", errors="replace").splitlines()[:10]
            except Exception:
                continue
            if not any(re.match(r"^set -e", line) for line in head_lines):
                set_flag_issues += f"{bn}: missing set -e; "
    if set_flag_issues:
        check("script_error_handling", "fail", set_flag_issues)
    else:
        check("script_error_handling", "pass")

    # --- Check 13: shellcheck (optional) ---
    shellcheck = shutil.which("shellcheck")
    if shellcheck:
        shellcheck_issues = ""
        if scripts_dir.is_dir():
            for script in sorted(scripts_dir.rglob("*.sh")):
                if not script.is_file():
                    continue
                bn = script.name
                try:
                    proc = subprocess.run(
                        [shellcheck, "-S", "warning", str(script)],
                        capture_output=True, text=True, timeout=30,
                    )
                    sc_out = (proc.stdout or proc.stderr).strip()
                    if sc_out:
                        first3 = "\n".join(sc_out.splitlines()[:3])
                        shellcheck_issues += f"{bn}: {first3}; "
                except Exception:
                    pass
        if shellcheck_issues:
            check("script_shellcheck", "fail", shellcheck_issues[:300])
        else:
            check("script_shellcheck", "pass")
    else:
        check("script_shellcheck", "skip", "shellcheck not installed, run: brew install shellcheck")

    # --- Check 14: syntax smoke test ---
    syntax_issues = ""
    if scripts_dir.is_dir():
        for script in sorted(scripts_dir.rglob("*.sh")):
            if not script.is_file():
                continue
            bn = script.name
            try:
                proc = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True, timeout=10)
                if proc.returncode != 0:
                    syntax_issues += f"{bn}: {(proc.stderr or proc.stdout).strip()}; "
            except Exception:
                pass
        for script in sorted(scripts_dir.rglob("*.py")):
            if not script.is_file():
                continue
            bn = script.name
            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(script)],
                    capture_output=True, text=True, timeout=10,
                )
                if proc.returncode != 0:
                    syntax_issues += f"{bn}: {(proc.stderr or proc.stdout).strip()}; "
            except Exception:
                pass
    if syntax_issues:
        check("script_smoke_test", "fail", syntax_issues[:300])
    else:
        check("script_smoke_test", "pass")

    # --- Check 15: No stubbed implementation ---
    stubbed_issues = ""
    if scripts_dir.is_dir():
        stub_patterns = re.compile(
            r"TODO: Implement|not implemented|NotImplementedError|throw new Error\(\"Not implemented|stub implementation|placeholder implementation",
            re.I,
        )
        for script in sorted(scripts_dir.rglob("*")):
            if not script.is_file() or script.suffix not in (".sh", ".ts", ".js", ".py"):
                continue
            bn = script.name
            try:
                s_text = script.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            matches = []
            for i, s_line in enumerate(s_text.splitlines(), 1):
                if stub_patterns.search(s_line):
                    stripped = s_line.strip()
                    # Skip lines that define the search pattern itself (r"..." or "...")
                    if 'r"' in s_line and 'not implemented' in s_line:
                        continue
                    if 'stub implementation' in s_line and ('re.compile' in s_line or 'r"' in s_line or "r'" in s_line):
                        continue
                    matches.append(f"{i}:{stripped[:80]}")
            if matches:
                stubbed_issues += f"{bn}: {'; '.join(matches[:3])}; "
    if stubbed_issues:
        check("no_stubbed_implementation", "fail", stubbed_issues[:300])
    else:
        check("no_stubbed_implementation", "pass")

    # --- Output JSON ---
    output_json(str(skill_dir))


if __name__ == "__main__":
    main()

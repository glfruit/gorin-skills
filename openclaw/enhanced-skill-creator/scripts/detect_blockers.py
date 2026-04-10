#!/usr/bin/env python3
"""detect_blockers.py — Detect execution blockers / ambiguity hotspots in a skill."""
import json
import re
import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print('{"error": "Usage: detect_blockers.py <skill-directory>"}', file=sys.stderr)
        sys.exit(1)

    skill_dir = Path(sys.argv[1].rstrip("/"))
    skill_md = skill_dir / "SKILL.md"

    if not skill_dir.is_dir():
        print('{"error": "Skill directory does not exist"}', file=sys.stderr)
        sys.exit(1)
    if not skill_md.is_file():
        print('{"error": "SKILL.md not found in skill directory"}', file=sys.stderr)
        sys.exit(1)

    # Run validator
    script_dir = Path(__file__).resolve().parent
    validator = script_dir / "validate_skill.py"
    validation = {}
    try:
        proc = subprocess.run(
            [sys.executable, str(validator), str(skill_dir)],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0 or proc.stdout.strip():
            validation = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except Exception:
        pass

    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    checks = {c.get("name"): c for c in validation.get("checks", [])}

    findings = []

    def add(kind, severity, message, detail="", line=None, suggested_fix=""):
        findings.append({
            "kind": kind,
            "severity": severity,
            "message": message,
            "detail": detail,
            "line": line,
            "suggestedFix": suggested_fix,
        })

    # Validator-backed blockers
    mapping = [
        ("routing_safety_metadata", "blocker", "Metadata routing safety failure", "Tighten description and remove wildcard/catch-all phrasing."),
        ("workflow_numbering", "ambiguity", "Workflow is not clearly numbered", "Add numbered steps and explicit branch logic."),
        ("resource_references_exist", "blocker", "Referenced resource file is missing", "Create or relink the missing resource."),
        ("error_handling_section", "missing_fallback", "Error Handling section is missing", "Add explicit failure handling paths."),
        ("negative_triggers_section", "assumption", "When NOT to Use / negative trigger section is missing", "Add explicit negative triggers to reduce routing ambiguity."),
        ("progressive_disclosure_signals", "assumption", "No bundled-resource references detected", "Move dense details into references/assets/scripts and link them."),
    ]
    for check_name, kind, msg, fix in mapping:
        c = checks.get(check_name)
        if c and c.get("status") == "fail":
            sev = "fail" if kind in ("blocker", "missing_fallback") else "warn"
            add(kind, sev, msg, c.get("detail", ""), suggested_fix=fix)

    # Text heuristics for ambiguity
    ambiguous_patterns = [
        (r"\bmaybe\b", 'Uses "maybe", which often signals under-specified procedure'),
        (r"\bperhaps\b", 'Uses "perhaps", which often signals under-specified procedure'),
        (r"\bif needed\b", 'Contains "if needed" without necessarily defining the trigger condition'),
        (r"\bappropriate\b", 'Contains "appropriate", which may rely on unstated judgment criteria'),
        (r"\bas necessary\b", 'Contains "as necessary", which may hide a missing decision rule'),
    ]
    for idx, line in enumerate(lines, 1):
        lower = line.lower()
        for pat, msg in ambiguous_patterns:
            if re.search(pat, lower):
                add("ambiguity", "warn", msg, detail=line.strip(), line=idx, suggested_fix="Replace vague language with explicit decision criteria or step branching.")

    # Missing fallback heuristics
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        is_command = False
        if re.search(r"`(bash|python3?|node|sh)\s+[^`]+`", stripped, re.I):
            is_command = True
        elif re.match(r"^(bash|python3?|node|sh)\s+\S+", stripped, re.I):
            is_command = True
        elif re.search(r"\b(run|execute)\b.*`?scripts/[^` ]+", stripped, re.I):
            is_command = True

        if is_command and idx < len(lines):
            window = "\n".join(lines[max(0, idx - 2):min(len(lines), idx + 3)])
            if not re.search(r"fail|error|stop|if .* fails|fallback|report", window, re.I):
                add("missing_fallback", "warn", "Executable command mentioned without nearby failure handling", detail=stripped, line=idx, suggested_fix="Add a local failure path or point to Error Handling.")

    # Environment assumptions
    for idx, line in enumerate(lines, 1):
        if re.search(r"\b(api|auth|credential|token|python|node|bash|jq|ffmpeg|sqlite)\b", line, re.I):
            if not re.search(r"install|verify|check|precondition|requires|dependency", text, re.I):
                add("assumption", "warn", "Tooling or credential dependency mentioned without an explicit precondition/check pattern", detail=line.strip(), line=idx, suggested_fix="Add a prerequisite check or explicit dependency section.")
                break

    summary = {
        "blockers": sum(1 for f in findings if f["kind"] == "blocker"),
        "ambiguities": sum(1 for f in findings if f["kind"] == "ambiguity"),
        "assumptions": sum(1 for f in findings if f["kind"] == "assumption"),
        "missingFallbacks": sum(1 for f in findings if f["kind"] == "missing_fallback"),
    }
    result = "PASS" if not findings else "WARN"
    if summary["blockers"] > 0:
        result = "FAIL"

    print(json.dumps({
        "tool": "detect-blockers",
        "version": "0.1",
        "skillPath": str(skill_md.parent),
        "result": result,
        "summary": summary,
        "findings": findings,
        "artifacts": {"draft": None},
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

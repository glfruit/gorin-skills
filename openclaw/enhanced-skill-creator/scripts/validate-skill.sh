#!/usr/bin/env bash
set -euo pipefail

# validate-skill.sh — Structural validation for OpenClaw skills
# Usage: bash validate-skill.sh <skill-directory>
# Output: JSON with pass/fail per check, overall result, and summary

SKILL_DIR="${1:?Usage: validate-skill.sh <skill-directory>}"

# Normalize path (remove trailing slash)
SKILL_DIR="${SKILL_DIR%/}"

if [[ ! -d "$SKILL_DIR" ]]; then
  echo '{"error": "Directory does not exist: '"$SKILL_DIR"'"}' >&2
  exit 1
fi

SKILL_MD="$SKILL_DIR/SKILL.md"
pass_count=0
fail_count=0
results=()

check() {
  local name="$1"
  local status="$2"
  local detail="${3:-}"
  if [[ "$status" == "pass" ]]; then
    ((pass_count++))
  elif [[ "$status" == "fail" ]]; then
    ((fail_count++))
  fi
  # "skip" doesn't count toward pass or fail
  # Escape detail for JSON
  detail="${detail//\\/\\\\}"
  detail="${detail//\"/\\\"}"
  detail="${detail//$'\n'/\\n}"
  results+=("{\"name\": \"$name\", \"status\": \"$status\", \"detail\": \"$detail\"}")
}

# --- Check 1: SKILL.md exists ---
if [[ -f "$SKILL_MD" ]]; then
  check "skill_md_exists" "pass"
else
  check "skill_md_exists" "fail" "SKILL.md not found in $SKILL_DIR"
  # Can't continue without SKILL.md
  printf '{"directory": "%s", "pass": %d, "fail": %d, "total": %d, "result": "FAIL", "checks": [%s]}\n' \
    "$SKILL_DIR" "$pass_count" "$fail_count" "$((pass_count + fail_count))" \
    "$(IFS=,; echo "${results[*]}")"
  exit 1
fi

# --- Check 2: Valid YAML frontmatter with name + description ---
frontmatter=""
if head -1 "$SKILL_MD" | grep -q '^---$'; then
  frontmatter=$(sed -n '2,/^---$/p' "$SKILL_MD" | sed '$d')
fi

has_name=false
has_desc=false
name_value=""
desc_value=""

if [[ -n "$frontmatter" ]]; then
  name_value=$(echo "$frontmatter" | grep -E '^name:' | head -1 | sed 's/^name:[[:space:]]*//' | tr -d '"' || true)
  desc_value=$(echo "$frontmatter" | grep -E '^description:' | head -1 | sed 's/^description:[[:space:]]*//' | tr -d '"' || true)
  [[ -n "$name_value" ]] && has_name=true
  [[ -n "$desc_value" ]] && has_desc=true
fi

if $has_name && $has_desc; then
  check "frontmatter_valid" "pass"
else
  missing=""
  $has_name || missing="name"
  $has_desc || missing="${missing:+$missing, }description"
  check "frontmatter_valid" "fail" "Missing fields: $missing"
fi

# --- Check 3: Name format (lowercase-hyphen-numbers) ---
if [[ -n "$name_value" ]]; then
  if [[ "$name_value" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
    check "name_format" "pass"
  else
    check "name_format" "fail" "Name '$name_value' must be lowercase-hyphen-numbers only"
  fi
else
  check "name_format" "fail" "No name field found"
fi

# --- Check 4: Description length >= 50 characters ---
if [[ -n "$desc_value" ]]; then
  desc_len=${#desc_value}
  if [[ $desc_len -ge 50 ]]; then
    check "description_length" "pass" "${desc_len} characters"
  else
    check "description_length" "fail" "Description is ${desc_len} chars, need >= 50"
  fi
else
  check "description_length" "fail" "No description field found"
fi

# --- Check 4b: Routing safety in metadata ---
routing_issues=""
metadata_text="$frontmatter"
if echo "$metadata_text" | grep -qiE '(^|[^[:alnum:]])\*($|[^[:alnum:]])|\.\*'; then
  routing_issues="${routing_issues}Wildcard pattern detected in frontmatter; "
fi
if echo "$metadata_text" | grep -qiE 'any request|all tasks|everything|general-purpose assistant|use for all questions'; then
  routing_issues="${routing_issues}Catch-all phrasing detected in frontmatter; "
fi
if [[ -n "$desc_value" ]] && ! echo "$desc_value" | grep -qiE "don't use|do not use|not for|avoid when|except when"; then
  routing_issues="${routing_issues}Description lacks explicit negative trigger phrasing; "
fi
if [[ -z "$routing_issues" ]]; then
  check "routing_safety_metadata" "pass"
else
  check "routing_safety_metadata" "fail" "$routing_issues"
fi

# --- Check 5: At least 2 core sections ---
# Match common section names in English and Chinese, with or without emoji prefixes
section_count=0
found_sections=""
for section in "Overview" "When to Use" "Core Workflow" "Quick Start" "Quick Reference" \
  "Workflow" "When NOT to Use" "Common Mistakes" "Resources" "Error Handling" \
  "核心功能" "快速开始" "使用方式" "工作流" "配置" "输出格式" "依赖" "错误处理" \
  "Core Functionality" "Usage" "Configuration" "Output" "Dependencies"; do
  if grep -qi "^#.*${section}" "$SKILL_MD"; then
    ((section_count++))
    found_sections="${found_sections:+$found_sections, }$section"
  fi
done
if [[ $section_count -ge 2 ]]; then
  check "core_sections" "pass" "Found: $found_sections"
else
  check "core_sections" "fail" "Only $section_count core sections found (need >= 2). Found: ${found_sections:-none}"
fi

# --- Check 5b: Numbered workflow / step-by-step guidance ---
step_matches=$(grep -nE '(^|[[:space:]])(Step[[:space:]]+[0-9]+|[0-9]+\.)' "$SKILL_MD" | head -5 || true)
if [[ -n "$step_matches" ]]; then
  check "workflow_numbering" "pass" "Found numbered workflow steps"
else
  check "workflow_numbering" "fail" "Missing clear numbered workflow steps (e.g. Step 1 / 1.)"
fi

# --- Check 5c: Progressive disclosure signals ---
pd_signals=$(grep -nE 'references/|assets/|scripts/' "$SKILL_MD" | head -5 || true)
if [[ -n "$pd_signals" ]]; then
  check "progressive_disclosure_signals" "pass" "Found bundled resource references"
else
  check "progressive_disclosure_signals" "fail" "No references to references/, assets/, or scripts/ found in SKILL.md"
fi

# --- Check 6: No forbidden files at root ---
forbidden_found=""
for f in README.md INSTALL.md; do
  if [[ -f "$SKILL_DIR/$f" ]]; then
    forbidden_found="${forbidden_found:+$forbidden_found, }$f"
  fi
done
if [[ -z "$forbidden_found" ]]; then
  check "no_forbidden_files" "pass"
else
  check "no_forbidden_files" "fail" "Forbidden files found: $forbidden_found"
fi

# --- Check 7: SKILL.md <= 500 lines ---
line_count=$(wc -l < "$SKILL_MD" | tr -d ' ')
if [[ $line_count -le 500 ]]; then
  check "size_constraint" "pass" "${line_count} lines"
else
  check "size_constraint" "fail" "SKILL.md is ${line_count} lines, max 500"
fi

# --- Check 8: Scripts have shebang and are executable ---
script_issues=""
if [[ -d "$SKILL_DIR/scripts" ]]; then
  while IFS= read -r script; do
    basename_script=$(basename "$script")
    if ! head -1 "$script" | grep -q '^#!'; then
      script_issues="${script_issues}${basename_script}: missing shebang; "
    fi
    if [[ ! -x "$script" ]]; then
      script_issues="${script_issues}${basename_script}: not executable; "
    fi
  done < <(find "$SKILL_DIR/scripts" \( -name "*.sh" -o -name "*.py" \) -type f 2>/dev/null)
fi
if [[ -z "$script_issues" ]]; then
  check "script_standards" "pass"
else
  check "script_standards" "fail" "$script_issues"
fi

# --- Check 9: No placeholder text ---
# Skip lines that quote these terms as examples (contain quotes, backticks, or "Before"/"After"/"Detection"/"search")
placeholder_found=""
for pattern in "Step one" "example\.com" "placeholder" "TODO" "FIXME" "lorem ipsum" "your .* here"; do
  matches=$(grep -inE "$pattern" "$SKILL_MD" \
    | grep -ivE '["'"'"'`].*'"$pattern"'|Before|After|Detection|search.*for|Anti-Pattern|Failure|Lesson|previous|检测|never.*placeholder|not.*placeholder|\- \[.\].*placeholder|\- \[.\].*TODO' \
    | head -3 || true)
  if [[ -n "$matches" ]]; then
    first_match=$(echo "$matches" | head -1 | sed 's/[[:space:]]*$//')
    placeholder_found="${placeholder_found}${first_match}; "
  fi
done
if [[ -z "$placeholder_found" ]]; then
  check "no_placeholder_text" "pass"
else
  check "no_placeholder_text" "fail" "${placeholder_found:0:200}"
fi

# --- Check 9b: Negative trigger section exists in body ---
if grep -qiE '^#+ .*When NOT to Use' "$SKILL_MD" || grep -qiE '^#+ .*不.*使用' "$SKILL_MD"; then
  check "negative_triggers_section" "pass"
else
  check "negative_triggers_section" "fail" "Missing a clear 'When NOT to Use' section"
fi

# --- Check 9c: Error handling section exists or is referenced ---
if grep -qiE '^#+ .*Error Handling' "$SKILL_MD" || grep -qiE '^#+ .*错误处理' "$SKILL_MD"; then
  check "error_handling_section" "pass"
else
  check "error_handling_section" "fail" "Missing an 'Error Handling' section"
fi

# --- Check 9d: Internal Acceptance section exists ---
if grep -qiE '^#+ .*Internal Acceptance' "$SKILL_MD" || grep -qiE '^#+ .*内部验收' "$SKILL_MD"; then
  check "internal_acceptance_section" "pass"
else
  check "internal_acceptance_section" "fail" "Missing an 'Internal Acceptance' section"
fi

# --- Check 9e: Delivery Contract / Delivery Rule section exists ---
if grep -qiE '^#+ .*(Delivery Contract|Delivery Rule)' "$SKILL_MD" || grep -qi '^#+ .*交付' "$SKILL_MD"; then
  check "delivery_contract_section" "pass"
else
  check "delivery_contract_section" "fail" "Missing a 'Delivery Contract' or 'Delivery Rule' section"
fi

# --- Check 9f: User-facing completion rule requires integrated ---
if grep -qiE 'integrated' "$SKILL_MD" && grep -qiE 'Do \*\*not\*\* report|do not report|only report .*integrated|unless .*integrated' "$SKILL_MD"; then
  check "integrated_completion_rule" "pass"
else
  check "integrated_completion_rule" "fail" "Missing explicit rule that only integrated skills may be reported complete to the user"
fi

# --- Check 10: Referenced resource files exist ---
missing_refs=""
while IFS= read -r ref; do
  clean_ref=$(echo "$ref" | sed 's/^[^`]*`//; s/`.*$//')
  [[ -z "$clean_ref" ]] && continue
  if [[ ! -e "$SKILL_DIR/$clean_ref" ]]; then
    missing_refs="${missing_refs}${clean_ref}; "
  fi
done < <(grep -oE '`(references|assets|scripts)/[^` ]+' "$SKILL_MD" || true)
if [[ -z "$missing_refs" ]]; then
  check "resource_references_exist" "pass"
else
  check "resource_references_exist" "fail" "Missing referenced resources: ${missing_refs:0:200}"
fi

# --- Check 11: No hardcoded /Users/ paths in scripts ---
# Only flag actual path usage, not grep patterns searching for /Users/
hardcoded_found=""
if [[ -d "$SKILL_DIR/scripts" ]]; then
  while IFS= read -r script; do
    matches=$(grep -n '/Users/' "$script" \
      | grep -v '^[0-9]*:[[:space:]]*#' \
      | grep -v "grep.*'/Users/'" \
      | grep -v 'grep.*"/Users/"' \
      | grep -v "grep.*'/Users/'" \
      | head -3 || true)
    if [[ -n "$matches" ]]; then
      hardcoded_found="${hardcoded_found}$(basename "$script"): $matches; "
    fi
  done < <(find "$SKILL_DIR/scripts" \( -name "*.sh" -o -name "*.py" \) -type f 2>/dev/null)
fi
# Also check SKILL.md for hardcoded paths (but allow them in examples/comments)
if [[ -z "$hardcoded_found" ]]; then
  check "no_hardcoded_paths" "pass"
else
  check "no_hardcoded_paths" "fail" "${hardcoded_found:0:200}"
fi

# --- Check 12: set -e / set -euo pipefail in scripts ---
set_flag_issues=""
if [[ -d "$SKILL_DIR/scripts" ]]; then
  while IFS= read -r script; do
    # Check first 10 lines for set -e or set -eu or set -euo pipefail
    head_lines=$(head -10 "$script")
    if ! echo "$head_lines" | grep -qE '^set -e'; then
      set_flag_issues="${set_flag_issues}$(basename "$script"): missing set -e; "
    fi
  done < <(find "$SKILL_DIR/scripts" -name "*.sh" -type f 2>/dev/null)
fi
if [[ -z "$set_flag_issues" ]]; then
  check "script_error_handling" "pass"
else
  check "script_error_handling" "fail" "$set_flag_issues"
fi

# --- Check 13: shellcheck static analysis (optional) ---
if command -v shellcheck &>/dev/null; then
  shellcheck_issues=""
  if [[ -d "$SKILL_DIR/scripts" ]]; then
    while IFS= read -r script; do
      sc_output=$(shellcheck -S warning "$script" 2>&1 || true)
      if [[ -n "$sc_output" ]]; then
        # Take first 3 lines of output
        first3=$(echo "$sc_output" | head -3)
        shellcheck_issues="${shellcheck_issues}$(basename "$script"): $first3; "
      fi
    done < <(find "$SKILL_DIR/scripts" -name "*.sh" -type f 2>/dev/null)
  fi
  if [[ -z "$shellcheck_issues" ]]; then
    check "script_shellcheck" "pass"
  else
    check "script_shellcheck" "fail" "${shellcheck_issues:0:300}"
  fi
else
  check "script_shellcheck" "skip" "shellcheck not installed, run: brew install shellcheck"
fi

# --- Check 14: syntax smoke test (bash -n for .sh, py_compile for .py) ---
syntax_issues=""
if [[ -d "$SKILL_DIR/scripts" ]]; then
  while IFS= read -r script; do
    syntax_err=$(bash -n "$script" 2>&1 || true)
    if [[ -n "$syntax_err" ]]; then
      syntax_issues="${syntax_issues}$(basename "$script"): $syntax_err; "
    fi
  done < <(find "$SKILL_DIR/scripts" -name "*.sh" -type f 2>/dev/null)
  while IFS= read -r script; do
    syntax_err=$(python3 -m py_compile "$script" 2>&1 || true)
    if [[ -n "$syntax_err" ]]; then
      syntax_issues="${syntax_issues}$(basename "$script"): $syntax_err; "
    fi
  done < <(find "$SKILL_DIR/scripts" -name "*.py" -type f 2>/dev/null)
fi
if [[ -z "$syntax_issues" ]]; then
  check "script_smoke_test" "pass"
else
  check "script_smoke_test" "fail" "${syntax_issues:0:300}"
fi

# --- Check 15: No stubbed implementation in scripts ---
stubbed_issues=""
if [[ -d "$SKILL_DIR/scripts" ]]; then
  while IFS= read -r script; do
    matches=$(grep -nEi 'TODO: Implement|not implemented|NotImplementedError|throw new Error\("Not implemented|stub implementation|placeholder implementation' "$script" \
      | grep -v 'matches=\$(grep -nEi' \
      | head -3 || true)
    if [[ -n "$matches" ]]; then
      stubbed_issues="${stubbed_issues}$(basename "$script"): $(echo "$matches" | tr '\n' ' '); "
    fi
  done < <(find "$SKILL_DIR/scripts" -type f \( -name "*.sh" -o -name "*.ts" -o -name "*.js" -o -name "*.py" \) 2>/dev/null)
fi
if [[ -z "$stubbed_issues" ]]; then
  check "no_stubbed_implementation" "pass"
else
  check "no_stubbed_implementation" "fail" "${stubbed_issues:0:300}"
fi

# --- Output JSON ---
overall="PASS"
if [[ $fail_count -gt 0 ]]; then
  overall="FAIL"
fi

printf '{"directory": "%s", "pass": %d, "fail": %d, "total": %d, "result": "%s", "checks": [%s]}\n' \
  "$SKILL_DIR" "$pass_count" "$fail_count" "$((pass_count + fail_count))" "$overall" \
  "$(IFS=,; echo "${results[*]}")"

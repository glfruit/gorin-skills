# Acceptance Report — oc-card

Result: passed

## Primary Entrypoint

- Command / script: `python3 scripts/route_visual_skill.py --json "<request>"`
- Required dependencies: `python3`

## Supported Inputs

- Input type(s): natural-language visual request
- Required arguments: request text unless `--mode` is used
- Optional arguments: `--mode`, `--json`

## Expected Outputs

- Output type(s): routed mode + target downstream skill
- Default output location: stdout
- Naming convention: n/a

## Success Criteria

- What must exist after a successful run: JSON or plain-text route decision
- What must be true in the output: target skill matches the intended backend for the request shape, and the routed skill exists locally

## Failure / Fallback Behavior

- Known failure modes: unsupported mode alias, malformed CLI invocation
- Fallback behavior: classify manually via `references/mode-routing.md`
- Explicit non-goals: does not generate the final image by itself

## Verification Evidence

- Happy-path command: `python3 skills/oc-card/scripts/route_visual_skill.py --json '把这篇文章做成图'`
- Example input: `把这篇文章做成图`
- Example output path: stdout JSON
- Integrated caller (if any): direct chat request that needs routing before invoking a specialized visual skill

## Actual Run

- Workspace: `/Users/gorin/.openclaw/workspace-daily-tl`
- Observed routes:
  - `把这篇文章做成图` → `mode=long-card`, `target_skill=baoyu-infographic`
  - `做一个小红书多图卡片` → `mode=multi-card`, `target_skill=baoyu-xhs-images`
  - `给这篇文章做个封面` → `mode=cover`, `target_skill=baoyu-cover-image`
  - `把这个概念讲成漫画` → `mode=comic`, `target_skill=baoyu-comic`
- Local downstream skill existence verified for all four routed targets
- Validation snapshot:
  - `validate-skill`: PASS
  - `detect-overlap`: PASS (0 high-risk, 0 medium-risk)
  - `detect-blockers`: PASS

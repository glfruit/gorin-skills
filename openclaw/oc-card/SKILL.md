---
name: oc-card
description: "OpenClaw-native router for ambiguous card-format requests. Use when the user says '做成图', '做成卡片', '转成视觉卡片', 'long card', or wants help choosing a visual card format from source material. Don't use it for summarization, prose cleanup, publishing, tabular conversion, or when the user already named a specific downstream visual generator."
triggers: ["做成图", "做成卡片", "转成视觉卡片", "long card"]
user-invocable: true
agent-usable: true
---

# oc-card

Route visual requests to the best existing OpenClaw image skill. This is our rewrite of `ljg-card`, but adapted to OpenClaw tools and our current skill inventory rather than Claude-specific HTML molds.

## When to Use

- Turn pasted source material into a visual deliverable when the output shape is still vague.
- Choose between card families before invoking a specialized backend.
- Normalize vague requests like “帮我做成图” into a concrete downstream workflow.

## When NOT to Use

- Do not use this for pure rewriting, outlining, or note-taking.
- Do not use this when the user already explicitly chose a concrete downstream visual skill.
- Do not use this when the user already knows the exact output family they want; go straight to the specialized backend.
- Do not promise pixel-identical parity with upstream `ljg-card`; this rewrite is a router, not the old Playwright renderer.

## Design Pattern

This skill follows the **Pipeline** pattern: infer the requested visual shape, pick the best specialized backend, then continue inside that backend's workflow.

## Core Workflow

1. Read `references/mode-routing.md` for the mapping rules.
2. Run `python3 scripts/route_visual_skill.py --json "<user request>"`.
3. If output shape is still ambiguous, ask **one** clarifying question.
4. Read the routed downstream skill's `SKILL.md` and continue there.
5. Report the final artifact path from the downstream skill, not from `oc-card`.

## Quick Reference

- Auto-route request: `python3 scripts/route_visual_skill.py --json "把这篇文章做成图"` — if it fails, classify manually with `references/mode-routing.md`.
- Force long card: `python3 scripts/route_visual_skill.py --mode -l --json` — if it fails, use the long-card row in `references/mode-routing.md`.
- Force infographic: `python3 scripts/route_visual_skill.py --mode -i --json` — if it fails, route to `baoyu-infographic` manually.
- Force multi-card: `python3 scripts/route_visual_skill.py --mode -m --json` — if it fails, route to `baoyu-xhs-images` manually.
- Force comic: `python3 scripts/route_visual_skill.py --mode -c --json` — if it fails, route to `baoyu-comic` manually.
- Force whiteboard: `python3 scripts/route_visual_skill.py --mode -w --json` — if it fails, route to `baoyu-image-gen` manually.

## Common Mistakes

| Mistake | Why It Fails | Better Approach |
|---|---|---|
| Rebuilding another HTML screenshot system | Duplicates maintenance and ignores stronger local skills | Route to existing OpenClaw generators |
| Treating every “做成图” request as one image | Some requests need carousel, comic, or cover workflows | Infer shape first, then route |
| Hiding backend setup requirements | Downstream skills may need EXTEND.md or confirmations | Honor the downstream skill's blocking steps |

## Error Handling

### Missing Prerequisites
If the target backend is missing from the current installation, say which skill is missing and fall back to the nearest generic backend only if the user accepts lower fidelity.

### Unsupported Input or Configuration
If the user demands exact parity with upstream `ljg-card` HTML molds, say this rewrite does not yet implement that renderer.

### Script or Tool Failure
If `route_visual_skill.py` fails, classify manually using `references/mode-routing.md` and mention the script failure.

### Ambiguous State
If the request does not reveal whether the user wants one image, a cover, or a multi-image carousel, ask one concise clarifying question and stop there.

### Partial Success
If routing succeeds but the downstream generator is blocked on config/auth/preferences, report routing as done and name the blocker explicitly.

## Gotchas

- `oc-card` does not generate the final image by itself; it chooses the backend.
- Whiteboard/sketchnote currently route to `baoyu-image-gen`, not a dedicated whiteboard renderer.
- Long-card requests map to `baoyu-infographic` because that is the closest maintained backend in our stack.
- If the user already chose a backend, skip `oc-card` and go straight there.

## Internal Acceptance

- **Happy-path input**: "把这篇文章做成图"
- **Invocation method**: `python3 scripts/route_visual_skill.py --json "把这篇文章做成图"`
- **Expected artifacts**: JSON route showing a concrete downstream visual skill
- **Success criteria**: the mode resolves deterministically and the target skill exists in the local skill inventory
- **Fallback / blocker behavior**: if the script fails, classify manually via `references/mode-routing.md`
- **Integration point**: direct chat request for a visual deliverable, followed by handing off to the selected downstream skill

## Delivery Contract

- Internal readiness target for this version: `integrated`
- This version is complete when routing works on real requests and one downstream handoff path has been proven in this workspace.
- Do not report this skill as complete to the user unless readiness has reached `integrated`.

## Resources

- `references/mode-routing.md`
- `references/golden-cases.md`
- `scripts/route_visual_skill.py`

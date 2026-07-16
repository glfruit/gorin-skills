# Mode Routing

`oc-card` is the OpenClaw-native rewrite of `ljg-card`, but it intentionally does **not** copy the old Claude-specific HTML + Playwright architecture. Instead, it routes to existing OpenClaw image skills.

## Mode Mapping

| Requested shape | Signals | Route to |
|---|---|---|
| Long reading card | 长图, 卡片, 做成图, reading card | `baoyu-infographic` |
| Infographic | 信息图, infographic, 可视化, visual summary | `baoyu-infographic` |
| Multi-card / carousel | 多图, 多卡, carousel, 小红书, XHS | `baoyu-xhs-images` |
| Comic | 漫画, comic, manga | `baoyu-comic` |
| Whiteboard / sketchnote | 白板, whiteboard, sketchnote, 视觉笔记 | `baoyu-image-gen` |
| Cover | 封面, cover, hero image | `baoyu-cover-image` |
| Generic visual request | draw an image, make a picture | `baoyu-image-gen` |

## Why This Rewrite Exists

The upstream `ljg-card` skill assumed:
- Claude skill roots like `~/.claude/skills`
- a Node + Playwright screenshot pipeline
- fixed HTML templates inside the skill

In our environment we already have stronger OpenClaw-native generators. Rewriting as a router gives us:
- better reuse of existing skills
- less duplicate maintenance
- no redundant screenshot stack
- easier future extension when a dedicated whiteboard or reading-card backend appears

## Routing Rules

1. Prefer the most specialized backend already available.
2. If the user's requested output shape is unclear, ask **one** clarifying question at most.
3. After routing, read the target skill's `SKILL.md` and continue with that workflow.
4. If a backend requires setup (for example `EXTEND.md`), do not skip that setup.

## Failure Boundaries

- `oc-card` itself does not generate the final image; it selects the best downstream skill.
- Whiteboard/sketchnote currently routes to `baoyu-image-gen` because no dedicated OpenClaw-native whiteboard renderer exists yet.
- If the user wants exact parity with upstream `ljg-card` HTML molds, that is a separate implementation project, not this rewrite.

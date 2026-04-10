# Golden Cases

This rewrite is based on these real cases:

1. **Upstream `ljg-card`**
   - Source: `https://github.com/lijigang/ljg-skills/tree/main/skills/ljg-card`
   - Valuable pattern: one entrypoint that understands several visual molds from natural language.
   - Not copied: Claude-specific `~/.claude/skills` paths and Playwright screenshot stack.

2. **Local `baoyu-infographic`**
   - Source: `~/.gorin-skills/openclaw/baoyu-infographic/SKILL.md`
   - Valuable pattern: strong information-structure workflow for dense visual explanation.
   - Used here for: long-card and infographic routes.

3. **Local `baoyu-cover-image` / `baoyu-comic` / `baoyu-xhs-images`**
   - Source: corresponding local OpenClaw skills
   - Valuable pattern: specialized backends for single-cover, comic, and multi-card social image outputs.
   - Used here for: choosing the most specialized downstream generator instead of forcing one rendering pipeline.

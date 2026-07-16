I am evaluating an Agent Skill. Agents will decide whether to load this skill based entirely on the YAML metadata below.

{name-and-description-here}

Based strictly on this description:

1. Generate 3 realistic user prompts that you are 100% confident should trigger this skill.
2. Generate 3 user prompts that sound similar but should NOT trigger this skill.
3. Critique the description. Is it too broad, too narrow, or collision-prone?
4. Flag any routing safety problems, especially:
   - wildcard / catch-all behavior
   - lack of negative triggers
   - generic verb-only phrasing
   - overlap with common skill categories
5. Suggest an optimized rewrite that is narrower, explicit, and non-greedy.

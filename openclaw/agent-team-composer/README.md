# agent-team-composer

Generate a multi-agent team scaffold from natural-language requirements.

This skill outputs a usable team package instead of just prose:
- `SOUL.md`
- `AGENTS.md`
- `CollaborationRules.md`
- `Contacts.md`
- `agent-config.yaml`

It is intended for:
- OpenClaw team bootstrap
- internal collaboration norms
- IM-aware coordination setup for Telegram / Discord / WeChat

It is not intended for:
- deploying bots automatically
- creating real secrets
- mutating existing production teams in place

## Run

From this directory:

```bash
npx ts-node scripts/main.ts "帮我组建一个招投标团队，包括申报主管、信息雷达、材料撰写师，支持 Telegram 协作" --output-dir ./out
```

The generated team folder will be written into `./out/<team-slug>/`.

## Files

- `SKILL.md`: runtime usage guide
- `research/golden-cases.md`: source-pattern notes
- `references/team-patterns.md`: team structure reference
- `references/collaboration-rules.md`: collaboration principles
- `scripts/main.ts`: scaffold generator
- `scripts/team/`: document templates

## Notes

- The official skill root is the `agent-team-composer` directory under your OpenClaw skills folder.
- Ignore stray workspace copies created during earlier failed runs.

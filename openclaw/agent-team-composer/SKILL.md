---
name: agent-team-composer
description: 从自然语言团队需求生成 OpenClaw 多智能体团队脚手架，包括 SOUL.md、AGENTS.md、协作规则和 YAML 配置。用于“组建团队”“创建协作团队”“生成团队配置”等请求。
---

# Agent Team Composer

Use this skill when the user wants to:
- create a new OpenClaw team from natural language
- generate collaboration docs for a multi-agent squad
- scaffold SOUL / AGENTS / config files for Telegram, Discord, or WeChat collaboration

Do not use this skill for:
- editing one existing single agent only
- deploying bots automatically
- generating secrets or real credentials

## Inputs

Expected input is natural language, for example:

```text
帮我组建一个招投标团队，致力于招投标全流程支持。
团队包括：
- 申报主管：负责统筹协调
- 信息雷达：负责信息搜集
- 材料撰写师：负责材料写作
协作模式：并行
告警通道：Telegram
日报输出：Discord
```

## Output

Generate a team folder containing:
- `SOUL.md`
- `AGENTS.md`
- `CollaborationRules.md`
- `Contacts.md`
- `agent-config.yaml`

## Run

From this skill directory:

```bash
npx ts-node scripts/main.ts "<团队描述>" --output-dir ./out
```

Result:
- `./out/<team-slug>/`

## Notes

- The generator is implemented in:
  - `scripts/main.ts`
- Templates live in:
  - `scripts/team/`
- Canonical template file is:
  - `scripts/team/soul-template.md`

## Validation

Minimum validation before claiming completion:
- generator runs successfully
- at least one sample input produces all five output files
- no unresolved `{{placeholder}}` remains in generated output

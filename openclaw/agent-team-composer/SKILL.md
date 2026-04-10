---
name: agent-team-composer
description: "从自然语言团队需求生成 OpenClaw 多智能体团队脚手架，包括 SOUL.md、AGENTS.md、协作规则和 YAML 配置。Do NOT use for single-agent creation or modifying existing team configs."
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

## Production Patterns

Generated teams MUST follow the patterns in `references/production-patterns.md`:
- Pattern A: Self-propulsion protocol (auto_continue + 3 hard rules)
- Pattern B: Model fallback policy table
- Pattern C/D: Worker/TL standard workspace structure
- Pattern E: Standing orders JSON schema
- Pattern F: SOUL.md 瘦身 (<50 行 for new teams)
- Pattern G/H: Workspace cleanup thresholds + ghost role prevention

## When NOT to Use

- 用户只想创建单个 agent（直接手动创建即可）。
- 不用于修改已有团队的配置（用直接编辑）。
- 不用于非 OpenClaw 的多 agent 框架。

## Error Handling

- 自然语言描述模糊时，生成后让用户确认再创建文件。
- workspace 目录冲突时，提示用户选择新名称。
- 模板渲染失败时，报告缺少的变量。

## Internal Acceptance

- 生成的 SOUL.md、AGENTS.md、YAML 配置文件结构完整。
- 所有引用的协作规则和工具权限配置正确。
- validate-skill.sh 对生成的技能文件通过。

## Gotchas

- Agent name 必须是 lowercase-hyphen 格式，包含中文或大写会报错。
- 协作规则中的 agent 引用必须与 AGENTS.md 中定义的名字一致。
- 创建后需要重启 gateway 才能加载新 agent。

## Delivery Contract

- 输出所有创建的文件路径列表。
- 每个文件的作用简要说明。
- 后续步骤（如重启 gateway）一并告知。
**注意：本技能是大型流水线的一部分。Do **not** report completion to the user unless all dependent tools/scripts/skills have been verified as integrated.**not** report completion to the user unless all dependent tools/scripts/skills integration tests have passed.**

## Workflow Steps

1. Parse the user's natural language description to identify agents, roles, and collaboration rules.
2. Generate SOUL.md for each agent with personality and behavior.
3. Generate AGENTS.md with role assignments and interaction rules.
4. Create workspace directory and YAML configuration.
5. Validate the generated files pass structural checks.

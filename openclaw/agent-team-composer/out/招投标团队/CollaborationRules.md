# Collaboration Rules - 招投标团队

## Workflow

- Mode: 串行
- Description: 串行协作：上一位成员的输出是下一位成员的输入，适合审核链和依赖明确的流程。
- Max concurrent tasks: 1
- Timeout per agent: 300s
- Total timeout: 900s

## Routing Rules

- All external requests enter via the team TL.
- Work may be split across specialists only after task decomposition.
- Final user-facing output must be merged before delivery.

## Failure Rules

- Retry transient failures up to 3 times.
- Escalate ambiguous task boundaries to the TL.
- Do not silently drop tasks or outputs.

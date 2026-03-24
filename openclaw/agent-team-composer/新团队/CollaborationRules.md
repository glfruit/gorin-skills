# Collaboration Rules - 新团队

## Workflow

- Mode: 混合
- Description: 混合协作：并行采集与串行审核结合，适合真实团队的多阶段任务。
- Max concurrent tasks: 5
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

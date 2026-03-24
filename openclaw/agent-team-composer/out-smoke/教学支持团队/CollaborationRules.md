# Collaboration Rules - 教学支持团队

## Workflow

- Mode: 并行
- Description: 并行协作：多个成员同时处理不同子任务，再由 TL 汇总，适合采集、分析和生产并发任务。
- Max concurrent tasks: 3
- Timeout per agent: 300s
- Total timeout: 600s

## Routing Rules

- All external requests enter via the team TL.
- Work may be split across specialists only after task decomposition.
- Final user-facing output must be merged before delivery.

## Failure Rules

- Retry transient failures up to 3 times.
- Escalate ambiguous task boundaries to the TL.
- Do not silently drop tasks or outputs.

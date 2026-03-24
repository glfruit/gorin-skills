# Collaboration Rules - {{team_name}}

## Workflow

- Mode: {{workflow_mode_label}}
- Description: {{workflow_mode_desc}}
- Max concurrent tasks: {{max_concurrent}}
- Timeout per agent: {{timeout_per_agent}}s
- Total timeout: {{timeout_total}}s

## Routing Rules

- All external requests enter via the team TL.
- Work may be split across specialists only after task decomposition.
- Final user-facing output must be merged before delivery.

## Context-Aware Privacy

- 非私聊场景自动跳过：MEMORY.md、个人联系人详情、财务数据、原始日记
- 上下文类型不明确时，默认使用更严格的分级（机密优先）
- 工作邮箱等公共联系方式可以共享，私人联系方式不可

## Failure Rules

- Retry transient failures up to 3 times.
- Escalate ambiguous task boundaries to the TL.
- Do not silently drop tasks or outputs.
- Proactively report all failures with error details and context（用户看不到 stderr）。

## Governance

- 规则不跨文件重复。如果某条规则在 AGENTS.md 已存在，其他文件引用而非复制。
- 每个自动加载的文件都会消耗每次请求的 token 预算，只放必需内容。
- 详细文档和参考资料放在 docs/ 或 reference/ 目录，按需加载。

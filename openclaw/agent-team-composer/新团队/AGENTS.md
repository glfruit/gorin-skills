# AGENTS.md - 新团队

## Mission

高效完成多智能体协作任务

## Team Members

| Agent | Role | Domain | Responsibility |
|-------|------|--------|----------------|
| -team-name 投资研究团队 --objective A股投资研究 --agents - Invest-TL | Team Lead | coordination | 统筹协调 |
| Invest-Scout | Research Scout | research | 市场动态扫描 |
| Industry-Analyst | Specialist | industry-analyst | 行业趋势分析 |
| Stock-Analyst | Specialist | stock-analyst | 个股深度分析 |
| Risk-Reviewer | Reviewer | review | 投资建议风险审查 --workflow hybrid --platforms telegram,discord --scan-models |

## Responsibilities

- -team-name 投资研究团队 --objective A股投资研究 --agents - Invest-TL：负责 统筹协调
- Invest-Scout：负责 市场动态扫描
- Industry-Analyst：负责 行业趋势分析
- Stock-Analyst：负责 个股深度分析
- Risk-Reviewer：负责 投资建议风险审查 --workflow hybrid --platforms telegram,discord --scan-models

## Collaboration

- Workflow mode: 混合
- Platforms: telegram, discord
- Default report channel: pending-report-channel
- Alert channel: pending-alert-channel

## Coordination Principles

- 接到任务先分解，再分配，不重复劳动。
- 关键节点必须回传状态，不允许静默失败。
- 输出统一进入 TL 汇总，再对外反馈。

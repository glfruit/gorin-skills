---
type: reviewer
updated: 2026-03-27
based_on: code-review, harness-audit, de-ai-writing
---

# Reviewer 创建经验

## 核心模式

**Rubric 必须明确**：
- 每个检查项有清晰的通过/失败标准
- 严重度分级：error / warning / info（或 P0/P1/P2）
- 不留模糊地带——"可能有问题"不是 review 结果

**结构化输出**：
- JSON 格式给程序消费，人类可读格式给用户
- 每个发现包含：位置（文件:行号）、问题描述、严重度、建议修复
- 汇总统计：N error, M warning, K info

**范围可控**：
- 支持增量 review（只看 diff 或指定文件）
- 支持全量 review（扫描整个项目）
- 可以配置忽略规则或降低特定规则的严重度

## 常见陷阱

- 标准 太泛 → 什么都报 warning，信号被淹没
- 没有 severity 分级 → agent 不知道先修哪个
- 只报问题不给修复建议 → review 结果没人看
- 太慢（扫描整个 codebase） → 用户体验差，应该支持增量模式
- 规则不稳定（同一输入不同结果） → 失去可信度

## 质量信号

- Review 结果可以直接转化为 action items
- 重复运行相同输入得到相同结果（确定性）
- 覆盖率：能发现已知的常见问题类型
- 误报率低：标记为 error 的确实需要修复

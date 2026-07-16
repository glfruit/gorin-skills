---
type: library-internal
updated: 2026-03-27
based_on: example-library-skill, harness-audit, openclaw-nowledge-mem
---

# Library / Internal Skill 创建经验

## 核心模式

**不是给用户直接用的**：
- `user-invocable: false`，被其他 skill 或 agent 调用
- SKILL.md 重点是接口定义和调用约定，不是用户引导
- 文档面向开发者（其他 agent 或 skill creator）

**接口要明确**：
- 输入/输出 schema 用 JSON 或明确的类型标注
- 边界条件写清楚（空输入、超长输入、无效输入）
- 版本号跟着 skill 走，breaking change 要在 SKILL.md 标注

**轻量为王**：
- 内部 skill 不需要 When to Use / When NOT to Use 这些用户引导段
- 核心是：它能做什么、怎么调用、返回什么
- 复杂的内部 skill 也要有 Gotchas 段

## 常见陷阱

- 做了 user-invocable 的界面但实际没人直接用 → 浪费 token
- 接口不明确，调用方靠猜参数 → 隐性耦合
- 没有错误码约定 → 调用方无法区分暂时失败和永久失败
- 改了内部实现但没改版本号 → 上游调用方不知道 API 变了

## 质量信号

- 其他 skill 能通过 SKILL.md 快速理解怎么调用
- 输入/输出有示例，不是纯文字描述
- 有版本号和 changelog

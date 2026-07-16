---
type: meta-skill
updated: 2026-03-27
based_on: enhanced-skill-creator, skill-creator, ai-builder-digest
---

# Meta-Skill 创建经验

## 核心模式

**自我引用但不自我依赖**：
- Meta-skill 可以参考自身的设计模式（enhanced-skill-creator 就是例子）
- 但不能形成循环依赖（skill A 依赖 skill B，B 又依赖 A）
- 提供足够的独立文档，不用被调用也能理解

**方法论 > 模板**：
- Meta-skill 教的是"怎么做好"，不是"填什么字段"
- 每个规则要解释为什么，不是只说做什么
- 提供 golden examples 作为参照标准

**递归安全**：
- 明确哪些操作是递归安全的（可以用自己创建的 skill 再创建新 skill）
- 哪些操作不是（不能无限嵌套调用自己）
- 设置深度限制或退出条件

## 常见陷阱

- 规则太多太泛 → agent 被规则淹没，反而不如没有 skill
- 自身结构不符合自己制定的规范 → 失去可信度
- 过度抽象 → 新 skill creator 不知道从哪开始
- 不积累 creation-patterns → 每次创建都从零开始

## 质量信号

- 用自己创建的 skill 来创建新 skill 时，流程顺畅
- 自身的 SKILL.md 通过自己的 validate 脚本检查
- Creation-patterns 随着实际创建经验持续增长

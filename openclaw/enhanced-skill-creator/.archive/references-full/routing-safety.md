# Routing Safety Guide

## 目标
防止 skill 因 metadata 或 trigger 设计不当而误触发、泛滥触发或吞掉其他 skill 的路由机会。

## Critical 风险模式
### 1. Wildcard / Catch-all
禁止：
- `*`
- `.*`
- `any request`
- `all tasks`
- `everything`
- `general-purpose assistant`
- `use for all questions`

### 2. 无边界的通用描述
高风险示例：
- Handles coding tasks
- Helps with files
- Analyzes content
- Manages workflows

### 3. 缺少 negative triggers
skill 必须说明“不适用于什么”。

### 4. 抢占系统基础职责
若 skill 声称自己处理任意消息、通用问答、通用路由，应视为高风险，除非它本身就是 router/meta-skill 且经过单独审核。

## 强制规则
1. 禁止 wildcard trigger。
2. `description` 必须同时描述能力、使用场景和至少一个不适用场景。
3. 必须包含领域限定词，不能只有通用动词。
4. 新 skill 发布前应做 collision / overlap 检查。

## 推荐 description 形态
`Handles X for Y context. Use when ... Don't use it for ...`

## Negative Trigger 示例
- Don't use it for general coding tasks.
- Don't use it for unrelated repositories or generic file editing.
- Don't use it when the user only needs a one-line shell command.

## 发布前检查清单
- [ ] 没有 `*` 或 `.*`
- [ ] 没有 catch-all phrases
- [ ] 存在 negative triggers
- [ ] 领域限定词清晰
- [ ] 不与现有 skills 明显冲突

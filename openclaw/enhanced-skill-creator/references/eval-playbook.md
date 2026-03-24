# Eval Playbook

## 1. Discovery Validation
只给模型看 frontmatter 的 `name + description`，验证技能是否会被正确触发。

### 目标
- 生成 3 个应触发的 prompt
- 生成 3 个不应触发的 prompt
- 批评 description 是否过宽/过窄
- 提出重写建议

### 关注点
- false positive
- false negative
- 缺少 negative triggers
- 描述是否过于贪婪

## 2. Logic Validation
输入完整的 `SKILL.md` 与目录结构，让模型按真实请求模拟执行。

### 输出要求
- 当前在做什么
- 正在读哪个文件
- 正在跑哪个脚本
- 哪一步必须猜测
- 缺失了哪些前提

## 3. Execution Blocker Detection
要求模型标记：
- missing prerequisite
- missing file reference
- missing fallback
- ambiguous branch
- undefined environment assumption

## 4. Edge-Case QA
切换到“ruthless QA tester”模式，只提出 3–5 个高压问题，不直接修复。

### 聚焦点
- 环境前提
- 自定义配置
- 工具失败
- 兼容性风险
- fallback 缺失

## 5. Progressive Disclosure Review
检查：
- SKILL.md 是否过长
- 大模板是否应迁到 `assets/`
- 复杂规则是否应迁到 `references/`
- 重复脆弱逻辑是否应迁到 `scripts/`

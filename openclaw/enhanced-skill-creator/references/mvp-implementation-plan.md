# Enhanced Skill Creator MVP 实施方案

## 目标
将 `enhanced-skill-creator` 从“技能模板生成器”升级为“Skill Engineering Workbench”，覆盖生成、检查、评估、结构化增强与路由安全。

## 已确认的 MVP 范围
1. Skill 脚手架生成
2. `name/description` lint
3. Step-by-step instruction lint
4. Progressive disclosure 建议
5. Discovery validation 模板
6. Execution blocker detection
7. Routing safety 检查
8. Collision check（基础版）
9. `assets/` 模板建议
10. `scripts/` 下沉建议
11. Error handling 章节生成

## 核心产品决策
- `enhanced-skill-creator` 不只是生成器，而是工程化技能设计器。
- `Routing Safety` 是核心能力，不是附属功能。
- `*`、`.*`、catch-all trigger、无负边界描述视为高危/阻断问题。
- MVP 先强调“能检查、能建议、能生成草案”，暂不做激进自动重写。

## 风险优先级
### P1：系统级风险
- wildcard / catch-all trigger
- 缺少 negative triggers
- 与已有 skill 高重叠
- 无错误处理出口

### P2：结构与执行风险
- SKILL.md 过胖
- 流程非编号、分支不清
- 复杂模板直接塞主文件
- 脆弱重复逻辑未下沉到 `scripts/`

## 实施分期
### Sprint 1：规则底座
- 明确 metadata 规则
- 明确 routing safety 规则
- 明确 instruction/style 规则
- 更新 `SKILL.md` 与参考文档

### Sprint 2：结构增强
- 补充 `assets/` 模板
- 补充 `references/` 指南
- 形成 discovery / error-handling / routing playbooks

### Sprint 3：静态分析脚本
- 增强 `validate-skill.sh`
- 增加 routing safety 检查
- 增加 step-by-step / placeholder / negative-trigger 检查

### Sprint 4：分析与生成增强
- blocker detection
- overlap / collision check（基础版）
- error handling 草案生成
- scaffold 能力增强

## MVP 交付标准
### 必须能拦住
- trigger 中使用 `*`
- catch-all 描述
- 缺少 negative triggers
- 全文无编号工作流
- 缺少 Error Handling
- 明显不存在的资源引用

### 必须能建议
- 何时迁移到 `references/`
- 何时创建 `assets/` 模板
- 何时把脆弱流程下沉到 `scripts/`

## 首批落地文件
- `references/routing-safety.md`
- `references/eval-playbook.md`
- `assets/discovery-validation-prompt.md`
- `assets/error-handling-template.md`
- 更新 `SKILL.md` 以纳入新规则与资源

## 暂不纳入首批自动化
- 自动重写整个 SKILL.md
- 自动迁移段落
- 自动生成复杂脚本实现

## 下一步
1. 更新 `SKILL.md` 中的质量规则与资源索引
2. 强化 `validate-skill.sh` 的 routing safety / workflow / error handling 检查
3. 视需要新增 `detect-overlap.py` 或 shell 原型脚本
4. 用统一 JSON schema 收敛脚本输出，并补充 blocker detection、fix suggestions、shell quality runner

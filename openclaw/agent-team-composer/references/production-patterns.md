# Production-Tested Team Patterns

> 从 6 个 TL 团队 + 40+ worker 的实际运营中提炼的模式。
> 2026-03-25/26 跨团队审计后固化。

## Pattern A: Self-Propulsion Protocol（自推进协议）

**问题**: TL 收到 standing-order 后只汇报不执行，session 结束任务停滞。

**方案**: 四层保障：

| 层级 | 位置 | 规则 |
|------|------|------|
| JSON | standing-orders.json | `auto_continue: true` |
| SOUL | SOUL.md Hard Rules | "汇报不是停点"、"禁止零执行汇报"、"Heartbeat 期间必须执行" |
| HEARTBEAT | HEARTBEAT.md | 步骤 1 = "读取并执行第一个 pending action"（不是"读取"） |
| AGENTS | AGENTS.md | Session 启动时消费 standing-orders，有 pending action 立即执行 |

**共享协议位置**: `~/.openclaw/shared/protocols/standing-order-auto-continue.md`

**Agent 引用方式**: SOUL.md 中直接内联 3 条 hard rules，AGENTS.md 引用共享协议路径。

## Pattern B: Model Fallback Policy Table

**问题**: AGENTS.md 声明的模型与 openclaw.json 实际配置不一致。

**方案**: AGENTS.md 中用表格格式，明确列出每个角色的主模型和 fallback。

```markdown
## Model Fallback Policy

| 角色 | 主模型 | Fallback 链 |
|------|--------|-------------|
| {tl-name} | gpt-5.4 | glm-5-turbo → k2p5 |
| {worker-1} | glm-5-turbo | k2p5 → gpt-5.4 |
| {worker-2} | glm-5-turbo | k2p5 → gpt-5.4 |
| {specialist} | k2p5 | glm-5-turbo → gpt-5.4 |
```

**规则**:
- 质量关键角色（TL、Critic、Designer）：gpt-5.4
- 通用生产角色：glm-5-turbo
- 编码角色：k2p5
- 轻量角色（文档打包、MOOC）：glm-4.7-flashx 或 glm-5-turbo
- 通用 fallback：primary → k2p5 → glm-5-turbo → gpt-5.4
- openclaw.json 中 agents.list 必须与 AGENTS.md 保持一致

## Pattern C: Worker Workspace 标准结构

**最小文件集**:
```
workspace-{team}-{role}/
├── SOUL.md          # 40-50 行：性格 + 3-4 hard rules
├── AGENTS.md        # 50-70 行：职责 + 模型 + standing-order 消费
├── IDENTITY.md      # 名称 + emoji + 一句话定位
└── memory/          # 日记目录
```

**共享 hard rules（所有 worker 必须有）**:
1. **问题先自救**: 遇到错误先查文档/日志/代码，3 分钟内无进展再求助
2. **汇报附证据**: 修改了什么文件、跑了什么命令、得到了什么结果
3. **Standing Order 消费**: session 启动时读取 TL 的 standing-orders.json，执行未完成 action
4. **不自作主张**: 不修改非职责范围内的文件，不确定时先问

## Pattern D: TL Workspace 标准结构

**最小文件集**:
```
workspace-{team}-tl/
├── SOUL.md              # 50-65 行：性格 + hard rules（含自推进 3 条）
├── AGENTS.md            # 角色定义 + 模型策略 + 协作流程
├── HEARTBEAT.md         # 执行驱动的巡检清单
├── TEAM_CONTEXT.md      # 团队结构 + 约束
├── IDENTITY.md
├── USER.md
├── TOOLS.md
├── standing-orders.json # 统一 schema
├── data/                # 团队数据
├── tasks/               # 任务产出
└── memory/              # 日记
```

**HEARTBEAT.md 必须包含**:
1. 读取并执行 standing-orders 第一个 pending action
2. Cross-check: active standing-order + 零执行 = 🔴 blocked

## Pattern E: Standing Orders JSON Schema

**统一 schema**: `~/.openclaw/shared/schemas/standing-orders-schema.json`

**核心结构**:
```json
{
  "status": "active",
  "task": {
    "name": "任务名称",
    "next_actions": [
      {
        "action": "具体行动描述",
        "status": "pending",
        "blocking": false,
        "assigned_to": "可选"
      }
    ],
    "acceptance": "完成标准描述",
    "auto_continue": true
  }
}
```

**校验脚本**: `~/.openclaw/skills/harness-audit/scripts/validate_standing_orders.py`

## Pattern F: SOUL.md 瘦身原则

**SOUL.md 只放**:
- 性格/定位（2-3 句）
- 价值观（2-3 条）
- Hard Rules（3-5 条，影响行为的红线）
- 绝对不超过 50 行（新团队标准）

**SOUL.md 不放**:
- 工作流程 → AGENTS.md
- 检查清单 → AGENTS.md 或 references/
- 模板/示例 → references/
- 指标/KPI → AGENTS.md

**瘦身流程**:
1. 读 SOUL.md，标记非性格/非红线内容
2. 迁移到 AGENTS.md 或 references/
3. SOUL.md 补充共享协议引用（如 standing-order-auto-continue.md）

## Pattern G: Workspace 清理阈值

| 文件数 | 严重度 | 行动 |
|--------|--------|------|
| < 20 | ✅ 正常 | — |
| 20-30 | ⚠️ P2 | 检查可归档文件 |
| 30-80 | 🔶 P1 | 归档历史文件到 .archive/ |
| > 80 | 🔴 P1 严重 | 立即清理 |

**排除目录**: skills/, memory/, .git/, node_modules/, .archive/, .openclaw/

## Pattern H: Ghost Role 清理

**常见空壳角色来源**:
- 早期规划但从未创建 workspace
- 重命名后旧 ID 未清理
- invest-{role} 等子角色只有 AGENTS.md 引用但未注册

**清理流程**:
1. `openclaw.json` agents.list ↔ workspace-* 目录双向校验
2. 有 agents.list 但无 workspace → 移除（除非是内置 agent 如 main/claude/codex）
3. 有 workspace 但无 agents.list → 检查是否是废弃 workspace，考虑归档

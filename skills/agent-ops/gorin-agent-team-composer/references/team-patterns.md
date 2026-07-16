# Agent Team Composition Patterns

## Team Composition Patterns

### Pattern 1: Team Directory Structure

```
Team Name:招投标团队
├── pm (申报主管)
│   ├── Role: coordination
│   ├── Capabilities: task delegation, SWOT analysis
│   └── IM: dingtalk|telegram|discord|wechat
├── information-radar (信息雷达)
│   ├── Role: scanning
│   ├── Capabilities:招标信息扫描,爬取
│   └── IM: dingtalk|telegram|discord|wechat
├── writer (材料撰写师)
│   ├── Role: content
│   ├── Capabilities:方案撰写,文档整理
│   └── IM: dingtalk|telegram|discord|wechat
└── shared/
    ├── documents/        # 共享文档区（A2A传递长文本）
    └── templates/        # 模板文件
```

### Pattern 2: SOUL.md Structure

**Hierarchy**:
```
SOUL.md
├── # Agent 核心价值观
│   ├── 信任队友
│   ├── 委派任务
│   ├── 汇报闭环
│   └── 共享文档
└── # 团队协作规范
    ├── 任务委派流程
    ├── 汇报协议
    └── 冲突解决机制
```

**Values**:
- **信任队友**: 相信队友会完成任务，不重复做
- **委派任务**: 理解任务后委派，明确期望
- **汇报闭环**: 主动汇报进展，任务完成后交付完整成果
- **共享文档**: 使用 shared zone 传递长文本，不通过群消息

### Pattern 3: AGENTS.md Structure

```
AGENTS.md
├── # 团队成员
│   ├── pm (申报主管): coordination
│   ├── information-radar (信息雷达): scanning
│   └── writer (材料撰写师): content
├── # 协作流程
│   ├── 任务委派: User → pm → information-radar
│   └── 汇报: information-radar → pm → User
├── # 工具流程
│   ├── IM: dingtalk/telegram/discord
│   ├── 文件共享: shared zone
│   └── 部署: manual confirmation required
└── # 可用工具
    ├── 招标信息源
    ├── 文档模板
    └── 分析工具
```

### Pattern 4: IM Platform Integration

| Platform | Auth | Capabilities | Session |
|----------|------|--------------|---------|
| DingTalk | ClientID + Secret | text, image, file | BotCode |
| Telegram | Bot Token | text, photo, document | session_id |
| Discord | Bot Token + Guild ID | text, image, file | channel_id |
| WeChat | Corp ID + Secret | text, image, file | Agent ID |

### Pattern 5: Double-Helix Protocol

```
Phase 1: Delegation
    User → @pm
    ↓
    pm → sessions_send(@information-radar, task)
    ↓
    information-radar receives task

Phase 2: Reporting
    information-radar → sessions_send(@pm, result)
    ↓
    pm receives ack and wakes up
    ↓
    pm → sessions_send(@User, final result)
    ↓
    User receives final result
```

### Pattern 6: Shared File Zone

```
shared/
├── documents/            # 长文本传递
│   ├── input/           # 输入文件
│   ├── output/          # 输出文件
│   └── intermediate/    # 中间文件
└── templates/           # 模板文件
    ├── team-structure.json
    ├── delegation-template.md
    └── reporting-template.md
```

### Pattern 7: Agent Configuration Template

```json
{
  "agents": [
    {
      "id": "unique_id",
      "name": "Agent Name",
      "role": "role_type",
      "im": "platform_name",
      "a2a_enabled": true,
      "session_visible": ["all"],
      "capabilities": ["capability_1", "capability_2"],
      "tools": ["tool_1", "tool_2"]
    }
  ],
  "collaboration": {
    "trust_agents": true,
    "enable_delegation": true,
    "reporting_protocol": "double-helix"
  }
}
```

### Pattern 8: Anti-Slop Rules

**Never**:
1. Hardcode credentials
2. Assume OpenClaw version
3. Implicit delegation (without ack)
4. Rely on group chat for long text
5. Use timeout-based assume failure

**Always**:
1. Use placeholders in templates
2. Use portable formats (JSON + Markdown)
3. Explicit delegation + ack
4. Use shared file zone
5. Confirm before deployment

### Pattern 9: Team Composition Workflow

```
User Input → Natural language description
    ↓
Extract elements (team, members, IM)
    ↓
Generate SOUL.md (values + rules)
    ↓
Generate AGENTS.md (directory + workflow)
    ↓
Generate agents.json (configuration)
    ↓
Output project structure
```

### Pattern 10: Output Structure

```
team-project/
├── agents.json              # 配置文件（machine-readable）
├── README.md                # 使用说明（human-readable）
├── DEPLOYMENT.md            # 部署指南
├── agents/
│   ├── agent-id-1/
│   │   ├── SOUL.md          # 价值观与规范
│   │   ├── AGENTS.md        # 信息与工具
│   │   └── config.json      # Agent专用配置
│   └── agent-id-2/
│       └── ...
└── shared/                  # 共享文件（A2A）
    ├── documents/
    └── templates/
```

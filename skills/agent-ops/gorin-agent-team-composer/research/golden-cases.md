# Agent Team Composer - Golden Cases Research

## 1. Original Project: agentrun-team

**Context**: OpenClaw 中的 agentrun-team skill 用于自动化组建多智能体协作团队。

**Core Insights**:
- Focus on **team collaboration patterns** (delegation, reporting, reliability)
- Automated configuration: user describes team, auto-generate configs
- SOUL.md + AGENTS.md pattern for team意识 and communication
- Double-helix reporting protocol for reliability
- IM bindings: DingTalk, Telegram, Discord, WeChat
- A2A permissions and session visibility

**Key Features**:
1. **Collaboration norms standardization**:委派、汇报、可靠性标准化
2. **Configuration automation**:用户只需描述需求，自动生成全部配置
3. **Customizable members**:用户可定义不同业务场景的团队成员

**Collaboration Protocol**:
```
User → 委派任务
    ↓
委派 Agent 发送 sessions_send → 下游 Agent
    ↓
下游 Agent 完成任务后主动汇报
    ↓
汇报通过 sessions_send 回传给委派 Agent
    ↓
委派 Agent 收到回执后被精准唤醒
```

**Anti-Patterns**:
- No implicit delegation → explicit sessions_send + ack
- No relying on group chat → use shared file zone
- No timeout-based assume failure → explicit double-helix

## 2. OpenClaw/Skill Structure Patterns

### Local Skills Reference:

#### visual-knowledge-explainer (recently created)
- **Two-Dimension Selection**: Content type + Template/Theme
- **Auto Content Recognition**: Identify 教材/培训/知识讲解/流程/对比/技术
- **Template Gallery**: 6 HTML templates for different scenarios
- **Progressive Disclosure**: SKILL.md + references/

#### docx/pptx/pdf
- **File-based workflows**: Input file → Modify/Convert → Output file
- **Template system**: Pre-defined document structures
- **Output conventions**: File naming, directory structure

### Pattern Extraction:

| Pattern | Example from visual-knowledge-explainer |
|---------|-----------------------------------------|
| Auto Recognition | Content type detection → Template selection |
| Template Gallery | 6 templates for different content types |
| Progressive Disclosure | SKILL.md + references/ |
| Output Format | HTML + Markdown + Screenshot |

## 3. Multi-Agent Team Patterns

### Team Composition Structure:

```
Team
├── Member 1 (pm)
│   ├── ID: unique identifier
│   ├── Role: coordination
│   ├── IM: dingtalk|telegram|discord|wechat
│   ├── A2A: enabled
│   └── Session: visible to team
├── Member 2 (information-radar)
│   ├── ID: unique identifier
│   ├── Role: scanning
│   ├── IM: dingtalk|telegram|discord|wechat
│   ├── A2A: enabled
│   └── Session: visible to team
└── Member 3 (writer)
    ├── ID: unique identifier
    ├── Role: content
    ├── IM: dingtalk|telegram|discord|wechat
    ├── A2A: enabled
    └── Session: visible to team
```

### SOUL.md for Teams:

**Core Values**:
- Trust agents (don't redo work)
- Delegate properly
- Report explicitly
- Share documents

**Collaboration Rules**:
- Delegate after understanding task
- Wait for ack (not poll)
- Share files in shared zone
- Report in group chat

### AGENTS.md for Teams:

**Team Directory**:
- Member list with ID, role, IM, capabilities
- Team workflow description
- Delegate instructions

**Configuration**:
- IM credentials (DingTalk, Telegram, Discord, WeChat)
- A2A permissions
- Session visibility rules

## 4. IM Platform Configurations

### DingTalk (钉钉)
- RobotCode based authentication
- Client ID + Client Secret
- Enterprise internal app
- Support: text, image, file

### Telegram
- Bot Token
- @BotFather created bot
- Support: text, photo, document
- Session visibility via session_id

### Discord
- Bot Token
- Application ID
- Guild ID
- Channel ID
- Support: text, image, file

### WeChat (微信)
- Corp ID + Secret
- Agent ID
- Support: text, image, file

## 5. Anti-Pattern Analysis

### What NOT to Do:

1. **No hardcoded credentials** - Use placeholders in templates
2. **No assuming OpenClaw version** - Use portable configurations
3. **No implicit delegation** - Explicit sessions_send + ack
4. **No relying on group chat** - Use shared file zone for long text
5. **No timeout assume failure** - Explicit reporting protocol

### What TO Do:

1. **Double-helix protocol** - Explicit delegation and reporting
2. **Shared file zone** - For document sharing
3. **Portable formats** - JSON/YAML + Markdown
4. **Clear documentation** - SOUL.md + AGENTS.md
5. **User confirmation** - Before deployment

## 6. Requirement from agentrun-team

### Core Requirements:
1. **Collaboration norms standardization** -委派/汇报/可靠性规范
2. **Configuration automation** -用户描述 → 自动生成配置
3. **Team member customization** -用户定义成员

### From user's perspective:
- Input: Natural language description
- Output: Complete project structure (JSON + Markdown)
- Action: User confirms before deployment
- IM support: Telegram/Discord/WeChat

## 7. Skill Design Decision

### This skill is NOT:
- A plugin implementation
- An agent deployment script
- A template for OpenClaw config

### This skill IS:
- A **Process Guide** for team composition
- A **template generator** for agent configurations
- A **documentation guide** for team意识

### Target workflow:
```
User: "帮我组建一个招投标团队"
    ↓
Skill: Extract team elements
    ↓
Skill: Generate team project structure
    ↓
User: Review configuration
    ↓
User: Confirm deployment
```

## 8. Template Planning

### Core Templates:

**Required**:
1. `agent-config.json` - Agent configuration (machine-readable)
2. `sooul-template.md` - SOUL.md template (human-readable)
3. `agents-template.md` - AGENTS.md template (human-readable)
4. `team-contacts.md` - Team directory
5. `collaboration-rules.md` - Collaboration norms

**Optional (per IM)**:
- `im-config-telegram.md` - Telegram specific config
- `im-config-discord.md` - Discord specific config
- `im-config-wechat.md` - WeChat specific config

### Script Reference:

| Script | Purpose |
|--------|---------|
| `main.ts` | Entry point |
| `detect-intent.ts` | Detect team composition intent |
| `extract-team-elements.ts` | Extract from natural language |
| `generate-team-config.ts` | Generate project structure |
| `deploy-validate.sh` | Validation before deployment |

### Output Directory:

```
team-project/
├── agents.json              # Configuration (machine-readable)
├── README.md                # Usage guide
├── DEPLOYMENT.md            # Deployment guide
└── agents/
    ├── agent-id-1/
    │   ├── SOUL.md          # Values & rules (human-readable)
    │   ├── AGENTS.md        # Info & tools (human-readable)
    │   └── config.json      # Agent-specific config
    ├── agent-id-2/
    │   └── ...
    └── shared/              # Shared files for A2A
        ├── documents/
        └── templates/
```

## 9. Anti-Slop Rules

1. **No hardcoded credentials** - Always use placeholders
2. **No deployment code** - Only generate configuration
3. **No version assumption** - Use portable formats
4. **No implicit delegation** - Always use explicit protocol
5. **No group chat assumption** - Always use shared file zone

## 10. Eval Prompts

### Eval A: 招投标团队
- [ ] Team structure: pm, information-radar, writer
- [ ] SOUL.md: Trust agents, delegate properly
- [ ] AGENTS.md: Team directory, workflow
- [ ] IM config: DingTalk credentials
- [ ] Collaboration protocol: Double-helix

### Eval B: 内容创作团队
- [ ] Team structure: content-analyst, writer, editor
- [ ] SOUL.md: Share documents, delegate tasks
- [ ] AGENTS.md: Team directory, collaboration rules
- [ ] IM config: Telegram credentials
- [ ] Documentation: README + DEPLOYMENT

### Eval C: 客服团队
- [ ] Team structure: triage, specialist, manager
- [ ] SOUL.md: Trust agents, report explicitly
- [ ] AGENTS.md: Team directory, escalation rules
- [ ] IM config: WeChat credentials
- [ ] Anti-slop: No hardcoded credentials

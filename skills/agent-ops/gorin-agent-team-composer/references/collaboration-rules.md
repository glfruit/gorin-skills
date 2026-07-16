# Collaboration Rules for Multi-Agent Teams

## SOUL.md Collaboration Rules

## Trust Agents

- 相信队友会完成任务
- 委派任务后不重复做
- 收到任务后主动推进

## Delegate Properly

- 理解任务后委派
- 明确委派期望（task description, deadline）
- 等待 ack 再继续

## Report Explicitly

- 任务完成后主动汇报
- 提供完整交付物
- 清晰标注状态（pending/completed/failed）

## Share Documents

- 使用 shared zone 传递长文本
- 不通过群消息传递长文本
- 文件命名规范：`team-task-YYYYMMDD-{input|output}.md`

## A2A Protocol

- 启用 A2A 通讯
- Session 可见性白名单
- 不依赖群消息唤醒

---

## AGENTS.md Collaboration Rules

## Team Directory

| Agent ID | Name | Role | Capabilities | IM |
|----------|------|------|--------------|-----|
| pm | 申报主管 | coordination | delegation, SWOT | DingTalk |
| information-radar | 信息雷达 | scanning |招标扫描 | DingTalk |
| writer | 材料撰写师 | content | 方案撰写 | DingTalk |

## Workflow

### Delegation Flow

```
User → @pm
    ↓
pm → sessions_send(@information-radar, "请扫描浙江政府采购网")
    ↓
information-radar → sessions_send(@pm, "扫描结果：...")
```

### Reporting Flow

```
information-radar → sessions_send(@pm, "任务完成，结果如下：...")
    ↓
pm → sessions_send(@User, "最终结果：...")
```

## IM Credentials

| Platform | Client ID | Secret | Agent ID |
|----------|-----------|--------|----------|
| DingTalk | ${DT_CLIENT_ID} | ${DT_SECRET} | ${DT_AGENT_ID} |
| Telegram | ${TG_BOT_TOKEN} | - | - |
| Discord | ${DC_BOT_TOKEN} | - | ${DC_GUILD_ID} |

---

## Anti-Slop Rules

1. **No Hardcoded Credentials** - 使用占位符 ${PLACEHOLDER}
2. **No Implicit Delegation** - 必须 sessions_send + ack
3. **No Group Chat for Long Text** - 使用 shared zone
4. **No Timeout Assume Failure** - 显式汇报协议
5. **No Version Assumption** - 使用 portable formats

---
name: safe-mode
description: "Session-scoped safety modes for destructive or sensitive operations. Activate via /careful, /freeze, or /dry-run keywords. Do NOT use for routine operations or read-only tasks."
---


# safe-mode - Session-Scoped Safety Modes

Temporary safety constraints activated by keywords in user messages. Unlike persistent config changes, these are **session-only** — they expire when the conversation resets or a new session starts.

## Activation Keywords

| Keyword | Mode | Effect |
|---------|------|--------|
| `/careful` | **Confirmation Mode** | Ask before any write operation (edit, write, exec with writes, delete) |
| `/freeze` | **Read-Only Mode** | Block all write operations. Only read, search, and analyze allowed |
| `/dry-run` | **Preview Mode** | Show what *would* happen without executing. For exec: echo commands instead of running. For edits: show diff preview |

## Deactivation

| Keyword | Effect |
|---------|--------|
| `/unfreeze` | Remove all safety constraints |
| `/normal` | Same as /unfreeze |

## How It Works

1. User sends a message containing an activation keyword
2. Agent acknowledges and applies the constraint for the **remainder of the session**
3. Agent **must refuse** violating operations and explain what was blocked
4. Session reset (`/new`) clears all safety modes

## Behavior Details

### /careful Mode

Before any write operation, agent must:
1. Describe what it's about to do
2. Wait for explicit user confirmation (yes/go/approve)
3. Only proceed after confirmation received

Applies to:
- `write` tool (file creation/overwrite)
- `edit` tool (file modification)
- `exec` with commands that modify files (`rm`, `mv`, `curl -o`, `pip install`, `npm install`, etc.)
- `message` with `action=send` to external channels
- Any tool that produces side effects outside the workspace

Does NOT apply to:
- `read` tool
- `exec` with read-only commands (`cat`, `grep`, `ls`, `openclaw status`, etc.)
- `web_fetch`
- `browser` read-only actions (`snapshot`, `screenshot`)
- `memory_search`, `nowledge_mem_*` read operations

### /freeze Mode

**All write operations are blocked.** Agent must refuse and suggest alternatives:

| Operation | Refusal message |
|-----------|----------------|
| `write` | "🔒 Freeze active — write blocked. Use /unfreeze to allow writes." |
| `edit` | "🔒 Freeze active — edits blocked. Use /unfreeze to allow writes." |
| `exec` with writes | "🔒 Freeze active — destructive command blocked. Read-only alternatives: [suggest grep/cat/jq/etc]" |
| `message` send | "🔒 Freeze active — external messages blocked. Use /unfreeze to allow." |

Allowed operations (same as /careful exceptions):
- All read-only tools
- `sessions_spawn` (spawning agents for background work is OK)
- TTS, canvas display

### /dry-run Mode

For each write operation:
1. Show the command or diff that *would* be applied
2. Do NOT execute
3. End with: "Dry-run mode active — nothing was changed. Remove /dry-run to execute."

For `exec`: show the command wrapped in `echo` or prefix with `# DRY-RUN:`.
For `edit`: show the diff without applying.
For `write`: show the file content that *would* be written.

## Gotchas

- **Safety modes are agent-honor, not system-enforced.** The LLM must follow these rules voluntarily. Always verify the agent respects the mode.
- **Sub-agents inherit the conversation context but not the mode state.** If you spawn a subagent during /freeze, add mode instructions to the task prompt.
- **`/careful` can be chatty.** For batch operations (e.g., updating 10 files), ask the user to approve all at once instead of per-file.
- **Compaction may lose mode state.** If context is compacted mid-session, remind the agent of the active mode.
- **Multiple modes don't stack.** `/careful` + `/freeze` = `/freeze` (stricter wins).

## Usage Examples

**User**: `/careful` then delete all temp files in ~/Downloads older than 30 days
**Agent**: 🔒 Careful mode active. I plan to run:
```
find ~/Downloads -type f -mtime +30 -print
```
This will find files older than 30 days. Shall I list them first before deleting?

---

**User**: `/freeze` show me the current openclaw config
**Agent**: 🔒 Freeze active. Reading config...
[shows config]

**User**: now fix the controlUi origins
**Agent**: 🔒 Freeze active — edits blocked. Use `/unfreeze` to allow writes.

---

**User**: `/dry-run` rename all .js files to .ts in src/
**Agent**: 🔍 Dry-run mode. These files would be renamed:
- src/index.js → src/index.ts
- src/utils.js → src/utils.ts
- src/parser.js → src/parser.ts

Nothing was changed. Remove /dry-run to execute.

## When NOT to Use

- 不用于日常操作（安全模式限制功能，影响效率）。
- 不用于只读操作（安全模式主要是保护写入）。
- 用户明确知道风险并要求跳过安全检查时。

## Error Handling

- 安全模式激活失败时，检查关键词匹配逻辑。
- 误触发时，用户可以手动退出安全模式。
- 安全模式下执行了危险操作时，立即停止并报告。

## Internal Acceptance

- 安全模式正确激活/退出。
- 激活期间所有写入操作被拦截或需确认。
- 退出后所有功能恢复正常。

## Delivery Contract

- 安全模式状态变更时明确通知用户。
- 拦截的操作记录并展示给用户确认。
**注意：本技能是大型流水线的一部分。Do **not** report completion to the user unless all dependent tools/scripts/skills have been verified as integrated.**not** report completion to the user unless all dependent tools/scripts/skills integration tests have passed.**

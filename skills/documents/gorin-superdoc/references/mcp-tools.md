# MCP Tools Reference

All tools prefixed with `superdoc__superdoc_`. Available globally to all agents.

## Session Management

| Tool | Params | Returns |
|------|--------|---------|
| `open` | `path: str` | `session_id` |
| `save` | `session_id, out?: str` | saved path |
| `close` | `session_id` | void |
| `info` | `session_id` | word/char/paragraph counts, outline, capabilities |
| `get_text` | `session_id` | full plain text |
| `get_node` | `session_id, address: str` (JSON) | node details |

## Search

| Tool | Params | Returns |
|------|--------|---------|
| `find` | `session_id, pattern?: str, type?: str` | `matches[]` + `context[].textRanges[]` |

**Key**: `context[].textRanges[]` contains `TextAddress` objects for mutation targets.
Format: `{"kind":"text","blockId":"...","range":{"start":N,"end":N}}`

## Mutation (all accept `suggest: bool` for tracked changes)

| Tool | Params | Description |
|------|--------|-------------|
| `replace` | `session_id, text, target: str` (JSON TextAddress) | Replace text at range |
| `insert` | `session_id, text, target: str` (JSON TextAddress) | Insert text at position |
| `delete` | `session_id, target: str` (JSON TextAddress) | Delete text at range |
| `format` | `session_id, style, target: str` (JSON TextAddress) | Toggle bold/italic/underline/strikethrough |
| `create` | `session_id, type, text?, level?, at?: str, suggest?` | Create paragraph or heading |

## Comments

| Tool | Params |
|------|--------|
| `add_comment` | `session_id, text, target: str` (JSON) |
| `list_comments` | `session_id, include_resolved?: bool` |
| `reply_comment` | `session_id, comment_id, text` |
| `resolve_comment` | `session_id, comment_id` |

## Tracked Changes

| Tool | Params |
|------|--------|
| `list_changes` | `session_id, type?, limit?, offset?` |
| `accept_change` | `session_id, id` |
| `reject_change` | `session_id, id` |
| `accept_all_changes` | `session_id` |
| `reject_all_changes` | `session_id` |

## Lists

| Tool | Params |
|------|--------|
| `insert_list` | `session_id, target: str` (JSON), position: "before"\|"after", text` |
| `list_set_type` | `session_id, target: str` (JSON), kind: "ordered"\|"bullet"` |

---
name: superdoc
description: "Edit Word documents (.docx) using SuperDoc MCP tools or CLI. Use when the user asks to find-and-replace, insert, delete, format, add comments, or make tracked changes in a .docx file. Triggers: 'superdoc', 'edit docx', 'word edit', 'tracked changes', 'review document', '批注', '修订', '审阅文档'. Also use when reading/analyzing .docx that needs mutation. Do NOT use for PDFs, creating new .docx from scratch (use docx skill), spreadsheets, or non-.docx files."
triggers:
  - "superdoc"
  - "edit docx"
  - "tracked changes"
  - "review document"
  - "批注"
  - "修订"
  - "审阅文档"
  - "修订模式"
user-invocable: true
agent-usable: true
readiness: production-ready
---

# SuperDoc — AI-native .docx Editing

Read, search, edit, and review Word documents with tracked changes and comments.

## When to Use / When NOT to Use

**Use when:** editing existing .docx, reviewing with tracked changes/comments, AI-assisted doc collaboration, reading .docx for structured analysis.

**Do NOT use when:** creating new .docx from scratch → `docx` skill; PDFs → `pdf` skill; .xlsx/.pptx → `xlsx`/`pptx` skill; Obsidian vault → `pkm-*` skills; git code review → `code-review` skill.

## Interface Decision

| | MCP Tools (default) | CLI Wrapper (advanced) |
|--|--|--|
| **Access** | Built-in: `superdoc__superdoc_*` | Script: `superdoc-edit.sh` |
| **Session** | Per-call (auto lifecycle) | Persistent (open → edit → save → close) |
| **Capabilities** | 23 core tools | 150+ operations |
| **Track changes** | `suggest=true` | `changeMode=tracked` |

**Rule**: Default MCP. Use CLI for batch ops, tables, footnotes, hyperlinks, diff, multi-step pipelines. Never mix both on same file.

## MCP Workflow

1. **Open**: `superdoc__superdoc_open(path)` → `session_id`
2. **Read**: `superdoc__superdoc_get_text(session_id)` / `get_info` / `get_markdown`
3. **Search**: `superdoc__superdoc_find(session_id, pattern="关键词")` → `context[].textRanges[]`
4. **Mutate**: `replace` / `insert` / `delete` / `format` / `create` — all accept `suggest=true`
5. **Review**: `add_comment` / `list_changes` / `accept_all_changes`
6. **Save**: `superdoc__superdoc_save(session_id)`
7. **Close**: `superdoc__superdoc_close(session_id)`

**⚠️ CRITICAL**: `find()` returns `matches[]` (block addresses) + `context[].textRanges[]` (text addresses). Always use `textRanges[]` as mutation targets.

Full tool reference: `references/mcp-tools.md`

## CLI Workflow

Script: `scripts/superdoc-edit.sh` (symlink to `/Users/gorin/doc-collab/superdoc-edit.sh`)

```bash
superdoc-edit open /path/file.docx
superdoc-edit text /path/file.docx        # full text
superdoc-edit info /path/file.docx        # metadata + outline
superdoc-edit query /path/file.docx "文本" # → mutation refs
superdoc-edit replace-ref /path/file.docx "<ref>" "新内容" [tracked]
superdoc-edit save /path/file.docx
superdoc-edit close /path/file.docx
```

Advanced operations (tables, footnotes, hyperlinks, diff, etc.): `references/cli-operations.md`

## Gotchas

1. MCP `target` must come from `context[].textRanges`, never `matches[]`
2. `suggest=true` doesn't modify the document — changes are tracked for human review
3. CLI session tracked in `/tmp/superdoc-sessions/` — auto-managed by wrapper
4. CLI operation IDs: `doc.replace`, `track-changes.list` (dot notation, not camelCase)

## Error Handling

| Error | Fix |
|-------|-----|
| `NO_ACTIVE_DOCUMENT` | Re-run `open` |
| `MATCH_NOT_FOUND` | Check spelling, try `get-text` first |
| `AMBIGUOUS_MATCH` | Narrow pattern, add `--limit 1` |
| `TARGET_NOT_FOUND` | Re-query for fresh ref |
| Session leaked | Always pair open with close |

## Internal Acceptance
- **Happy-path**: Open test doc → query "待完善" → get refs → verify snippet matches
- **Mutation test**: Open → find → replace with suggest=true → list_changes shows 1 entry → reject_all → close
- **CLI test**: `superdoc-edit open/info/text/query/save/close` all return expected output

## Delivery Contract
All agents with SuperDoc MCP access can edit .docx without extra config. CLI path available for advanced operations. Skill is ready for teaching team integration.

## References

| File | Content |
|------|---------|
| `references/mcp-tools.md` | Complete MCP tool parameter reference |
| `references/cli-operations.md` | Advanced CLI operations catalog |
| `scripts/superdoc-edit.sh` | Agent-friendly CLI wrapper |

## Dependencies
- MCP: globally registered, zero config
- CLI: Python 3.12 venv at `/Users/gorin/doc-collab/.venv`
- Web preview: `http://10.0.0.31:3001` (optional)

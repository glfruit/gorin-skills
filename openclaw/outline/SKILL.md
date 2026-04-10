---
name: outline
description: "Manage Outline knowledge base — create/read/search/update/delete documents and collections. Use when the user asks to create wiki pages, search knowledge base, manage collections, organize team docs, share documents, or batch import content to Outline. Triggers: 'outline', '知识库', 'wiki', 'collection', '创建文档 outline', '搜索知识库'. Do NOT use for editing .docx files (use superdoc skill) or PDFs (use pdf skill)."
triggers:
  - "outline"
  - "知识库"
  - "wiki"
  - "创建文档 outline"
  - "搜索知识库"
  - "批量导入 outline"
user-invocable: true
agent-usable: true
readiness: production-ready
---

# Outline — Knowledge Base Management

Read, create, search, organize, and share documents in Outline.

## When to Use / When NOT to Use

**Use when:** creating/managing wiki pages, searching knowledge base, organizing collections, sharing docs, batch importing.

**Do NOT use when:** editing .docx → `superdoc` skill; PDFs → `pdf` skill; Obsidian vault → `pkm-*` skills.

## API Access

- **Base URL**: `http://10.0.0.31:3000/api/`
- **Auth**: `Authorization: Bearer <key>` header
- **Config**: `~/.openclaw/shared/outline-config.json`
- **All endpoints**: POST method, JSON body, RPC style (`POST /api/documents.create`)

## Core Operations

### Documents

```bash
# Create
curl -s -X POST "$URL/api/documents.create" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"title":"标题","text":"正文内容(markdown)","collectionId":"<id>","publish":true}'

# Get
curl -s -X POST "$URL/api/documents.info" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"id":"<doc-id>"}'

# Update
curl -s -X POST "$URL/api/documents.update" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"id":"<doc-id>","title":"新标题","text":"新内容"}'

# Search
curl -s -X POST "$URL/api/documents.search" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"query":"关键词"}'

# Delete (moves to trash)
curl -s -X POST "$URL/api/documents.delete" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"id":"<doc-id>"}'
```

### Collections

```bash
# List all
curl -s -X POST "$URL/api/collections.list" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{}'

# List docs in collection
curl -s -X POST "$URL/api/collections.documents" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"id":"<collection-id>"}'

# Create
curl -s -X POST "$URL/api/collections.create" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"name":"名称","permission":"read_write"}'
```

### Sharing

```bash
# Create share link
curl -s -X POST "$URL/api/shares.create" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"documentId":"<doc-id>","publish":true}'

# List shares
curl -s -X POST "$URL/api/shares.list" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{}'
```

## Agent Workflow (Helper Script)

Script: `scripts/outline-api.sh`

```bash
outline-api auth.info                # Verify connection
outline-api documents.list           # List all docs (paginated)
outline-api documents.search "关键词"  # Search
outline-api documents.create --collection <id> --title "标题" --text "内容"
outline-api documents.info <id>      # Get document
outline-api documents.update <id> --text "新内容"
outline-api collections.list         # List collections
outline-api collections.documents <id>  # Docs in collection
```

## Existing Collections

| Collection | ID | Squad |
|-----------|-----|-------|
| 📢 全员公告 | `39946ac0-148c-439e-8928-7ba83b27b64f` | all |
| 🎓 教学团队 | `b70fdcc2-e64e-4184-a274-0105781f6b09` | edu |
| 🔬 科研团队 | `e6da2435-5d39-41cf-8b59-9df7ef2cf80e` | research |
| 💼 投资团队 | `e1d96a4d-9404-4fff-af08-b8d8622880b2 | invest |
| 👨‍💻 开发团队 | `27d4a6c8-e8ac-4cfd-94d6-948efcdc4278` | dev |
| 🤖 AI 日常管理 | `25164f99-bb56-4ca4-a54d-b365e8da2301` | daily |
| 📚 共享知识 | `e88518e8-4335-4f7a-ba93-7e6b2400fd9b` | all |
| 🗄️ 归档 | `c8724279-221f-4a1b-9d4c-e2990f0f1d7d` | admin |

## Gotchas

1. **All endpoints are POST** — even reads/searches. No GET/PUT/DELETE.
2. **Document body is markdown** — `text` field accepts full markdown including headers, lists, code blocks.
3. **`publish: true`** required to make documents visible to team members.
4. **Pagination**: `limit` (default 25, max 100) + `offset` for list endpoints.
5. **Search** returns `id`, `title`, `text` snippets — use `documents.info` for full content.
6. **API key expires 2026-05-03** — check `~/.openclaw/shared/outline-config.json`.

## Error Handling

| Error | Fix |
|-------|-----|
| `authentication_required` | Check/renew API key |
| `collection_not_found` | Verify collection ID |
| `document_not_found` | Check doc ID or search for it |
| `permission_denied` | Check key scopes |

## Internal Acceptance
- API key verified, admin role confirmed
- 7 collections created successfully
- documents.create + documents.search + collections.list all tested

## Delivery Contract
All agents can access Outline API via config file. Helper script available for common operations.

## References

| File | Content |
|------|---------|
| `references/api-reference.md` | Full API method catalog (90+ endpoints) |
| `scripts/outline-api.sh` | CLI helper wrapper |
| `~/.openclaw/shared/outline-config.json` | API key & URL |

## Dependencies
- Outline running at `http://10.0.0.31:3000` (Docker)
- API key in `~/.openclaw/shared/outline-config.json`
- curl (available on all agents)

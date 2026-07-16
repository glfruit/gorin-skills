# Outline API Reference

Base URL: `http://10.0.0.31:3000/api/` — All POST, JSON body, Bearer auth.

## Documents (20+ methods)

| Method | Body | Description |
|--------|------|-------------|
| `documents.list` | `{} + limit/offset` | List all docs |
| `documents.info` | `{id}` | Get full document |
| `documents.create` | `{title, text?, collectionId?, publish?}` | Create doc |
| `documents.update` | `{id, title?, text?}` | Update doc |
| `documents.delete` | `{id}` | Move to trash |
| `documents.restore` | `{id}` | Restore from trash |
| `documents.archive` | `{id}` | Archive |
| `documents.unpublish` | `{id}` | Unpublish |
| `documents.move` | `{id, collectionId}` | Move to collection |
| `documents.duplicate` | `{id, title?, collectionId?}` | Duplicate |
| `documents.search` | `{query, limit?, offset?}` | Full-text search |
| `documents.search_titles` | `{query}` | Title-only search |
| `documents.templatize` | `{id}` | Convert to template |
| `documents.viewed` | `{limit?, offset?}` | Recently viewed |
| `documents.drafts` | `{limit?, offset?}` | Draft docs |
| `documents.archived` | `{limit?, offset?}` | Archived docs |
| `documents.deleted` | `{limit?, offset?}` | Trashed docs |
| `documents.import` | `{file, collectionId?}` | Import file |
| `documents.export` | `{id, format?}` | Export (md/html) |
| `documents.empty_trash` | `{}` | Empty trash |

## Collections (12+ methods)

| Method | Body | Description |
|--------|------|-------------|
| `collections.list` | `{limit?, offset?}` | List all |
| `collections.info` | `{id}` | Get details |
| `collections.create` | `{name, permission?, description?}` | Create |
| `collections.update` | `{id, name?, permission?}` | Update |
| `collections.delete` | `{id}` | Delete |
| `collections.documents` | `{id, limit?, offset?}` | Docs in collection |
| `collections.export` | `{id}` | Export all docs |
| `collections.export_all` | `{}` | Export workspace |
| `collections.add_user` | `{id, userId, permission?}` | Add user access |
| `collections.remove_user` | `{id, userId}` | Remove user |
| `collections.add_group` | `{id, groupId, permission?}` | Add group access |
| `collections.remove_group` | `{id, groupId}` | Remove group |

## Users & Groups (15+ methods)

| Method | Body | Description |
|--------|------|-------------|
| `users.list` | `{limit?, offset?}` | List users |
| `users.info` | `{id}` | Get user |
| `users.invite` | `{emails[], role?, message?}` | Invite users |
| `users.update_role` | `{id, role}` | Change role |
| `groups.list` | `{limit?, offset?}` | List groups |
| `groups.create` | `{name}` | Create group |
| `groups.add_user` | `{id, userId}` | Add to group |
| `groups.remove_user` | `{id, userId}` | Remove from group |

## Shares (5 methods)

| Method | Body | Description |
|--------|------|-------------|
| `shares.list` | `{}` | List shares |
| `shares.create` | `{documentId, publish?}` | Create share link |
| `shares.info` | `{id}` | Get share details |
| `shares.update` | `{id, publish?}` | Update share |
| `shares.revoke` | `{id}` | Revoke share |

## Revisions (2 methods)

| Method | Body | Description |
|--------|------|-------------|
| `revisions.list` | `{documentId, limit?, offset?}` | Version history |
| `revisions.info` | `{id, documentId}` | Get specific revision |

## Auth & Events

| Method | Body | Description |
|--------|------|-------------|
| `auth.info` | `{}` | Current user + team info |
| `auth.config` | `{}` | Auth configuration |
| `events.list` | `{limit?, audit?}` | Activity log |

## Response Format

All responses:
```json
{"ok": true, "status": 200, "data": { ... }, "policies": [...]}
```
Error:
```json
{"ok": false, "status": 401, "error": "authentication_required", "message": "..."}
```

## Permissions

| Value | Description |
|-------|-------------|
| `read` | View only |
| `read_write` | View + edit |
| `admin` | Full control |

## Document `text` Field

Accepts markdown: `# Heading`, `**bold**`, `- list`, `[link](url)`, `` `code` ``, `> blockquote`, etc.

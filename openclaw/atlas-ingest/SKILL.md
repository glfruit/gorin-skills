---
name: atlas-ingest
description: "Atlas vault 增量扫描：Dropbox raw/ 文件分类入库 + Clippings 编译。由独立 OpenClaw cron jobs 或手动运行触发。"
triggers: ["scan-dropbox", "scan-clippings", "atlas-ingest"]
user-invocable: false
command-dispatch: tool
agent-usable: true
requires:
  skills: [pkm-core]
---

# Atlas Ingest — 增量扫描 & 编译管线

扫描 Dropbox raw/ 和 Clippings 目录，增量检测新文件，智能分类后创建文献笔记、原子笔记、概念节点，并更新索引。

## 触发方式

- **cron**: 由独立 OpenClaw cron jobs 自动触发
- **手动**: Agent 调用 `ingest.py`

## 使用方式

```bash
# 扫描 Dropbox raw/ 目录
~/.gorin-skills/openclaw/atlas-ingest/.venv/bin/python ~/.gorin-skills/openclaw/atlas-ingest/scripts/ingest.py --source dropbox

# 扫描 Clippings 目录
~/.gorin-skills/openclaw/atlas-ingest/.venv/bin/python ~/.gorin-skills/openclaw/atlas-ingest/scripts/ingest.py --source clippings

# 扫描两者
~/.gorin-skills/openclaw/atlas-ingest/.venv/bin/python ~/.gorin-skills/openclaw/atlas-ingest/scripts/ingest.py --source all

# dry-run 模式（只检测不处理）
~/.gorin-skills/openclaw/atlas-ingest/.venv/bin/python ~/.gorin-skills/openclaw/atlas-ingest/scripts/ingest.py --source dropbox --dry-run

# 指定单个文件
~/.gorin-skills/openclaw/atlas-ingest/.venv/bin/python ~/.gorin-skills/openclaw/atlas-ingest/scripts/ingest.py --source dropbox --file /Users/gorin/Dropbox/OpenClaw/raw/paper.pdf
```

## 处理流程

### Dropbox raw/ 模式

```
1. 扫描 ~/Dropbox/OpenClaw/raw/
   ↓
2. SQLite 增量检测（比较 mtime）
   ↓
3. 锁文件处理：shutil.copy2 → /tmp/（指数退避 5 次）
   ↓
4. 文件分类（关键词匹配，不依赖 LLM）
   ├── PDF + abstract/method/results → paper
   ├── PDF + chapter/table of contents → book
   ├── .md + URL 来源 → article
   ├── 其他 → article（默认）
   ↓
5. 创建文献笔记 → atlas/1-Literature/{type}/
   ↓
6. 提取原子笔记 → atlas/3-Permanent/（LLM 驱动）
   ↓
7. 提取概念节点 → atlas/2-Concepts/（LLM 驱动）
   ↓
8. 更新索引 → atlas/4-Structure/Index/papers-index.md
   ↓
9. 更新 SQLite 状态
```

### Clippings 模式

```
1. 扫描 ~/pkm/atlas/9-Clippings/*.md
   ↓
2. 检测 frontmatter status: pending 或无 status
   ↓
3. 提取内容、分类、创建文献笔记
   ↓
4. 更新索引
   ↓
5. 标记剪藏 status: compiled
```

## 文件分类规则

| 特征 | 分类 | 判断依据 |
|------|------|----------|
| `.pdf` + abstract/method/results | paper | 学术论文特征词 |
| `.pdf` + chapter/table of contents | book | 书籍特征 |
| `.md` + 含 URL 来源 | article | 网页剪藏/博客 |
| 其他 | article | 默认兜底 |

## 文献笔记模板

文献笔记使用 ROADMAP.md 中定义的格式，frontmatter 包含：
- `title`, `type`, `date`, `tags`
- `source`（原始文件路径）
- `source_url`（如有）
- `authors`（如有）
- `file_type`（paper/book/article）
- `status`

## 索引格式

追加到 `4-Structure/Index/papers-index.md`，按领域分组：
```markdown
- [{title}](../1-Literature/{type}/{filename}.md) — 简要摘要
```

## SQLite 状态库

路径：`~/pkm/atlas/.state/dropbox.db`

已有表：
- `processed`: path(PK), filename, mtime, sha256, file_type, processed_at, target_note, status
- `scan_log`: id, scanned_at, files_found, files_new, files_updated, files_skipped, errors

## 配置

所有路径和配置硬编码在 ingest.py 顶部的 `CONFIG` dict 中，后续可迁移到 vault-config.yaml。

## 错误处理

- Dropbox 锁文件：指数退避重试 5 次（1s/2s/4s/8s/16s）
- PDF 解析失败：记录到 scan_log，跳过该文件
- SQLite 写入失败：回滚，不更新状态
- 索引文件不存在：自动创建

## When NOT to Use

- 不用于非 atlas vault 的文件处理。
- 不用于 LLM 交互式笔记创建（用 zk-router）。

## Changelog

### v1.0.0 (2026-04-04)
- 初始版本：Dropbox raw/ 扫描 + Clippings 编译
- 关键词分类（不依赖 LLM）
- 原子笔记和概念提取留 TODO

---
name: zk-literature
description: "[DEPRECATED] 文献笔记处理：URL → 文献笔记 → 原子 Zettels。已被 atlas-ingest 管线取代。"
triggers: []
user-invocable: false
command-dispatch: tool
agent-usable: false
status: deprecated
requires:
  skills: [pkm-core, obsidian-md, obsidian-defuddle]
  used-by: [zk-router]
---

# ZK Literature — 文献笔记处理 v2.0

> ⚠️ **DEPRECATED (2026-04-08)**
>
> 本 skill 的所有功能已被 `atlas-ingest` 管线取代。
>
> | 功能 | 旧方案（本 skill） | 新方案（atlas-ingest） |
> |------|-------------------|----------------------|
> | URL 文献入库 | web-reader + pkm CLI + zk-tool | URL → 9-Clippings → cron atlas-ingest |
> | 去重检查 | pkm dedup check | atlas-ingest 内置（DOI + SHA256） |
> | 原子笔记提取 | atomic_extract.py | atlas-ingest LLM extract_atoms_llm |
> | 关系发现 | pkm relation batch | atlas-ingest LLM 概念 + 双向链接 |
> | 分类 | 手动子目录 | atlas-ingest 5-area 加权分类 |
> | 目标 vault | octopus (Zettels/) | atlas (1-Literature/) |
>
> **不要再使用本 skill。** 新的文献入库流程：
> 1. 通过 zk-tool 或 atlas-ingest 创建 clipping 到 `~/pkm/atlas/9-Clippings/`
> 2. cron job `atlas-ingest-clippings` 自动拾取处理
> 3. atlas-ingest 生成文献笔记 + 概念 + 原子笔记 + 索引

## 原始文档（存档）

从 URL/文章/书籍提取内容，创建文献笔记 + 原子永久笔记。

**不处理**：user ideas → pkm-save-note；fleeting → idea-creator；moc → pkm-save-note。

**前置依赖**: 阅读 `pkm-core` 了解 vault 路径、frontmatter 规范、类型映射（`vault-config.yaml`）。

### 执行流程

1. 抓取内容（web-reader）
2. 去重检查（pkm dedup）
3. 关系发现（pkm relation batch）
4. 保存文献笔记（Zettels/2-Literature/）
5. 提取原子笔记（Zettels/3-Permanent/）
6. Frontmatter 合规检查
7. 孤儿预防

### Changelog

- **v2.0.0 (2026-03-27)**: 从 zk-para-zettel 重构
- **v2.0.1 (2026-04-08)**: 标记为 deprecated，功能由 atlas-ingest 取代

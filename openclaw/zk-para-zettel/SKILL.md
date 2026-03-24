---
name: zk-para-zettel
description: "Zettelkasten + PARA 笔记创建，5-type 关系分类，孤儿预防。用于 web capture、文献摘录、知识沉淀。可由 zk-router 统一调用。"
triggers: ["zettel", "zk", "知识笔记", "摘录"]
user-invocable: true
command-dispatch: tool
agent-usable: true
requires:
  skills: [pkm-core]
  used-by: [zk-router]
---

# ZK-PARA-Zettel — Zettelkasten 笔记 v1.1

创建原子化的永久笔记，自动关联 PARA 结构。

**注意**: 推荐使用统一入口 `zk-router`，单关键词 `zk` 触发，自动判断类型。

**前置依赖**: 阅读 `pkm-core` 了解 vault 路径、frontmatter 规范、命名规则。

## 快速触发

### 推荐方式（通过 zk-router）
- `zk <内容>` — 统一入口，智能判断
- `zk https://...` — Web摘录自动识别

### 直接触发（保留兼容）
- "保存为 zettel" / "创建知识笔记" / "摘录这段"
- Web capture：从 URL 抓取内容后自动创建 literature 笔记

## 执行流程

### 1. 判断笔记类型

| 来源 | 类型 | 目录 |
|------|------|------|
| 用户想法/观点 | `zettel` | `Zettels/3-Permanent` |
| 书籍/论文/文章 | `literature` | `Zettels/2-Literature` |
| MOC/索引页 | `moc` | `Zettels/4-Structure` |

### 2. 去重 + 分类 + 关系发现

```bash
PKM="${HOME}/.openclaw/pkm/pkm"
VAULT="${HOME}/Workspace/PKM/octopus"

# 去重
$PKM dedup check "$title" "$content"

# 分类
classification=$($PKM classify classify "$content" "$type" "$project" "$area")
location=$(echo "$classification" | jq -r '.location')

# 关系发现（5-type）
$PKM relation batch "$content" "$(grep -rl "$keyword" "$VAULT" --include="*.md" | head -20)"
```

### 3. 渲染并保存

```bash
# literature 笔记需要额外字段
vars=$(jq -n \
    --arg id "$(date +%Y%m%d%H%M)" \
    --arg title "$title" \
    --arg content "$content" \
    --arg summary "$summary" \
    --arg created "$(date +%Y-%m-%d)" \
    --arg source_url "$url" \
    --arg author "$author" \
    '{id: $id, title: $title, content: $content, summary: $summary, created: $created, source_url: $source_url, author: $author}')

note=$($PKM template render "$type" "$vars")
echo "$note" > "$VAULT/$location/$($PKM vault generate-filename "$title")"
```

### 4. 孤儿预防

新笔记必须有至少一个 outgoing link（`related` 或 `up`），否则提示补充关联。

## Zettel 写作规则

1. **原子性** — 每个笔记只讲一个观点
2. **自足性** — 不需要看其他笔记就能理解核心观点
3. **链接性** — 至少链接到 1 个现有笔记（通过 PKM Core 关系发现自动完成）
4. **frontmatter 合规** — 遵守 pkm-core 硬性规则

## 参考文档

- `pkm-core` — frontmatter 规范、vault 结构、命名规则
- `pkm-core/references/vault-structure.md` — 目录结构详解

## Changelog

### v1.1.0 (2026-03-20)
- 添加 pkm-core 依赖
- 添加孤儿预防步骤
- 简化重复规范说明

### v1.0.0
- 初始版本

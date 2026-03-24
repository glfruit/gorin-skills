---
name: idea-creator
description: "创建和管理想法笔记，自动发现关系。使用 '想法 xxx' 或 '/pkm_idea' 触发。"
triggers: ["想法", "idea", "闪念", "灵感", "/pkm_idea"]
user-invocable: true
command-dispatch: tool
agent-usable: true
requires:
  skills: [pkm-core]
---

# Idea Creator — 想法笔记 v1.1

快速捕获闪念和灵感，自动分类、发现关系、存入 vault。

**前置依赖**: 阅读 `pkm-core` 了解 vault 路径、frontmatter 规范。

## 触发方式

- Telegram: `想法 <内容>` 或 `/pkm_idea`
- 对话: "记一个想法" / "有个灵感" / "idea: xxx"

## 执行流程

### 1. 提取想法内容

从用户输入中提取：
- 核心想法（必需）
- 标题（可选，自动生成）
- 关键词（用于关系发现）

### 2. 创建笔记

使用 PKM Core：
```bash
PKM="${HOME}/.openclaw/pkm/pkm"
VAULT="${HOME}/Workspace/PKM/octopus"

# 智能分类 → Zettels/1-Fleeting
classification=$($PKM classify classify "$content" "idea" "" "")
location=$(echo "$classification" | jq -r '.location')

# 去重检查
dup=$($PKM dedup check "$title" "$content")

# 关系发现
relations=$($PKM relation batch "$content" "")

# 渲染模板
vars=$(jq -n \
    --arg id "$(date +%Y%m%d%H%M)" \
    --arg title "$title" \
    --arg content "$content" \
    --arg summary "$summary" \
    --arg created "$(date +%Y-%m-%d)" \
    '{id: $id, title: $title, content: $content, summary: $summary, created: $created}')

note=$($PKM template render "idea" "$vars")

# 保存
echo "$note" > "$VAULT/$location/$($PKM vault generate-filename "$title")"
```

### 3. Frontmatter 合规

遵守 `pkm-core` 的 frontmatter 硬性规则（无行内注释、key ASCII、日期标准格式）。

## 5-Type 关系分类

PKM Core 自动发现并分类关系：

| 类型 | 含义 | 示例 |
|------|------|------|
| `supports` | 支持/佐证 | 两个想法互相印证 |
| `contradicts` | 对立/矛盾 | 新想法反驳旧笔记 |
| `related` | 相关 | 同主题的不同角度 |
| `extends` | 扩展 | 在旧想法基础上深入 |
| `cluster` | 聚类 | 属于同一知识集群 |

## 输出格式

```
## 💡 想法已保存

**标题**: {title}
**位置**: {vault}/{location}/{filename}
**关系**: 发现 {n} 条关联笔记
  - supports: {notes}
  - contradicts: {notes}
  - related: {notes}
```

## 参考文档

- `pkm-core` — frontmatter 规范、vault 结构
- `references/api-reference.md` — PKM Core API 详解
- `references/user-guide.md` — 使用指南

## Changelog

### v1.1.0 (2026-03-20)
- 添加 pkm-core 依赖
- 简化重复的 frontmatter 说明
- 添加合规检查步骤

### v1.0.0 (2026-02-22)
- 初始版本

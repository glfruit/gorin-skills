---
name: idea-creator
description: "创建和管理想法笔记，自动发现关系。使用 '想法 xxx' 或 '/pkm_idea' 触发。依赖 pkm-core 进行智能分类和关系发现。Do NOT use for general notes or literature excerpts."
triggers: ["想法", "idea", "闪念", "灵感", "/pkm_idea"]
user-invocable: true
command-dispatch: tool
agent-usable: true
requires:
  skills: [pkm-core]
  used-by: [zk-router]
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

### v1.2.0 (2026-03-27)
- 确认单一职责：所有 idea/fleeting 归此 skill

### v1.1.0 (2026-03-20)
- 添加 pkm-core 依赖
- 简化重复的 frontmatter 说明
- 添加合规检查步骤

### v1.0.0 (2026-02-22)
- 初始版本

## When NOT to Use

- pkm-save-note 不再处理 idea 类型，所有 idea/fleeting 归此 skill。
- 不要用于一般笔记保存（用 zk-router 或 pkm-save-note）。
- 不要用于文献摘录或 web capture（用 zk-literature）。
- 不要在没有想法内容时触发。

## Error Handling

- 想法为空或过短（<10 字符）时，提示用户补充内容。
- pkm-core 不可用时，直接使用基础模板保存并告知用户关系发现被跳过。
- Obsidian vault 不可达时，保存到临时文件并提示路径。

## Internal Acceptance

- 想法笔记保存到正确的 Fleeting 或 Permanent 目录。
- frontmatter 包含所有必填字段（type, tags, created）。
- 至少发现 1 条关系并写入 links。

## Gotchas

- 中文关键词需要 jieba 分词，不要手动切词。
- 同名想法会去重合并，不会覆盖已有笔记。
- 关系发现依赖 pkm-core，需确保 vault 路径正确。

## Delivery Contract

- 保存后输出笔记路径和发现的关系列表。
- 回复包含 💡 emoji 作为视觉确认。
- 路径使用 `obsidian://` URI 格式方便跳转。
**注意：本技能是大型流水线的一部分。Do **not** report completion to the user unless all dependent tools/scripts/skills have been verified as integrated.**


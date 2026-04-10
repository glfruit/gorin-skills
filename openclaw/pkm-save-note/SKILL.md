---
name: pkm-save-note
description: "通用笔记保存接口（非文献、非想法）。支持 insight/decision/summary/meeting/plan/review/moc/fleeting。由 zk-router 路由调用。"
triggers: []
user-invocable: false
command-dispatch: tool
agent-usable: true
requires:
  skills: [pkm-core, obsidian-md]
  used-by: [zk-router]
---

# PKM Save Note — 通用笔记保存 v3.0

保存非文献、非想法类型的笔记。

**不处理**：literature → zk-literature；idea/fleeting → idea-creator。

**前置依赖**: 阅读 `pkm-core` 了解 vault 路径、frontmatter 规范、类型映射（`vault-config.yaml`）。

## 支持的笔记类型

| type | 来源 | 说明 |
|------|------|------|
| `insight` | 用户成熟观点 | 原子化永久笔记（非文献提取） |
| `decision` | 决策/选择 | 永久笔记 |
| `summary` | 内容总结 | 永久笔记 |
| `meeting` | 会议纪要 | 项目笔记 |
| `plan` | 计划/待办 | 项目笔记 |
| `review` | 周报/月回顾 | 回顾笔记 |
| `moc` | 索引/MOC | 结构笔记 |
| `fleeting` | 临时记录 | 闪念笔记 |

类型→目录映射见 `pkm-core/vault-config.yaml`。

## 执行流程

### 1. 收集信息

从用户消息中提取：content、title、type（可选，默认智能分类）、project、area、tags、source。

### 2. 智能分类（未指定 type 时）

根据内容特征判断类型：
- "决定/选择" → decision
- "总结/摘要" → summary
- "会议/讨论/和XX聊" → meeting
- "计划/待办/task" → plan
- "周总结/月回顾/复盘" → review
- 内容 < 50 字且无结构 → fleeting
- 成熟观点（有论据、有结构） → insight

### 3. 去重检查

```bash
PKM="${HOME}/.openclaw/pkm/pkm"
$PKM dedup check "$title" "$content"
```

### 4. 关系发现

```bash
VAULT="${HOME}/Workspace/PKM/octopus"
$PKM relation batch "$content" "$(grep -rl "$keyword" "$VAULT" --include="*.md" | head -20)"
```

### 5. 渲染模板并保存

```bash
vars=$(jq -n \
    --arg id "$(date +%Y%m%d%H%M)" \
    --arg title "$title" \
    --arg content "$content" \
    --arg summary "$summary" \
    --arg created "$(date +%Y-%m-%d)" \
    --arg type "$detected_type" \
    '{id: $id, title: $title, content: $content, summary: $summary, created: $created, type: $type}')

note=$($PKM template render "$detected_type" "$vars")
echo "$note" > "$VAULT/$location/$($PKM vault generate-filename "$title")"
```

### 6. 原子笔记提取（insight/summary 类型）

如果内容包含多个独立观点，拆分为原子笔记（与 zk-literature 的 Step 5 同理）。

### 7. Frontmatter 合规检查

引用 pkm-core 共享管道（`vault-config.yaml`）。

### 8. 孤儿预防

引用 pkm-core 共享管道。

## Promote 子流程（pkp 触发）

```
pkp           → 找最近一条 status != promoted 的 fleeting 笔记
pkp <keyword> → 搜索包含 keyword 的 fleeting 笔记，让用户选择
```

执行：
1. 读取 fleeting 笔记
2. 评估成熟度（长度 > 100 字、有结构化论述、有明确论点 → 可升级）
3. 转存为 permanent zettel（3-Permanent）
4. 原笔记标记 `status: promoted`，加 `up: "[[新笔记]]"` 链接
5. 新笔记 `up` 链回原笔记
6. 关系发现 + 合规检查 + 孤儿预防

## When NOT to Use

- 文献摘录（用 zk-literature）。
- 快速捕获灵感（用 idea-creator）。

## Error Handling

- 分类失败时使用默认类型 'fleeting' 并告知用户。
- 去重发现相似笔记时询问用户。
- promote 时找不到候选笔记时提示。

## Changelog

### v3.0.0 (2026-03-27)
- 移除 idea 和 literature 类型（分别归 idea-creator 和 zk-literature）
- 新增 insight 类型
- 新增 promote 子流程
- 引用 pkm-core 共享管道
- 不再 user-invocable，由 zk-router 路由

### v2.1.0 (2026-03-20)
- 添加 pkm-core 依赖
- 添加 frontmatter 合规检查

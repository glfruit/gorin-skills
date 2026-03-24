---
name: pkm-core
description: "PKM 基础层 — vault 路径、frontmatter 规范、命名规则、Obsidian 语法。所有笔记类 skills 的公共依赖。不要直接触发，由 pkm-save-note、idea-creator、zk-para-zettel 等引用。"
user-invocable: false
agent-usable: true
---

# PKM Core — 笔记系统基础层

本 skill 提供所有笔记类 skills 共享的基础规范。**不要单独触发**，由其他笔记 skills 引用。

## Vault 路径

从 Obsidian 配置读取活跃 vault：
```bash
cat ~/Library/Application\ Support/obsidian/obsidian.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
for v in d.get('vaults',{}).values():
    if v.get('open'): print(v['path'])
"
```

当前 vault：
- **octopus**: `/Users/gorin/Workspace/PKM/octopus`（主 vault）
- **gourmet**: `/Users/gorin/Workspace/PKM/gourmet`

### Vault 目录结构（octopus）

```
octopus/
├── Home/                    ← 仪表盘、索引页
├── Calendar/
│   ├── Journal/Daily/       ← 日记（YYYY/MM/DD.md）
│   ├── Journal/             ← 其他日记
│   ├── Reviews/             ← 周/月/年回顾
│   └── Logs/                ← 日志
├── Zettels/
│   ├── 1-Fleeting/          ← 闪念笔记（临时）
│   ├── 2-Literature/        ← 文献笔记（书籍/文章）
│   │   ├── Books/
│   │   ├── Papers/
│   │   └── Articles/
│   ├── 3-Permanent/         ← 永久笔记（原子化）
│   └── 4-Structure/         ← 结构笔记（MOC、周报）
├── Efforts/
│   ├── 1-Projects/
│   │   ├── Active/
│   │   └── Done/
│   ├── 2-Areas/
│   └── 3-Works/
├── Archives/                ← 归档
│   └── Temp-Files/0.Inbox/
└── .obsidian/               ← Obsidian 配置（不要手动改）
```

## 笔记命名规则

| 类型 | 格式 | 示例 |
|------|------|------|
| 闪念 | `{type}-{简短描述}.md` | `idea-first-brain.md` |
| 文献 | `{title}.md` | `Thinking Fast and Slow.md` |
| Zettel | `{YYYYMMDDHHMM}-{标题}.md` | `202603201430-zettelkasten-method.md` |
| 日记 | `YYYY-MM-DD.md` | `2026-03-20.md` |
| 会议 | `{YYYYMMDDHHMM}-meeting-{主题}.md` | `202603201400-meeting-sprint-review.md` |
| 周报 | `YYYYMMDD-PARA-Weekly-Review-W{N}.md` | `20260308-PARA-Weekly-Review-W10.md` |
| MOC | `{Topic}-MOC.md` 或 `MoC-{Title}.md` | `AI-MOC.md` |

规则：
- ID 格式：`YYYYMMDDHHMM`（10 位数字）
- 标题分隔符：`-`
- 标题最大长度：50 字符
- 标题不包含特殊字符（`/`、`\`、`:`、`*`、`?`、`"`、`<`、`>`、`|`）

## Frontmatter 规范（所有笔记必须遵守）

### 基本格式

```yaml
---
title: "笔记标题"
type: zettel
date: 2026-03-20
tags: [tag1, tag2]
---
```

### Obsidian 认可的属性类型

| 类型 | 示例 | 说明 |
|------|------|------|
| Text | `title: My Title` | 纯文本，建议加引号 |
| Number | `rating: 4.5` | 数字 |
| Checkbox | `completed: true` | 布尔值 |
| Date | `date: 2026-03-20` | YYYY-MM-DD |
| Date & Time | `due: 2026-03-20T14:30:00` | ISO 8601 |
| List (inline) | `tags: [one, two]` | 推荐，最简洁 |
| List (multiline) | `tags:\n  - one\n  - two` | 也支持 |
| Link | `up: "[[Note]]"` | 必须加引号 |
| Links (list) | `related:\n  - "[[A]]"\n  - "[[B]]"` | 必须加引号 |

### ⚠️ 硬性规则

1. **列表项后不能加行内注释**
   ```yaml
   # ❌ 错误
   related:
     - "[[Note A]]" — 描述文字

   # ✅ 正确
   related:
     - "[[Note A]]"
   ```

2. **Front matter wikilinks 必须加引号**
   ```yaml
   # ❌ 错误
   up: [[Note]]

   # ✅ 正确
   up: "[[Note]]"
   ```

3. **Key 必须是 ASCII 字符**
   ```yaml
   # ❌ 可能出错
   心情: 😊

   # ✅ 正确
   mood: 😊
   ```

4. **日期格式必须标准**
   ```yaml
   # ❌ 错误
   date: 2024/01/15

   # ✅ 正确
   date: 2024-01-15
   ```

5. **不要在 front matter 中混用 tags 格式**
   ```yaml
   # ❌ 同时用 inline 和 multiline
   tags: [one]
     - two

   # ✅ 选一种
   tags: [one, two]
   ```

### 常用自定义属性

| 属性 | 用途 | 值类型 |
|------|------|--------|
| `type` | 笔记类型 | text（zettel/idea/literature/meeting/plan/review/moc/daily） |
| `status` | 状态 | text（fleeting/active/done/archived） |
| `project` | 所属项目 | link |
| `area` | 所属领域 | link |
| `book` / `author` | 书籍关联 | text |
| `source` | 来源 | text 或 link |
| `source_url` | 来源 URL | text |
| `up` | 上级笔记 | link |
| `related` | 关联笔记 | link list |
| `mood` / `energy` | 日记元数据 | text |
| `rating` | 评分 | number |
| `created` / `modified` | 时间戳 | date |
| `aliases` | 别名（用于搜索建议） | list |

## Obsidian 特有语法速查

详见 `references/obsidian-syntax.md`，关键项：

| 语法 | 写法 | 用途 |
|------|------|------|
| Wikilink | `[[Note]]` / `[[Note\|显示]]` / `[[Note#标题]]` | 内部链接 |
| Embed | `![[Note]]` / `![[img.png\|300]]` | 嵌入内容 |
| Callout | `> [!type]` / `> [!type]- 折叠` | 提示块 |
| Highlight | `==text==` | 高亮 |
| Comment | `%%hidden%%` | 隐藏注释 |
| Tag | `#tag` / `#nested/tag` | 行内标签 |

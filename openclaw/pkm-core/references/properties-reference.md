# Obsidian Properties (Frontmatter) 参考

来源：[Obsidian Help](https://help.obsidian.md/properties) + [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills)

## 基本格式

```yaml
---
title: My Note Title
date: 2024-01-15
tags:
  - project
  - important
aliases:
  - My Note
  - Alternative Name
cssclasses:
  - custom-class
status: in-progress
---
```

## 属性类型

| 类型 | 示例 | 说明 |
|------|------|------|
| Text | `title: My Title` | 纯文本 |
| Number | `rating: 4.5` | 数字 |
| Checkbox | `completed: true` | 布尔值 |
| Date | `date: 2024-01-15` | 日期 |
| Date & Time | `due: 2024-01-15T14:30:00` | ISO 8601 |
| List (inline) | `tags: [one, two]` | 内联数组 |
| List (multiline) | 见下方 | YAML 列表 |
| Link | `related: "[[Other Note]]"` | 单个 wikilink |
| Links (list) | 见下方 | wikilink 列表 |

## 内置属性

- `tags` — 搜索标签，在 graph view 中可见
- `aliases` — 笔记别名，用于链接建议
- `cssclasses` — 应用于笔记的 CSS 类

## Tags 写法

```yaml
# 内联数组（推荐）
tags: [project, active]

# 多行列表
tags:
  - project
  - active
```

规则：字母（任何语言）、数字（不能开头）、下划线 `_`、连字符 `-`、斜杠 `/`。

## Wikilink 作为属性值

```yaml
# 单个链接
up: "[[Index Note]]"

# 链接列表
related:
  - "[[Note A]]"
  - "[[Note B]]"

# ⚠️ 注意：链接值必须用引号包裹
# ❌ 错误
up: [[Index Note]]

# ✅ 正确
up: "[[Index Note]]"
```

## ⚠️ Obsidian YAML 常见错误

### 1. 列表项后加行内注释

```yaml
# ❌ 错误 — Obsidian 无法正确解析
related:
  - "[[Note A]]" — 描述文字
  - "[[Note B]]" — 另一个描述

# ✅ 正确
related:
  - "[[Note A]]"
  - "[[Note B]]"
```

### 2. Key 包含非 ASCII 字符

```yaml
# ❌ 可能出错
心情: 😊
# ✅ 安全
mood: 😊
```

### 3. 未闭合的引号

```yaml
# ❌ 错误
title: My "unquoted title

# ✅ 正确
title: "My \"unquoted\" title"
```

### 4. 日期格式不标准

```yaml
# ❌ 非标准
date: 2024/01/15

# ✅ 标准
date: 2024-01-15
```

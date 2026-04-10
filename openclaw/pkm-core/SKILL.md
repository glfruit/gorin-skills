---
name: pkm-core
description: "PKM 基础层 — vault 路径、frontmatter 规范、命名规则、Obsidian 语法。所有笔记类 skills 的公共依赖。不要直接触发，由 pkm-save-note、idea-creator、zk-para-zettel 等引用。 Do NOT use directly — invoked by other PKM skills only."
user-invocable: false
agent-usable: true
---


# PKM Core — 笔记系统基础层

本 skill 提供所有笔记类 skills 共享的基础规范。**不要单独触发**，由其他笔记 skills 引用。

## Vault 路径

所有 vault 配置（唯一权威来源）在 `vault-config.yaml` 的 `vaults` 字段。

```bash
# 获取指定 vault 路径
python3 -c "
import yaml
with open(os.path.expanduser('~/.gorin-skills/openclaw/pkm-core/vault-config.yaml')) as f:
    cfg = yaml.safe_load(f)
print(os.path.expanduser(cfg['vaults']['atlas']['path']))
"
```

### Vault 列表

| Vault | 路径 | 角色 | LLM 角色 |
|-------|------|------|----------|
| **atlas** | `~/pkm/atlas` | 知识图谱、研究资料 | 主导（写入+维护+链接） |
| **octopus** | `~/Workspace/PKM/octopus` | 日常管理、项目管理 | 辅助（人为主，LLM 辅助） |
| **loom** | `~/pkm/loom` | 内容创作工坊 | 辅助（人为主，LLM 辅助） |

### Atlas 目录结构

```
atlas/
├── 1-Literature/           ← 文献笔记
│   ├── Papers/             ← 学术论文
│   ├── Books/              ← 书籍
│   ├── Articles/           ← 博客/网页
│   ├── Repos/              ← 代码仓库
│   ├── Podcasts/           ← 播客/视频
│   └── Tweets/             ← X/Twitter thread
├── 2-Concepts/             ← 概念节点（跨文献关联）
├── 3-Permanent/            ← 原子笔记
├── 4-Structure/            ← 结构笔记
│   ├── MOC/                ← Map of Content
│   ├── Index/              ← LLM 维护的索引
│   └── Queries/            ← 查询产物回填
├── 5-Areas/                ← 知识领域
├── 6-Outputs/              ← 多格式产物
│   ├── PDF/ Slides/ Charts/ Reports/
├── 7-Templates/            ← 笔记模板
├── 8-Assets/               ← 图片/附件
├── 9-Clippings/            ← Web Clipper 剪藏
└── .state/                 ← 处理状态
```

### Octopus 目录结构

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

## 类型映射（唯一权威来源）

详见 `vault-config.yaml` 的 `vaults.<name>.type_mapping` 字段。各笔记 skill 不再各自维护 type → directory 映射，统一引用此文件。

**注意**：不同 vault 的类型映射不同。atlas 用 `1-Literature`，octopus 用 `Zettels/2-Literature`。

## 共享管道

详见 `vault-config.yaml` 的 `pipeline` 部分。所有创建类 skill（pkm-save-note、zk-literature、idea-creator）必须使用共享管道的 validate_frontmatter 和 prevent_orphan。

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

## When NOT to Use

- 不直接由用户触发，由其他笔记类技能引用。
- 不用于执行笔记操作（保存/搜索/分类由上层技能处理）。

## Error Handling

- vault 路径变量未设置时，使用默认路径并发出警告。
- frontmatter 解析失败时，报告具体行号和字段。
- 命名冲突时，在文件名后追加序号。

## Internal Acceptance

- 所有引用此技能的上层技能能正确读取配置。
- vault 路径、命名规则、frontmatter 规范与实际文件一致。
- validate-skill.sh 通过。

## Gotchas

- Obsidian vault 路径可能因环境不同而变化，始终使用环境变量。
- frontmatter 的 `tags` 必须是列表格式，不能用逗号分隔字符串。
- 笔记命名规则：`YYYY-MM-DD-title-kebab`，日期是必填前缀。

## Delivery Contract

- 配置变更需同步更新所有引用此技能的 SKILL.md。
- vault 路径变更需在 TOOLS.md 中同步更新。
**注意：本技能是大型流水线的一部分。Do **not** report completion to the user unless all dependent tools/scripts/skills have been verified as integrated.**not** report completion to the user unless all dependent tools/scripts/skills integration tests have passed.**

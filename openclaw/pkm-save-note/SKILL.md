---
name: pkm-save-note
description: "通用笔记保存接口。基于 PKM Core 智能分类、去重、5-type 关系发现、模板渲染，自动存入正确目录。"
triggers: ["保存笔记", "save note", "pkm save"]
user-invocable: true
command-dispatch: tool
agent-usable: true
requires:
  skills: [pkm-core]
---

# PKM Save Note — 通用笔记保存接口 v2.1

基于 PKM Core 的标准化笔记保存。Agent 调用此 skill 创建笔记。

**前置依赖**: 阅读 `pkm-core` skill 了解 vault 路径、frontmatter 规范、命名规则。

## 支持的笔记类型

| type | 存放目录 | 模板 | 说明 |
|------|---------|------|------|
| `log` / `thought` | `Zettels/1-Fleeting` | fleeting | 闪念、临时笔记 |
| `idea` | `Zettels/1-Fleeting` | idea | 有结构化的灵感 |
| `literature` | `Zettels/2-Literature` | literature | 书籍/文章/论文笔记 |
| `summary` / `decision` | `Zettels/3-Permanent` | zettel | 永久笔记 |
| `meeting` | `Efforts/1-Projects` | meeting | 会议记录 |
| `plan` | `Efforts/1-Projects` | plan | 计划文档 |
| `review` | `Efforts/2-Areas` | — | 周/月回顾 |
| `moc` | `Zettels/4-Structure` | moc | MOC 总览页 |

## Agent 执行流程

### Step 1: 收集信息

从用户消息中提取：
- `content` — 笔记正文（必需）
- `title` — 笔记标题（必需）
- `type` — 笔记类型（可选，默认由 PKM Core 智能分类）
- `project` — 所属项目（可选）
- `area` — 所属领域（可选）
- `tags` — 额外标签（可选）
- `source` / `source_url` — 来源（可选，文献笔记用）

### Step 2: 去重检查

```bash
PKM="${HOME}/.openclaw/pkm/pkm"
$PKM dedup check "$title" "$content"
```

如果检测到重复，询问用户是否合并或跳过。

### Step 3: 分类与定位

```bash
$PKM classify classify "$content" "$type" "$project" "$area"
```

返回 `location`（目录路径）和 `detected_type`。

### Step 4: 关系发现

```bash
# 搜索 vault 中的相关笔记
search_results=$(grep -rl "相关关键词" "$VAULT_PATH" --include="*.md" | head -20)

# 5-type 关系分类
$PKM relation batch "$content" "$search_results"
```

关系类型：`supports`（支持）、`contradicts`（对立）、`related`（相关）、`extends`（扩展）、`cluster`（聚类）

### Step 5: 渲染模板并保存

```bash
# 生成变量
vars=$(jq -n \
    --arg id "$(date +%Y%m%d%H%M)" \
    --arg title "$title" \
    --arg content "$content" \
    --arg summary "$summary" \
    --arg created "$(date +%Y-%m-%d)" \
    --arg type "$detected_type" \
    '{id: $id, title: $title, content: $content, summary: $summary, created: $created, type: $type}')

# 渲染模板（优先读 ~/.openclaw/pkm/templates/ 下的独立文件）
note=$($PKM template render "$detected_type" "$vars")

# 保存
echo "$note" > "$location/$($PKM vault generate-filename "$title")"
```

### Step 6: Frontmatter 合规检查

保存前验证（参考 `pkm-core` 的硬性规则）：
- [ ] 列表项后无行内注释
- [ ] wikilinks 属性值加引号
- [ ] key 是 ASCII 字符
- [ ] 日期格式 YYYY-MM-DD
- [ ] tags 格式统一

## PKM Core 命令速查

```bash
PKM="${HOME}/.openclaw/pkm/pkm"

$PKM classify classify "content" "type" "project" "area"  # 智能分类
$PKM dedup check "title" "content"                         # 去重检测
$PKM relation batch "content" "search_results"              # 关系分类
$PKM template render "zettel" '{"title":"test"}'            # 模板渲染
$PKM vault generate-id                                       # 生成 ID
$PKM vault generate-filename "title"                         # 生成文件名
$PKM vault ensure-dir "path"                                 # 确保目录存在
```

## Changelog

### v2.1.0 (2026-03-20)
- 添加 pkm-core 依赖声明
- 添加 frontmatter 合规检查步骤
- 添加 vault 路径和类型→目录映射表
- SKILL.md 从接口文档改为可执行指令

### v2.0.0 (2026-03-04)
- 重构为 PKM Core 接口
- 统一 5-type 关系分类

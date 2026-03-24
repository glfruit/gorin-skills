---
name: visual-knowledge-explainer
description: 把教材、培训资料、读书笔记、文章知识、流程说明、技术内容，转成结构清晰、视觉化、适合讲解、复习、培训、分享的 HTML explainer 页面或 slide-style 页面。Use when user asks for "visual explainer", "知识讲解页", "培训资料页", "教学 explainer", or "讲义页". NOT for: 单纯摘要、普通 markdown 排版、插画/封面/海报生成、社媒图片卡片、PPTX/DOCX/PDF 操作.
---

# Visual Knowledge Explainer - 教学/培训/知识讲解的视觉化页面生成

## 核心目标

不是"make pretty HTML"

而是：

> **"make content easier to teach, understand, review, and share."**

## 适用场景矩阵

| 场景 | 典型输入 | 典型输出 | 优先级 |
|------|----------|----------|--------|
| 教材编写 | 章节草稿、课程提纲 | 讲义页、教学 explainer、slides | 高 |
| 团队培训 | SOP、培训提纲、流程文档 | 培训页、流程页、slide-style 页面 | 高 |
| 知识讲解 | 文章摘要、读书笔记、知识卡 | explainer page、概念图、复习页 | 高 |
| 流程说明 | 工作流、步骤 | 流程图 + 卡片讲解页 | 中 |
| 技术说明 | 架构/模块描述 | 架构页、模块讲解页 | 中 |
| 对比分析 | 差异、特性矩阵 | HTML table 页面 | 中 |
| 工程评审 | diff、plan、repo 状态 | review page、recap page | 兼容 |

## 什么时候使用

✅ **使用这个技能当：**
- 你需要把教材内容转成"更容易教"的页面
- 你需要把培训资料转成"更容易讲"的页面
- 你需要把读书笔记转成"更容易复习"的页面
- 你需要把知识笔记转成"更容易分享"的页面
- 你需要把流程说明转成"更容易理解"的页面
- 你需要生成教学 explainer 页面

## When NOT to Use / 不使用的场景

❌ **不要使用这个技能当：**
- 单纯摘要 → 使用 `summarize` skill
- 普通 markdown 排版 → 直接编辑 markdown
- 插画/封面/海报/艺术图生成 → 使用 `baoyu-cover-image` 或 `baoyu-image-gen`
- 社媒图片卡片 → 使用 `baoyu-xhs-images` 或 `baoyu-infographic`
- PPTX/DOCX/PDF 操作 → 使用 `pptx`、`docx`、`pdf` skill
- 只需要图片、不需要结构化解释 → 使用 `baoyu-image-gen`

## 快速开始

```bash
# 基本用法
visual-knowledge-explainer <content.md>

# 指定主题
visual-knowledge-explainer <content.md> --theme default
visual-knowledge-explainer <content.md> --theme grace
visual-knowledge-explainer <content.md> --theme simple
visual-knowledge-explainer <content.md> --theme modern

# 指定类型（可选，自动识别优先）
visual-knowledge-explainer <content.md> --type 教材
visual-knowledge-explainer <content.md> --type 培训
visual-knowledge-explainer <content.md> --type 知识讲解

# 生成截图（可选）
visual-knowledge-explainer <content.md> --screenshot

# 指定输出目录（可选）
visual-knowledge-explainer <content.md> --output-dir ~/Downloads
```

## 工作流程

### Step 1: 输入类型识别

系统会自动识别内容类型：

| 识别信号 | 内容类型 |
|---------|---------|
| "教程"、"教学"、"课堂"、"课程" | 教材 |
| "SOP"、"流程"、"步骤"、"培训" | 培训 |
| "笔记"、"读书"、"概念"、"知识点" | 知识讲解 |
| "流程图"、"workflow" | 流程/SOP |
| "对比"、"vs"、"差异" | 对比分析 |
| "架构"、"模块"、"系统" | 技术说明 |
| "如何"、"使用"、"指南" | 教程 |

### Step 2: 模板选择

根据内容类型选择合适模板：

| 内容类型 | 推荐模板 | 适用场景 |
|---------|---------|---------|
| 教材 | `chapter-explainer.html` | 多模块教学，带学习目标 |
| 培训 | `training-page.html` | SOP、培训、步骤说明 |
| 知识讲解 | `explainer-page.html` | 笔记、文章、概念 |
| 流程 | `workflow-page.html` | 步骤流程，带 Mermaid |
| 对比 | `comparison-table.html` | A vs B、特性对比 |
| 快速演示 | `slide-deck.html` | 幻灯片风格 |

### Step 3: 主题选择

根据内容类型和受众选择主题：

| 内容类型 | 推荐主题 | 视觉特点 |
|---------|---------|---------|
| 教材 | `grace` or `default` | 教育友好 |
| 培训 | `default` or `simple` | 清晰步骤 |
| 知识讲解 | `grace` or `modern` | 阅读友好 |
| 流程 | `simple` or `modern` | 清晰流程 |
| 技术说明 | `modern` or `default` | 专业技术感 |
| 对比分析 | `default` or `grace` | 清晰对比 |

**主题说明**：
- `default` - 经典布局，标题居中
- `grace` - 优雅卡片，阴影圆角
- `simple` - 极简现代，留白充足
- `modern` - 大圆角，宽松行距

### Step 4: 渲染引擎

**Hybrid 策略**：
- 简单列表 → HTML `<ul>`
- 复杂数据 → HTML `<table>`
- 关系/流程 → Mermaid
- 视觉分隔 → CSS Grid

**Mermaid 规则**：
- 仅在需要可视化时使用
- 1-2 个 diagram per page max
- 保持简单，清晰优先

### Step 5: 输出

- HTML 单文件（内联 CSS）
- 可选：Markdown 预览
- 可选：截图（当前通过 Playwright CLI）

## 当前实现状态

已实现：
- markdown -> HTML 单文件生成
- 自动内容类型识别
- 模板选择
- 第一版主题切换
- 可选截图生成

仍在继续补：
- 更成熟的主题系统
- 更强的 workflow / comparison 结构化提取
- 更稳的截图 fallback

## Readiness

- 当前等级：`integrated`
- 证据：
  - markdown -> HTML 已实跑
  - `--screenshot` 已实跑
  - 已通过读书工作流集成调用
  - 实际产物已落到 Obsidian 书目录

更详细的实现说明见：
- `references/implementation-notes.md`

## 关键原则

### 教学导向

**不是装饰，而是教学工具**：
- 每个页面应该帮助 teaching
- 每个设计应该服务于 understanding
- 每个视觉元素应该增加 clarity

### 结构化内容

**标准结构**：
```
Hero Section (title, context, objectives)
    ↓
Learning Objectives / Prerequisites
    ↓
Modules (3-7 modules, each with: concept, example, mistakes)
    ↓
Summary / Review
    ↓
Reference Section (further reading)
```

### 视觉纪律

**必须遵守**：
- 无通用 AI 风格页面
- 无纯文本 dump
- 无装饰性装饰（decoration without purpose）
- 无过度复杂布局
- 无过多 Mermaid（1-2 个 per page max）

### Anti-Slop 规则

1. **没有结构** → 不合格
2. **没有例子** → 不合格
3. **没有学习目标**（教材）→ 不合格
4. **没有 FAQ**（培训）→ 不合格
5. **只有装饰** → 不合格

## 输出示例

### Key Elements

**Hero Section**:
- Title
- Subtitle (context)
- Metadata (topic, level, time)
- Learning objectives (教材)
- Prerequisites (培训)

**Body Sections**:
- Modules (3-7)
- Each module: concept, example, common mistakes, application

**Reference Section**:
- Further reading
- Related concepts
- Quick reference (optional)

## 文件命名

```
{content-title}-{timestamp}.html

Examples:
- git-intro-20260315-082900.html
- training-onboarding-20260315-082900.html
- note-concept-20260315-082900.html
```

## 错误处理

**常见问题**：

1. **内容类型无法识别**
   - Solution: user 明确指定 `--type <type>`

2. **模板不匹配**
   - Solution: use fallback `explainer-page.html`

3. **主题未找到**
   - Solution: use default theme `default`

## 高级用法

### Shell Interaction

**Example**:
```
user: visual-knowledge-explainer ~/notes/git-intro.md --theme grace --screenshot
agent: [分析内容类型...] → 检测到：教材 → 选择模板：chapter-explainer.html → 应用主题：grace → 生成页面... → 生成截图...
agent: ✅ 已生成 HTML 页面 + 截图：~/Downloads/visual-explainer/git-intro-20260315-082900.html + png
```

## 与原 visual-explainer 的区别

| 特性 | visual-explainer (original) | visual-knowledge-explainer (new) |
|------|----------------------------|----------------------------------|
| 主要用途 | 工程 review | 教学/培训/知识讲解 |
| 内容识别 | 手动指定 | 自动识别 + 手动覆盖 |
| 主题系统 | 4 dimensions (texture/mood/typography/density) | 4 themes (default/grace/simple/modern) |
| 模板系统 | 通用 | 6 个专用模板 |
| 输出Focus | HTML | HTML + Screenshot + Preview |
| 环境假设 | Claude Code plugin | OpenClaw native |

## 目录结构

```
visual-knowledge-explainer/
├── SKILL.md              # This file
├── references/
│   ├── aesthetic-rules.md       # Theme guidelines
│   ├── rendering-strategy.md    # Template selection
│   ├── page-patterns.md         # Template specs
│   ├── mermaid-guidelines.md    # Mermaid usage
│   ├── anti-slop-rules.md       # Quality constraints
│   └── output-conventions.md    # File naming, delivery
└── templates/
    ├── explainer-page.html
    ├── training-page.html
    ├── chapter-explainer.html
    ├── workflow-page.html
    ├── comparison-table.html
    └── slide-deck.html
```

## 下一步

1. 输入内容（markdown 或文本）
2. 自动识别类型（教材/培训/知识讲解/流程/对比/技术）
3. 选择模板和主题
4. 生成 HTML 页面
5. （可选）生成截图
6. 返回文件路径

---

**Remember**: This skill is about **teaching**, not decoration.

```

---
name: visual-knowledge-explainer
description: 把教材、培训资料、读书笔记、文章知识、流程说明、技术内容，转成结构清晰、视觉化、适合讲解、复习、培训、分享的 HTML explainer 页面或 slide-style 页面。Use when user asks for "visual explainer", "知识讲解页", "培训资料页", "教学 explainer", or "讲义页". NOT for: 单纯摘要、普通 markdown 排版、插画/封面/海报生成、社媒图片卡片、PPTX/DOCX/PDF 操作.
---

# Visual Knowledge Explainer

> 不是 "make pretty HTML"，而是 **"make content easier to teach, understand, review, and share."**

## 适用场景

| 场景 | 典型输入 | 典型输出 |
|------|----------|----------|
| 教材编写 | 章节草稿、课程提纲 | 讲义页、教学 explainer |
| 团队培训 | SOP、培训提纲、流程文档 | 培训页、流程页 |
| 知识讲解 | 文章摘要、读书笔记 | explainer page、复习页 |
| 流程说明 | 工作流、步骤 | 流程图 + 卡片讲解页 |
| 技术说明 | 架构/模块描述 | 架构页、模块讲解页 |
| 对比分析 | 差异、特性矩阵 | HTML table 页面 |

## When NOT to Use

❌ 单纯摘要 → `summarize` | ❌ 普通 markdown → 直接编辑 | ❌ 插画/海报 → `baoyu-cover-image` | ❌ 社媒卡片 → `baoyu-xhs-images` | ❌ PPTX/DOCX/PDF → respective skills

## Quick Start

```bash
visual-knowledge-explainer <content.md>
visual-knowledge-explainer <content.md> --theme grace
visual-knowledge-explainer <content.md> --type 教材
visual-knowledge-explainer <content.md> --screenshot
visual-knowledge-explainer <content.md> --output-dir ~/Downloads
```

## Workflow

### Step 1: Input Type Recognition

Auto-detect from content signals. 详见 `references/rendering-strategy.md`

### Step 2: Template Selection

| 内容类型 | 推荐模板 |
|---------|---------|
| 教材 | `chapter-explainer.html` |
| 培训 | `training-page.html` |
| 知识讲解 | `explainer-page.html` |
| 流程 | `workflow-page.html` |
| 对比 | `comparison-table.html` |
| 快速演示 | `slide-deck.html` |

### Step 3: Theme Selection

- `default` — 经典布局，标题居中
- `grace` — 优雅卡片，阴影圆角
- `simple` — 极简现代，留白充足
- `modern` — 大圆角，宽松行距

### Step 4: Render

Hybrid: simple lists → HTML `<ul>`, complex data → `<table>`, relationships → Mermaid (1-2 per page max), visual separation → CSS Grid.

### Step 5: Output

HTML single file (inline CSS). Optional: markdown preview, screenshot (Playwright).

## 关键原则

### 教学导向

每个页面帮助 teaching，每个设计服务 understanding，每个视觉元素增加 clarity。

### 标准结构

```
Hero Section (title, context, objectives)
    ↓
Learning Objectives / Prerequisites
    ↓
Modules (3-7, each: concept, example, mistakes)
    ↓
Summary / Review
    ↓
Reference Section
```

### Anti-Slop 规则

1. 没有结构 → 不合格
2. 没有例子 → 不合格
3. 没有学习目标（教材）→ 不合格
4. 没有 FAQ（培训）→ 不合格
5. 只有装饰 → 不合格

详见 `references/anti-slop-rules.md`

## 错误处理

| Issue | Solution |
|-------|----------|
| 内容类型无法识别 | 用户指定 `--type <type>` |
| 模板不匹配 | Fallback `explainer-page.html` |
| 主题未找到 | Fallback `default` |

## References

| File | Content |
|------|---------|
| `references/rendering-strategy.md` | Template selection, content type detection |
| `references/page-patterns.md` | Template specifications |
| `references/aesthetic-rules.md` | Theme guidelines |
| `references/mermaid-guidelines.md` | Mermaid usage rules |
| `references/anti-slop-rules.md` | Quality constraints |
| `references/output-conventions.md` | File naming, delivery |

## Readiness

`integrated` — 已实跑 markdown→HTML、截图、读书工作流集成。

## 目录结构

```
visual-knowledge-explainer/
├── SKILL.md
├── references/  (aesthetic-rules, rendering-strategy, page-patterns, ...)
└── templates/   (explainer-page.html, training-page.html, chapter-explainer.html, ...)
```

---

**Remember**: This skill is about **teaching**, not decoration.

## Error Handling

- 输入内容过长时，分段处理并提示用户。
- HTML 渲染失败时，检查模板和 CSS 是否完整。
- 浏览器预览失败时，输出文件路径让用户手动打开。

## Internal Acceptance

- 生成的 HTML 页面在浏览器中正确渲染。
- 内容结构清晰，层级关系正确。
- 样式美观且无布局错乱。

## Gotchas

- 某些中文特殊字符在 HTML 标题中可能显示异常，需要 HTML entity 转义。
- 复杂的数学公式可能需要 MathJax/KaTeX 支持。
- 图片链接必须是公开可访问的 URL，本地路径无法在 HTML 中使用。

## Delivery Contract

- 输出生成的 HTML 文件路径。
- 如有图片，一并输出图片路径列表。
- 预览 URL（如支持）或打开方式说明。
**注意：本技能是大型流水线的一部分。Do **not** report completion to the user unless all dependent tools/scripts/skills integration tests have passed.**

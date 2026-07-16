# Rendering Strategy

Determine the right template based on content type and user intent.

## Strategy Flow

```
Input Content
    ↓
Step 1: Detect Content Type
    ↓ (auto or explicit)
→ Content Type:教材/培训/笔记/流程/对比/技术
    ↓
Step 2: Select Template
    ↓ (template selection matrix)
→ Template: chapter-explainer/training-page/workflow-page/etc.
    ↓
Step 3: Apply Theme
    ↓ (theme selection rules)
→ Theme: default/grace/simple/modern
    ↓
Step 4: Render HTML
    ↓ (template + theme + content)
→ Output: HTML + Screenshot
```

## Content Type Detection

### Auto-Detection (Primary Method)

Analyze content signals:

| Signal | Content Type |
|--------|--------------|
| "教程"、"教学"、"课堂"、"课程" | 教材 |
| "SOP"、"流程"、"步骤"、"培训" | 培训 |
| "笔记"、"读书"、"概念"、"知识点" | 知识讲解 |
| "流程图"、"workflow"、"步骤" | 流程/SOP |
| "对比"、"vs"、"A vs B"、"差异" | 对比分析 |
| "架构"、"模块"、"系统"、"技术" | 技术说明 |

### Explicit Selection (Fallback)

- User specifies: `--type <type>`
- Or choose from detected types

## Template Selection Matrix

| Content Type | Recommended Template | Why |
|--------------|----------------------|-----|
| 教材/课程 | `chapter-explainer.html` | Multi-module, learning objectives |
| 培训资料 | `training-page.html` | Prerequisites, FAQ, steps |
| 知识讲解 | `explainer-page.html` | Core concept, examples |
| 流程/SOP | `workflow-page.html` | Step-by-step with Mermaid |
| 对比分析 | `comparison-table.html` | A vs B, multi-factor |
| 技术说明 | `explainer-page.html` | Clear sections, diagrams |
| 快速对比 | `comparison-table.html` | Minimal, high-density |

## Rendering Logic

### Hybrid Strategy

| Content Density | Rendering Style |
|-----------------|-----------------|
| Low (1-2 concepts) | Hero + Body (short) |
| Medium (3-7 modules) | Hero + Modules + Reference |
| High (7+ concepts) | Hero + Modules + Submodules + Reference |

### Element Mapping

| Markdown Element | HTML Output | Notes |
|------------------|-------------|-------|
| `# Title` | Hero section | With metadata |
| `## Module` | Module card | With title, details |
| `### Subsection` | Subsection | Inside module |
| **Bold** | `<strong>` | Emphasis |
| _Italic_ | `<em>` | Emphasis |
| `> Quote` | Blockquote | Reference style |
| `---` | Horizontal rule | Section separator |
| Code blocks | `<pre><code>` | Syntax highlighted |
| `---` (three dashes) | Reference section | separation |

## Template Selection Examples

### Example 1: 教程内容

**Input**: "如何使用Git进行版本控制"

**Signals**: "如何使用" (tutorial), "Git" (technical)

**Detection**: → 教材/技术教程

**Template**: `chapter-explainer.html`

**Theme**: `grace` (educational friendly)

### Example 2: SOP 文件

**Input**: "日志收集SOP：从发现到解决"

**Signals**: "SOP" (explicit), "日志收集" (process)

**Detection**: → 培训/SOP

**Template**: `training-page.html`

**Theme**: `simple` (clear steps, minimal decoration)

### Example 3: 读书笔记

**Input**: "《原则》作者：瑞·达利欧 - 第三章 机器式思维"

**Signals**: "《" (book), "第三章" (chapter)

**Detection**: → 知识讲解/读书笔记

**Template**: `explainer-page.html`

**Theme**: `grace` (reading friendly)

## Advanced: Multi-Template Fallback

If primary template不合适:

1. Try base template
2. Check content density
3. If too dense → split or suggest Simplification
4. If too sparse → add examples or context

## Error Handling

| Error | Action |
|-------|--------|
| No clear content type | Ask user: "是教材/培训/笔记/流程/对比/技术？" |
| Template not found | Use default `explainer-page.html` |
| Theme not found | Use default theme `default` |

# Visual Knowledge Explainer - Templates

Template files for different content types.

## Templates

### 1. chapter-explainer.html

**Use for**: 教材/课程讲义/教学材料

**Features**:
- Learning objectives
- Module breakdown (3-7 modules)
- Examples in each module
- Common mistakes
- Review questions

### 2. training-page.html

**Use for**: 培训资料/SOP/流程文档

**Features**:
- Prerequisites
- Step-by-step workflow
- FAQ
- Troubleshooting

### 3. explainer-page.html

**Use for**: 知识讲解/读书笔记/技术说明

**Features**:
- Core concept summary
- Key points
- Examples
- Application examples
- Related concepts

### 4. workflow-page.html

**Use for**: 流程/SOP/步骤说明

**Features**:
- Mermaid flowchart
- Step-by-step narrative
- Visual aids

### 5. comparison-table.html

**Use for**: 对比分析/A vs B/特性对比

**Features**:
- HTML table (not just markdown)
- Clear headers
- Visual indicators

### 6. slide-deck.html

**Use for**: 快速演示/教学幻灯片

**Features**:
- Slide-style layout
- Clear hierarchy
- Bullet points

## Template Parameters

Each template accepts:
- `{title}` - Page title
- `{subtitle}` - Page subtitle
- `{theme}` - Theme name (default/grace/simple/modern)
- `{content}` - Main content
- `{learning_objectives}` - (optional) Learning objectives
- `{prerequisites}` - (optional) Prerequisites
- `{modules}` - (optional) Module breakdown
- `{examples}` - (optional) Examples
- `{faq}` - (optional) FAQ
- `{troubleshooting}` - (optional) Troubleshooting
- `{summary}` - (optional) Summary
- `{references}` - (optional) References

## Theme Integration

All templates include theme CSS variables:

```css
:root {
  --theme-primary: #color;
  --theme-secondary: #color;
  --theme-text: #color;
  --theme-background: #color;
  --theme-card-bg: #color;
  --theme-card-border: #color;
  --theme-heading-text: #color;
  --theme-heading-bg: #color;
  --spacing-unit: 8px;
  --font-size-base: 16px;
  --font-size-large: 20px;
  --font-size-small: 14px;
}
```

## Template Selection Logic

See `references/rendering-strategy.md` for detailed logic.

## Anti-Slop in Templates

Each template enforces:
- Structure (Hero/Body/Reference)
- Teaching elements (objectives, examples, mistakes)
- Visual hierarchy (not just text dump)

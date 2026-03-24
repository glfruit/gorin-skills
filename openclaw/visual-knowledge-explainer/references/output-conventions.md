# Output Conventions

File naming, directory structure, and delivery patterns.

## File Naming

### HTML Output
```
{content-title}-{timestamp}.html

Examples:
- git-intro-20260315-082900.html
- training-onboarding-20260315-082900.html
- note-concept-20260315-082900.html
```

### Markdown Preview (optional)
```
{content-title}-{timestamp}.md

Examples:
- git-intro-20260315-082900-preview.md
```

### Screenshot (optional)
```
{content-title}-{timestamp}.png

Examples:
- git-intro-20260315-082900.png
```

## Output Directory

### Default Location
```
~/Downloads/visual-explainer/

# Options
--output-dir <path>  # Custom directory
--output-file <name>  # Custom filename
```

### With Project Context (When Applicable)
```
.project/output/explainers/
  ├── git-intro-20260315-082900.html
  └── training-onboarding-20260315-082900.html
```

## Delivery Patterns

### Pattern 1: Return Path Only (Default)

**When**: Most common, when user doesn't specify

```json
{
  "output": {
    "type": "HTML",
    "path": "/Users/gorin/Downloads/visual-explainer/git-intro-20260315-082900.html",
    "file": "git-intro-20260315-082900.html",
    "size": "12KB",
    "timestamp": "2026-03-15 08:29:00"
  }
}
```

**Agent Action**: Return file path only

### Pattern 2: Return Path + Screenshot

**When**: User explicitly requests "生成截图"

```json
{
  "output": {
    "type": "HTML+Screenshot",
    "html": {
      "path": "/Users/gorin/Downloads/visual-explainer/git-intro-20260315-082900.html",
      "file": "git-intro-20260315-082900.html"
    },
    "screenshot": {
      "path": "/Users/gorin/Downloads/visual-explainer/git-intro-20260315-082900.png",
      "file": "git-intro-20260315-082900.png",
      "dimensions": "1920x1080"
    }
  }
}
```

**Agent Action**: Return path + screenshot path, possibly attach image

### Pattern 3: Preview in Chat

**When**: Short content (< 500 lines of HTML)

**Agent Action**: Return first 100-200 lines of HTML in code block

```html
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Git Intro</title>
  <style>
    /* ... */
  </style>
</head>
<body>
  <div class="explainer-page">
    <header class="hero-section">
      <h1>Git 版本控制入门</h1>
      <p class="subtitle">从零开始掌握 Git 基础操作</p>
    </header>
    <!-- ... -->
  </div>
</body>
</html>
```
```

### Pattern 4: Open in Browser

**When**: User explicitly requests "打开浏览器"

**Agent Action**: Return path, message like "已生成，可手动打开查看"

**Note**: Don't auto-open browser - user's preference varies

## Message Format

### Success Message
```
✅ 已生成 HTML 页面：

📄 输出文件: `git-intro-20260315-082900.html`
📁 位置: `~/Downloads/visual-explainer/`
💬 预览: 可在浏览器中打开查看
📷 如需截图，请回复"生成截图"
```

### With Screenshot
```
✅ 已生成 HTML 页面 + 截图：

📄 HTML: `git-intro-20260315-082900.html`
📷 截图: `git-intro-20260315-082900.png`
📁 位置: `~/Downloads/visual-explainer/`

可能会自动打开浏览器查看效果。
```

### With Preview
```
✅ 已生成 HTML 页面：

odb
```html
<div class="explainer-page">
  <header class="hero-section">
    <h1>Git 版本控制入门</h1>
    <p class="subtitle">从零开始掌握 Git 基础操作</p>
  </header>
  <!-- ... -->
</div>
```

📄 完整文件: `git-intro-20260315-082900.html`
📁 位置: `~/Downloads/visual-explainer/`
```

## Template Parameters

### HTML Template
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>{theme_css}</style>
</head>
<body>
  {content_html}
</body>
</html>
```

### Content HTML Structure
```html
<article class="explainer-page {theme}">
  {hero_section}
  
  {body_sections}
  <!-- Learning objectives -->
  <!-- Modules -->
  <!-- Examples -->
  <!-- Review -->
  
  {reference_section}
  <!-- Further reading -->
  <!-- Related concepts -->
</article>
```

## Theme CSS Integration

### Inline CSS (Default)
- All CSS in `<style>` tag
- No external dependencies
- Single file, portable

### Or External CSS (Optional)
```html
<link rel="stylesheet" href="themes/{theme}.css">
```

**Not recommended** for MVP - inline is simpler and more portable.

## Error Handling

### File Write Failed
```
❌ 文件写入失败：

原因: {error}
建议: 检查目录权限或路径是否存在
```

### Invalid Input
```
❌ 无法生成页面：

原因: 输入内容格式不正确
建议: 
- 提供 Markdown 内容
- 或粘贴正文内容
```

### Template Not Found
```
❌ 模板未找到：

模板: {template_name}
建议: 使用默认模板或联系开发者
```

## Batch Output (Future)

For multiple pages:

```
📁 输出目录: `~/Downloads/visual-explainer/batch-20260315-083000/`

├── git-intro.html
├── training-onboarding.html
├── note-concept.html
└── README.md (batch summary)
```

# Anti-Slop Rules

Concrete rules to prevent generic AI-style output.

## Core Principle

> "The goal is to make content **easier to teach, explain, and review** - not just 'look pretty'."

If your output:
- Looks like an AI generic page
- Doesn't help teaching/explanation
- Is just decoration without structure
- Doesn't save time for trainers/teachers

→ **STOP and revise.**

---

## Hard Rules

### 1. No Generic AI Page Layout

**❌ DON'T**:
- Centered text with large title
- Card-based layout everywhere
- "AI style" gradient backgrounds
- Default color scheme without thought

**✅ DO**:
- Structure based on content type
- Layout for teaching flow (concept → example → practice)
- Visual hierarchy that guides attention
- Theme selected intentionally

### 2. No Pure Text Dump

**❌ DON'T**:
- Just copy markdown to HTML
- No visual hierarchy
- No break between sections
- No examples or visuals

**✅ DO**:
- Module/break structure
- Examples after concepts
- Visual aids (Mermaid/images)
- Summary sections

### 3. No decoration over function

**❌ DON'T**:
- Color for color's sake
- Animations without purpose
- Complex layouts for complexity
- "Pretty" but hard to read

**✅ DO**:
- Colors for meaning (red = warning, green = success)
- Animations for flow (step-by-step reveal)
- Layouts for scannability
- Visuals for understanding

### 4. No generic templates

**❌ DON'T**:
- Same template for everything
- No content analysis
- No theme selection
- Copy-paste output

**✅ DO**:
- Analyze content first
- Select template intentionally
- Customize based on audience
- Add teaching-focused elements

### 5. No unstructured output

**❌ DON'T**:
- No Hero/Body/Reference sections
- No clear hierarchy
- No module breakdown
- No summary

**✅ DO**:
- Hero section (title, context, objectives)
- Body (structured modules)
- Reference section (further reading)

---

## Screener Questions

Before output, ask:

1. **Can this help someone teach?**
   - If no, revise

2. **Is there a clear learning path?**
   - Concept → Example → Practice
   - If no, revise

3. **Would this be useful for review?**
   - Clear highlights, summaries, Q&A
   - If no, revise

4. **Is the structure intentional or default?**
   - Template selected for content type
   - If default, revise

5. **Does every visual element add value?**
   - Mermaid: adds clarity
   - Images: explains concept
   - Colors: guides attention
   - If just decoration, remove

---

## Quality Checklist

Before final output, verify:

### Structure
- [ ] Hero section present
- [ ] Clear module breakdown (3-7 modules)
- [ ] Summary section present
- [ ] Reference section present

### Content
- [ ] Examples provided for concepts
- [ ] Common mistakes identified
- [ ] Learning objectives stated
- [ ] Application examples included

### Visual
- [ ] Mermaid used only where helpful
- [ ] Colors intentional (not decorative)
- [ ] Layout scannable
- [ ] Hierarchy clear

### Teaching
- [ ] Can someone teach from this?
- [ ] Can someone review from this?
- [ ] Is the content structured for learning?
- [ ] Are there review elements?

---

## Real Examples

### Good Output (✅)

```html
<!-- Chapter explainer for Git tutorial -->
<header class="hero-section">
  <h1>Git 版本控制入门</h1>
  <p class="subtitle">从零开始掌握 Git 基础操作</p>
  
  <div class="learning-objectives">
    <h3>学习目标</h3>
    <ul>
      <li>理解 Git 的基本概念</li>
      <li>掌握常用 Git 命令</li>
      <li>能够独立使用 Git 进行版本管理</li>
    </ul>
  </div>
</header>

<section class="modules">
  <article class="module">
    <h3>模块 1: Git 是什么</h3>
    <p>Git 是分布式版本控制系统...</p>
    
    <div class="example">
      <h4>示例</h4>
      <pre><code>$ git init</code></pre>
    </div>
    
    <div class="common-mistakes">
      <h4>常见错误</h4>
      <ul>
        <li>忘记添加文件到暂存区</li>
      </ul>
    </div>
  </article>
</section>
```

### Bad Output (❌)

```html
<!-- Generic AI page -->
<div class="card">
  <h1>Git 教程</h1>
  <p>这里是关于 Git 的内容...</p>
  <div class="card">
    <h2>Git 是什么</h2>
    <p>Git 是一个版本控制系统...</p>
  </div>
  <div class="card">
    <h2>安装 Git</h2>
    <p>下载并安装...</p>
  </div>
</div>
```

---

## Anti-Slop Triggers

If any of these appear in your output, **STOP**:

1. "Generic AI style" detected
   - Centered title with large space
   - Card layout everywhere
   - No structure beyond sections

2. "Just markdown converted"
   - No visual hierarchy added
   - No examples added
   - No module breakdown

3. "Decoration without meaning"
   - Bright colors everywhere
   - Animations without purpose
   - Complex layouts for no reason

4. "No teaching focus"
   - No learning objectives
   - No examples
   - No review elements

5. "Default template used"
   - Same as previous output
   - No content analysis
   - No theme selection

---

## Summary

**Remember**: This is a **teaching/explaining tool**, not a decoration tool.

Before output:
- Analyze content
- Select template
- Apply theme
- Structure for teaching
- Add learning elements
- Verify anti-slop

→ Only then generate HTML.

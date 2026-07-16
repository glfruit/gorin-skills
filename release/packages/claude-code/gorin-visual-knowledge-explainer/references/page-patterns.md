# Page Patterns

Template specifications for different content types.

## 1. Chapter Explainer (教材/课程)

**Use case**: Book chapters, course units, teaching materials

**Key features**:
- Learning objectives section
- Module breakdown (3-7 modules)
- Examples in each module
- Common mistakes
- Review questions

**Structure**:
```html
<article class="explainer-page">
  <header class="hero-section">
    <h1>Chapter Title</h1>
    <p class="subtitle">Chapter description</p>
    <div class="metadata">
      <span>Topic: XXX</span>
      <span>Level: Beginner/Intermediate/Advanced</span>
      <span>Time: ~15 min</span>
    </div>
  </header>
  
  <section class="learning-objectives">
    <h2>Learning Objectives</h2>
    <ul>
      <li>Understand...</li>
      <li>Be able to...</li>
    </ul>
  </section>
  
  <section class="modules">
    <article class="module">
      <h3>Module 1: Concept</h3>
      <p>Explanation...</p>
      <div class="example">
        <h4>Example</h4>
        <pre><code>...</code></pre>
      </div>
      <div class="common-mistakes">
        <h4>Common Mistakes</h4>
        <ul>
          <li>Mistake 1</li>
        </ul>
      </div>
    </article>
    <!-- More modules -->
  </section>
  
  <section class="reference">
    <h2>References</h2>
    <ul>
      <li>Related chapter</li>
      <li>Further reading</li>
    </ul>
  </section>
</article>
```

## 2. Training Page (培训/SOP)

**Use case**: Training materials, SOP documents, workflow guides

**Key features**:
- Prerequisites
- Estimated time
- Step-by-step with visual
- FAQ section
- Troubleshooting

**Structure**:
```html
<article class="training-page">
  <header class="hero-section">
    <h1>Training Title</h1>
    <p class="subtitle">SOP / Training material</p>
    <div class="metadata">
      <span>Target: Everyone</span>
      <span>Level: All</span>
      <span>Time: ~20 min</span>
    </div>
  </header>
  
  <section class="prerequisites">
    <h2>Prerequisites</h2>
    <ul>
      <li>Knowledge 1</li>
      <li>Tools: Tool 1, Tool 2</li>
    </ul>
  </section>
  
  <section class="workflow">
    <h2>Workflow</h2>
    <div class="steps">
      <div class="step">
        <h3>Step 1: Action</h3>
        <p>Description...</p>
        <img src="diagram.png" alt="Visual aid" />
      </div>
      <!-- More steps -->
    </div>
  </section>
  
  <section class="faq">
    <h2>FAQ</h2>
    <div class="qa-pairs">
      <div class="qa-pair">
        <h4>Q: Question?</h4>
        <p>A: Answer...</p>
      </div>
    </div>
  </section>
  
  <section class="troubleshooting">
    <h2>Troubleshooting</h2>
    <div class="issues">
      <div class="issue">
        <h4>Problem</h4>
        <p>Solution...</p>
      </div>
    </div>
  </section>
</article>
```

## 3. Explainer Page (知识讲解)

**Use case**: Notes, articles, concept explanations, summaries

**Key features**:
- Core concept summary
- Key points
- Examples
- Application examples
- Related concepts

**Structure**:
```html
<article class="explainer-page">
  <header class="hero-section">
    <h1>Concept Title</h1>
    <p class="subtitle">Brief context and relevance</p>
  </header>
  
  <section class="core-concept">
    <h2>Core Concept</h2>
    <p>Single paragraph summary...</p>
  </section>
  
  <section class="key-points">
    <h2>Key Points</h2>
    <div class="point">
      <h3>Point 1</h3>
      <p>Explanation...</p>
    </div>
    <!-- More points -->
  </section>
  
  <section class="examples">
    <h2>Examples</h2>
    <div class="example">
      <h3>Example 1</h3>
      <pre><code>...</code></pre>
    </div>
  </section>
  
  <section class="application">
    <h2>Application</h2>
    <p>How to use in practice...</p>
  </section>
  
  <section class="related">
    <h2>Related Concepts</h2>
    <ul>
      <li>Link to concept 1</li>
    </ul>
  </section>
</article>
```

## 4. Workflow Page (流程/SOP)

**Use case**: Process documentation, step-by-step procedures, workflows

**Key features**:
- Mermaid flowchart
- Step-by-step narrative
- Visual aids
- Variations

**Structure**:
```html
<article class="workflow-page">
  <header class="hero-section">
    <h1>Workflow Title</h1>
    <p class="subtitle">Process description</p>
  </header>
  
  <section class="visual-overview">
    <h2>Visual Overview</h2>
    <div class="mermaid">
      graph TD
        A[Start] --> B[Step 1]
        B --> C[Step 2]
        C --> D[End]
    </div>
  </section>
  
  <section class="workflow-steps">
    <h2>Workflow Steps</h2>
    <div class="step">
      <h3>Step 1</h3>
      <p>Description...</p>
    </div>
    <!-- More steps -->
  </section>
</article>
```

## 5. Comparison Table (对比分析)

**Use case**: Feature comparisons, A vs B, pros-cons, multi-factor analysis

**Key features**:
- HTML table (not just markdown)
- Clear headers
- Visual indicators

**Structure**:
```html
<article class="comparison-page">
  <header class="hero-section">
    <h1>Comparison Title</h1>
    <p class="subtitle">Feature comparison</p>
  </header>
  
  <section class="comparison-table">
    <h2>Comparison</h2>
    <table>
      <thead>
        <tr>
          <th>Criteria</th>
          <th>Option A</th>
          <th>Option B</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Feature 1</td>
          <td>Yes</td>
          <td>No</td>
        </tr>
      </tbody>
    </table>
  </section>
  
  <section class="summary">
    <h2>Summary</h2>
    <p>When to use A vs B...</p>
  </section>
</article>
```

## 6. Slide Deck (轻量PPT风格)

**Use case**: Quick slide-style presentations, teaching slides

**Key features**:
- Slide-style layout
- Clear hierarchy
- Bullet points
- Visual separation

**Structure**:
```html
<article class="slide-deck">
  <section class="slide">
    <h1>Slide 1: Title</h1>
    <p>Subtitle or context</p>
  </section>
  
  <section class="slide">
    <h2>Key Points</h2>
    <ul>
      <li>Point 1</li>
      <li>Point 2</li>
    </ul>
  </section>
  
  <section class="slide">
    <h2>Details</h2>
    <p>Content...</p>
  </section>
</article>
```

## Template Selection Rules Summary

| Content Type | Best Template | When to Use |
|--------------|---------------|-------------|
| 教材/课程 | `chapter-explainer.html` | Teaching material, multi-module |
| 培训资料 | `training-page.html` | SOP, training, steps |
| 知识讲解 | `explainer-page.html` | Notes, articles, concepts |
| 流程/SOP | `workflow-page.html` | Step-by-step workflows |
| 对比分析 | `comparison-table.html` | A vs B, features |
| 快速演示 | `slide-deck.html` | Slide-style, teaching |

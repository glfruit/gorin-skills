# Visual Knowledge Explainer - Golden Cases Research

## 1. Original Project: Visual-Explainer (nicobailon)

**URL**: https://github.com/nicobailon/visual-explainer

**Core Insights**:
- Focus on **structured, human-readable output** rather than pure decoration
- Aesthetic direction system (4 dimensions: texture, mood, typography, density)
- Anti-slop constraints (no generic AI-style pages)
- Hybrid rendering strategy (Mermaid + HTML tables + CSS Grid)
- Hero/Body/Reference section hierarchy
- Not just "dump text to HTML" - must be designed for teaching/presentation

**Key Commands**:
- `explainer <file>` - Generate explainer page
- `explainer <file> --style <style>` - With specific style
- `explainer <file> --mode <mode>` - Different rendering modes

**Mermaid Integration**:
- Flowcharts for processes
- Sequence diagrams for interactions
- Class diagrams for structures
- State diagrams for workflows

**HTML Strategy**:
- Table → HTML `<table>` (not just markdown)
- Complex data → Structured HTML
- Mermaid for visualization
- CSS Grid for layout

## 2. OpenClaw/Skill Structure Patterns

### Local Skills Reference:

#### baoyu-markdown-to-html
- **Flow**: Input check → Theme resolution → Conversion → Output
- **Theme System**: Ask User Question when no default found
- **EXTEND.md**: Support project-level and user-level config
- **Progressive Disclosure**: Core in SKILL.md, detail in references/

#### baoyu-slide-deck
- **Two Dimensions**: Layout × Style
- **Auto Selection**: Content signals → Preset recommendation
- **Style Gallery**: 15+ presets with clear use cases
- **Dimensions**: Texture × Mood × Typography × Density

#### baoyu-infographic
- **Two Dimensions**: Layout × Style
- **Layout Gallery**: 21 types (linear-progression, bento-grid, hub-spoke, etc.)
- **Style Gallery**: 20 styles (craft-handmade, chalkboard, cyberpunk-neon, etc.)
- **Recommended Combinations**: Content type → Layout + Style mapping

### Pattern Extraction:

| Pattern | Example from baoyu-infographic |
|---------|-------------------------------|
| Two-Dimension System | Layout (21) × Style (20) |
| Content Signals → Preset | Tutorial → `sketch-notes` |
| Style Gallery | 20 styles with descriptions |
| Layout Gallery | 21 layouts with use cases |
| Progress Disclosure | SKILL.md + references/ |
| Theme Resolution | EXTEND.md → AskUserQuestion |

## 3. Teaching/Presentation Page Patterns

### Educational Content Structure:
1. **Hero Section**: Title, author, date, learning objectives
2. **Overview**: Big picture, key takeaways
3. **Module Breakdown**: 3-7 modules, each with:
   - Concept explanation
   - Example/code/diagram
   - Common mistakes
   - Practice/review questions
4. **Summary**: Key points recap
5. **Reference Section**: Further reading, related resources

### Training/SOP Structure:
1. **Hero Section**: Title, target audience, estimated time
2. **Prerequisites**: What learners should know
3. **Workflow**: Step-by-step with visual
4. **FAQ**: Common questions
5. **Troubleshooting**: Issue + Solution pairs
6. **Reference**: Cheatsheet, quick reference

### Knowledge/Note Structure:
1. **Hero Section**: Title, context, relevance
2. **Core Concept**: Single paragraph summary
3. **Key Points**: Bullet list with explanations
4. **Examples**: Code/real-world examples
5. **Connections**: Related concepts
6. **应用 (Application)**: How to use in practice

## 4. Current Knowledge Workflow

### Content Origin → Explainer Page Flow:

```
URL/Article
    ↓
Baoyu-Url-To-Markdown (fetch + convert)
    ↓
Obsidian/PKM Note
    ↓
Baoyu-Markdown-To-HTML (visual explainer page)
    ↓
Preview/Screenshot
```

```
Training Outline
    ↓
Training Page Template
    ↓
Workflow/Step-by-step
    ↓
Mermaid Flowchart
    ↓
Training Explainer Page
```

```
Book Chapter
    ↓
Chapter_notes.md
    ↓
Explainer Page
    ↓
Teaching Material (explainable, reviewable)
```

## 5. Anti-Pattern Analysis

### What NOT to Do:
1. **Generic AI Page**: No content-specific design
2. **Just More Text**: No visual hierarchy
3. **Decoration Over Function**: Pretty but hard to teach from
4. **Tool-Focused**: CLI-heavy when user just wants a page
5. **No Context**: No audience/target specified

### What TO Do:
1. **Structure First**: Hero → Body → Reference
2. **Visualize Concepts**: Mermaid, diagrams, flowcharts
3. **Teaching-Oriented**: Objectives, examples, mistakes
4. **Flexible Rendering**: Auto-select based on content type
5. **Multiple Formats**: HTML + Markdown preview + Screenshot

## 6. Enhancement from Original Visual-Explainer

### Improve:
1. **Auto Content Recognition**: Identify教材/培训/SOP/文章/技术说明
2. **Theme System**: Default, Grace, Simple, Modern
3. **Multi-Output**: HTML + Markdown + Screenshot
4. **OpenClaw Native**: No plugin assumptions
5. **Teaching Focus**: Learning objectives, examples, mistakes

### Adapt:
1. Mermaid usage rules → Keep
2. Anti-slop constraints → Keep
3. Hero/Reference hierarchy → Keep
4. Hybrid rendering → Keep
5. Aesthetic dimensions → Adapt to 4 themes

## 7. Eval Criteria

### Eval A: 教材内容
- [ ] Learning objectives clear
- [ ] Module breakdown logical
- [ ] Examples present
- [ ] Common mistakes highlighted

### Eval B: 培训资料
- [ ] Prerequisites clear
- [ ] Steps logical
- [ ] FAQ present
- [ ] Troubleshooting section

### Eval C: 知识笔记
- [ ] Core concept clear
- [ ] Key points structured
- [ ] Examples provided
- [ ] Application examples

## 8. Template Planning

### Core Templates:
1. `explainer-page.html` - General knowledge explainer
2. `training-page.html` - Training/SOP page
3. `chapter-explainer.html` - Book chapter teaching page
4. `workflow-page.html` - Process/SOP visualization
5. `comparison-table.html` - A vs B, multi-factor comparison
6. `slide-deck.html` - Slide-style page (lightweight)

### References:
- `aesthetic-rules.md` - Theme guidelines
- `rendering-strategy.md` - Template selection logic
- `page-patterns.md` - Template details
- `teaching-page-patterns.md` - Educational structure guidelines
- `mermaid-guidelines.md` - Mermaid usage rules

### Scripts:
- `main.ts` - Entry point
- `detect-content-type.ts` - Auto content type recognition
- `select-template.ts` - Template selection logic
- `render-html.ts` - HTML generation
- `generate-screenshot.ts` - Screenshot capture
- `maybe-open.sh` - Optional browser open

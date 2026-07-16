# Aesthetic Direction System

Select theme based on content type and audience.

## Themes

| Theme | Best For | Visual Characteristics |
|-------|----------|------------------------|
| `default` | General teaching, overview pages | Classic layout, centered title, subtitle |
| `grace` | Elegant training, professional content | Shadow cards, rounded corners,精致 blocks |
| `simple` | Quick reference, modular content | Minimal, asymmetric rounded, white space |
| `modern` | Technical docs, modern teaching | Large radius, pill-shaped headings, loose spacing |

## Theme Selection Matrix

| Content Type | Recommended Theme |
|--------------|-------------------|
| 教材/课程讲义 | `grace` or `default` |
| 团队培训/SOP | `default` or `simple` |
| 读书笔记/知识讲解 | `grace` or `modern` |
| 流程/SOP | `simple` or `modern` |
| 技术说明/架构 | `modern` or `default` |
| 对比分析 | `default` or `grace` |

## Theme Configuration

Each theme defines:
- Typography (fonts, sizes, weights)
- Color palette (primary, secondary, text, background)
- Component styles (cards, headings, blocks)
- Spacing (gaps, padding, margins)
- Border/Rounding rules

## Theme Override

- **Explicit theme**: Use CLI `--theme <name>`
- **Content signals**: Auto-select based on content type
- **Default**: `default` if no match

## Recommended Combinations

| Content Type | Theme + Layout | Notes |
|--------------|----------------|-------|
| 教程/Tutorial | `grace` + chapter-explainer | Educational friendly |
| SOP/流程 | `simple` + workflow-page | Clear steps |
| 技术架构 | `modern` + explainer-page | Clean technical look |
| 对比分析 | `default` + comparison-table | Clean table display |
| 读书笔记 | `grace` + chapter-explainer | Reading friendly |

## Theme Details (Complete Spec - references/aesthetic-themes/)

See individual theme files for complete CSS variables:

- `references/aesthetic-themes/default.md` - Classic layout
- `references/aesthetic-themes/grace.md` - Elegant cards
- `references/aesthetic-themes/simple.md` - Minimal modern
- `references/aesthetic-themes/modern.md` - Technical contemporary

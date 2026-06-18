---
name: gorin-edu-markdown-polisher
description: Normalize Edu Team Markdown sources for textbook, course, and training products without changing meaning, version truth, or unrelated sections.
homepage: https://github.com/glfruit/gorin-skills/tree/main/skills/edu/gorin-edu-markdown-polisher
version: 0.1.0
metadata:
  {
    "openclaw": {
      "emoji": "📝",
      "os": ["darwin", "linux"],
      "requires": { "bins": [] }
    }
  }
---

# Edu Markdown Polisher

Use this skill to normalize Markdown formatting for teaching products. It
borrows `baoyu-format-markdown`'s useful focus on frontmatter, headings, lists,
code fences, typography, and CJK/English spacing, but adapts it for Edu Team
source governance.

The skill is not a rewriting skill. It must not change facts, chapter structure,
source truth, or unrelated content.

## Trigger

- "格式化 Markdown"
- "修复教材 Markdown 格式"
- "整理章节 Markdown"
- "修复代码围栏/列表/表格"
- "polish markdown source"

## Workflow

1. Lock scope
   - Identify exact files and exact problem classes.
   - For revision tasks, only edit the problematic ranges.

2. Run preflight
   - Check headings, lists, code fences, tables, local image paths, placeholders,
     figure/table captions, and obvious unresolved markers.

3. Apply minimal formatting
   - Fix Markdown syntax and readability only.
   - Preserve original text, claims, examples, and source order unless the issue
     explicitly requires a local change.

4. Run post-check
   - Compare changed ranges.
   - Confirm no unrelated sections changed.
   - Produce a formatting report.

## Recommended Checks

- `git diff --word-diff` or equivalent range comparison.
- Markdown lint or project-specific Markdown hygiene audit.
- Code fence count before/after.
- Table count before/after when the task is not table-related.
- Image reference count before/after when the task is not image-related.

## Not Allowed

- Do not turn DOCX/PDF-extracted text into canonical Markdown.
- Do not replace a chapter body wholesale to fix local formatting.
- Do not remove lists, tables, code blocks, or images unless the review item
  explicitly requires removal.
- Do not invent frontmatter fields that the product contract does not use.

## References

- `references/markdown-polish-checklist.md`

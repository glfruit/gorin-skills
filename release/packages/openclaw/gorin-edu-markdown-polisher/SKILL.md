---
name: gorin-edu-markdown-polisher
description: Format an existing canonical Markdown source for a textbook, course, or training product. Use for local heading, list, fence, table, image-path, typography, or CJK/English-spacing repairs where meaning and source order must remain unchanged. Do not use for semantic rewriting, restructuring a chapter, or converting DOCX/PDF extraction into canonical source.
license: MIT
homepage: "https://github.com/glfruit/gorin-skills/tree/main/skills/education/gorin-edu-markdown-polisher"
metadata: {"openclaw":{"emoji":"📝","os":["darwin","linux"],"requires":{"bins":[]}}}
---

# Edu Markdown Polisher

Repair Markdown presentation with a surgical diff. The source's facts, examples, structure, and version truth are invariants.

## Workflow

### 1. Lock the patch surface

List the exact files and issue classes. Record fence, table, image, and list counts when the requested change could affect them. Read `references/markdown-polish-checklist.md`. Completion means the allowed ranges and preserved structures are explicit.

### 2. Inspect before editing

Locate malformed headings, lists, fences, tables, local image paths, placeholders, captions, and CJK/English spacing. Separate formatting defects from requests that would change meaning; report semantic requests instead of silently performing them.

### 3. Apply the smallest formatting patch

Edit only the locked ranges. Preserve wording, heading order, examples, code behavior, table cells, image references, and frontmatter fields unless the user explicitly scoped one of them for repair.

### 4. Prove preservation

Review the changed ranges with `git diff --word-diff` or an equivalent comparison. Recount any protected structures from Step 1 and run the repository's Markdown check when present. Completion means every changed line belongs to an approved issue class and every unrelated count is unchanged.

### 5. Report

Return:

- files and ranges changed;
- formatting classes fixed;
- preservation checks and commands run;
- unresolved semantic or project-specific questions.

Do not describe the work as complete when an unrelated section changed or a protected structure count drifted.

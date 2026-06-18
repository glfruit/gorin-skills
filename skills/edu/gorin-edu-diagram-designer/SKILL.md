---
name: gorin-edu-diagram-designer
description: Design source-grounded educational diagrams for textbook, course, and training products, including workflow, architecture, state, data-flow, timeline, and structure diagrams.
homepage: https://github.com/glfruit/gorin-skills/tree/main/skills/edu/gorin-edu-diagram-designer
version: 0.1.0
metadata:
  {
    "openclaw": {
      "emoji": "📐",
      "os": ["darwin", "linux"],
      "requires": { "bins": [] }
    }
  }
---

# Edu Diagram Designer

Use this skill to plan and specify educational diagrams. It adapts the useful
diagram taxonomy and spacing discipline from `baoyu-diagram`, but uses Edu Team
rules: source-grounded concepts, figure manifest registration, captioned
automatic numbering, and no direct mutation of canonical manuscript text.

## Trigger

- "画流程图"
- "画架构图"
- "画状态机"
- "把这个概念画成图"
- "生成教材图示"
- "diagram for this chapter"

## Diagram Types

- `workflow`: ordered teaching or operation process.
- `architecture`: components and relationships.
- `state-machine`: lifecycle, task-state, learning-state transitions.
- `data-flow`: data movement, transformation, storage.
- `structure`: ER, class, module, hierarchy, concept taxonomy.
- `timeline`: chronological events or development phases.
- `comparison`: before/after, A/B, alternatives.

## Workflow

1. Identify the canonical source section and target learner difficulty.
2. Choose exactly one primary diagram type.
3. Write a diagram spec under `assets/diagrams/specs/`.
4. If using Mermaid/SVG, save source under `assets/diagrams/source/`.
5. Render output under `assets/diagrams/rendered/`.
6. Register the diagram in the project figure manifest.
7. Run visual QA: no overlap, readable labels, correct terminology, valid
   source/caption/placeholder.

## Required Spec

Every diagram spec must include:

- source Markdown path and section
- diagram type
- learner purpose
- required labels
- prohibited assumptions
- output path
- caption
- insertion placeholder
- QA checklist

## Not Allowed

- Do not turn all content into one huge diagram.
- Do not use dark technical diagrams for beginner-facing textbook pages unless
  the product style spec explicitly permits it.
- Do not invent relationships that are not in the source.
- Do not skip source files; rendered images alone are not enough.

## References

- `references/diagram-spec-template.md`

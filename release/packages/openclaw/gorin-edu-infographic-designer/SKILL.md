---
name: gorin-edu-infographic-designer
description: Design educational infographics for textbook, course, and training
  products with learning objectives, layout selection, source preservation, and
  QA evidence.
license: MIT
homepage: "https://github.com/glfruit/gorin-skills/tree/main/skills/education/gorin-edu-infographic-designer"
metadata: {"openclaw":{"emoji":"📊","os":["darwin","linux"],"requires":{"bins":[]}}}
---

# Edu Infographic Designer

Use this skill when a teaching product needs an infographic, dense visual
summary, quick card, process overview, comparison matrix, or visual checklist.

It borrows `baoyu-infographic`'s layout × style thinking and structured content
pipeline, but adapts it for Edu Team needs: source text preservation, learning
objective binding, manifest registration, and delivery QA.

## Trigger

- "做信息图"
- "做一张高密度信息大图"
- "把这一节做成速查图"
- "visual summary"
- "infographic for training"

## Layout Families

- `linear-progression`: steps, procedures, timelines.
- `comparison-matrix`: alternatives, before/after, criteria comparison.
- `hierarchical-layers`: Bloom levels, capability layers, priority levels.
- `hub-spoke`: central concept with related practices.
- `dashboard`: metrics and learning analytics.
- `dense-modules`: compact handout or review card.
- `circular-flow`: cycles, feedback loops, recurring workflows.

## Workflow

1. Save source excerpt and learning objective.
2. Select a layout family based on information structure, not aesthetics first.
3. Preserve source facts and terminology verbatim.
4. Write `structured-content.md` with sections, labels, and visual elements.
5. Confirm the manifest `engine` and `generator_route`. Prefer `html_svg`,
   `svg`, or another deterministic route for factual/data-heavy infographics.
   Use `ai_image` only when the manifest permits it and the prompt is saved.
6. Write a generation prompt under `assets/infographics/prompts/` only when the
   approved route needs a prompt.
7. Generate or delegate output under `assets/infographics/rendered/`.
8. Register manifest, caption, and placeholder.
9. Validate readability and factual fidelity.

## Not Allowed

- Do not summarize away required data.
- Do not add unverified statistics.
- Do not make infographic text too dense for the target page or slide.
- Do not package an infographic without source and prompt files.
- Do not choose an image/model/backend outside the manifest
  `generator_route`.

## References

- `references/infographic-brief-template.md`

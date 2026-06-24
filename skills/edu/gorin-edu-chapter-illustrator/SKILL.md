---
name: gorin-edu-chapter-illustrator
description: Plan and specify textbook chapter illustrations with source-grounded visual intent, insertion points, prompts, and QA evidence. Adapted for Edu Team chapter workflows; does not directly invoke third-party baoyu skills.
homepage: https://github.com/glfruit/gorin-skills/tree/main/skills/edu/gorin-edu-chapter-illustrator
version: 0.1.0
metadata:
  {
    "openclaw": {
      "emoji": "🖼️",
      "os": ["darwin", "linux"],
      "requires": { "bins": [] }
    }
  }
---

# Edu Chapter Illustrator

Use this skill when a textbook, course handout, or training handout needs
chapter-level visual planning: conceptual illustrations, process figures,
comparison visuals, activity cards, or explanatory images.

This skill borrows the useful structure of `baoyu-article-illustrator`: content
analysis, type × style thinking, saved outline, saved prompt files, and output
directory discipline. It is adapted for Edu Team governance: Markdown source is
truth, figures must have captions/placeholders/manifests, and no generated image
can be claimed complete without QA evidence.

## Trigger

- "给章节配图"
- "为教材章节设计插图"
- "这章哪里需要图"
- "根据章节内容规划图示"
- "generate illustrations for chapter"

## Workflow

1. Lock source
   - Identify canonical Markdown source.
   - Do not derive final visual requirements from DOCX/PDF extraction when
     Markdown exists.

2. Analyze teaching need
   - Identify learner difficulty, abstract concepts, workflows, comparisons,
     and places where text alone is too heavy.
   - Mark each proposed visual with a governed `figure_type`, such as
     `workflow`, `framework`, `architecture`, `data_model`, `er_diagram`,
     `code_result`, `data_chart`, `software_screenshot`,
     `concept_illustration`, `scenario_illustration`, `cover`,
     `infographic`, or `reference_qr`.

3. Create visual plan
   - Write `design/visual-plan.md` or update the current phase visual plan.
   - For each visual include source section, learning purpose, insertion
     placeholder, caption draft, asset path, and QA requirement.

4. Select engine before generation
   - Apply the project's Figure Engine Policy before writing prompts or
     generating assets.
   - Deterministic figures (`workflow`, `architecture`, `data_model`,
     `er_diagram`, `code_result`, `data_chart`, `table_figure`,
     `software_screenshot`) must use source-grounded engines such as Mermaid,
     PlantUML, Graphviz, SVG, HTML, Python, or real screenshots.
   - AI image generation is only allowed for `scenario_illustration`, `cover`,
     and approved `concept_illustration` / `infographic` items.
   - QR figures must use `engine=qr` with a recorded `target_url`,
     `source_url`, or `source_value`. If the target is not available yet,
     record `target_status`, `target_note`, and evidence path instead of
     approving a placeholder.
   - Record `engine`, `generator_route`, and `engine_reason` in
     `design/figure-manifest.json`.
   - Allowed generator routes are:
     `mermaid_cli` / `html_mermaid_renderer` for Mermaid;
     `plantuml_cli` for PlantUML; `graphviz_cli` for Graphviz;
     `source_svg` for SVG; `html_svg_renderer` for HTML/SVG;
     `html_canvas_renderer` for HTML canvas; `python_plot` for charts;
     `python_table` for table figures; `browser_screenshot` or
     `manual_screenshot` for screenshots; `runtime_capture` for real command
     or code output; `qr_generator` for QR; `manual_source` for supplied
     artwork; `openclaw_native_image` or `approved_gorin_skill` for approved AI
     images.
   - Do not switch to an undeclared backend in a worker prompt or chat message.

5. Create prompt or source files before generation
   - Save prompts under `assets/figures/prompts/`.
   - Do not generate from ad-hoc inline prompts.
   - Prompts must include teaching objective, audience, exact text labels, style
     boundary, aspect ratio, and forbidden elements.
   - For deterministic engines, save source under `assets/figures/source/`
     instead of inventing a prompt.

6. Generate or hand off
   - Use the project's approved image/diagram generator only after prompt files
     or source files exist.
   - If generation is delegated, include the manifest item, source/prompt path,
     engine, generator route, and expected output path in the worker contract.

7. Validate
   - Ensure every generated asset appears in `design/figure-manifest.json` or
     the project visual manifest.
   - Check local file existence, caption, placeholder, source section, and
     whether text in the image matches the source language.

## Output Structure

```text
assets/figures/
  prompts/
    fig-05-01-workflow.md
  source/
  generated/
    fig-05-01-workflow.png
  qa/
    fig-05-01-workflow-qa.md
```

## Not Allowed

- Do not insert decorative images that do not support a learning objective.
- Do not use AI image generation for factual diagrams, data models, code
  results, software interfaces, tables, or charts.
- Do not change unrelated chapter text while adding visuals.
- Do not overwrite human-provided source artwork.
- Do not claim "配图完成" without manifest and QA evidence.

## References

- `references/visual-plan-template.md`
- `references/figure-prompt-template.md`

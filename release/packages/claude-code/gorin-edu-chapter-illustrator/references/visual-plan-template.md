# Chapter Visual Plan

## Source

- Project:
- Canonical Markdown:
- Version:
- Chapter / section:

## Visual Items

| ID | Source Section | figure_type | engine | generator_route | generation_model | generation_backend | generation_evidence_path | engine_reason | Learning Purpose | Placeholder | Caption | Source/Prompt/Target | Asset Path | QA |
|----|----------------|-------------|--------|-----------------|------------------|--------------------|--------------------------|---------------|------------------|-------------|---------|----------------------|------------|----|
| fig-00-01 | | workflow/framework/data_model/concept_illustration/reference_qr | mermaid/svg/html_svg/ai_image/qr | mermaid_cli/html_svg_renderer/openclaw_native_image/qr_generator | `openai/gpt-image-2` for ai_image, otherwise null | concrete renderer/script/approved gorin-* skill | `assets/figures/qa/fig-00-01-generation.md` | Why this engine is allowed for this figure type | | `{{FIG:fig-00-01}}` | 图 0-1 ... | `assets/figures/source/fig-00-01.mmd` or `assets/figures/prompts/fig-00-01.md` or `target_url`/`target_status` | `assets/figures/generated/fig-00-01.png` | pending |

## Review Rules

- Every visual must reduce learner difficulty or support practice.
- Every visual must map to a source section.
- Every visual must have a caption and placeholder before generation.
- Every visual must have policy-compliant `figure_type`, `engine`,
  `generator_route`, `generation_model` where applicable,
  `generation_backend`, and `generation_evidence_path`.
- AI image `generation_model` must be an approved image model; current
  allowlist is `openai/gpt-image-2`.
- `generation_backend` must name the concrete controlled renderer/script or
  approved `gorin-*` skill, not an ad-hoc third-party skill or vague prose.
- AI image generation must not be used for factual/data/code/interface figures.
- QR figures must have a real target value, or a pending target status with a note and evidence path.

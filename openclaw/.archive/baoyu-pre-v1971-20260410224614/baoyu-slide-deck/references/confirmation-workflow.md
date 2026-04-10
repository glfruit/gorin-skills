# Confirmation Workflow Reference

Detailed AskUserQuestion formats for Step 2 confirmation.

## Round 1 (Always)

Display summary before asking:
- Content type + topic identified
- Language: [from EXTEND.md or detected]
- Recommended style: [preset] (based on content signals)
- Recommended slides: [N] (based on content length)

### Question 1: Style

```
header: "Style"
question: "Which visual style for this deck?"
options:
  - label: "{recommended_preset} (Recommended)"
    description: "Best match based on content analysis"
  - label: "{alternative_preset}"
    description: "[alternative style description]"
  - label: "Custom dimensions"
    description: "Choose texture, mood, typography, density separately"
```

### Question 2: Audience

```
header: "Audience"
question: "Who is the primary reader?"
options:
  - label: "General readers (Recommended)"
    description: "Broad appeal, accessible content"
  - label: "Beginners/learners"
    description: "Educational focus, clear explanations"
  - label: "Experts/professionals"
    description: "Technical depth, domain knowledge"
  - label: "Executives"
    description: "High-level insights, minimal detail"
```

### Question 3: Slide Count

```
header: "Slides"
question: "How many slides?"
options:
  - label: "{N} slides (Recommended)"
    description: "Based on content length"
  - label: "Fewer ({N-3} slides)"
    description: "More condensed, less detail"
  - label: "More ({N+3} slides)"
    description: "More detailed breakdown"
```

### Question 4: Review Outline

```
header: "Outline"
question: "Review outline before generating prompts?"
options:
  - label: "Yes, review outline (Recommended)"
    description: "Review slide titles and structure"
  - label: "No, skip outline review"
    description: "Proceed directly to prompt generation"
```

### Question 5: Review Prompts

```
header: "Prompts"
question: "Review prompts before generating images?"
options:
  - label: "Yes, review prompts (Recommended)"
    description: "Review image generation prompts"
  - label: "No, skip prompt review"
    description: "Proceed directly to image generation"
```

## Round 2 (Only if "Custom dimensions" selected in Q1)

### Question 1: Texture

```
header: "Texture"
question: "Which visual texture?"
options:
  - label: "clean"
    description: "Pure solid color, no texture"
  - label: "grid"
    description: "Subtle grid overlay, technical"
  - label: "organic"
    description: "Soft textures, hand-drawn feel"
  - label: "pixel"
    description: "Chunky pixels, 8-bit aesthetic"
```
(Note: "paper" available via Other)

### Question 2: Mood

```
header: "Mood"
question: "Which color mood?"
options:
  - label: "professional"
    description: "Cool-neutral, navy/gold"
  - label: "warm"
    description: "Earth tones, friendly"
  - label: "cool"
    description: "Blues, grays, analytical"
  - label: "vibrant"
    description: "High saturation, bold"
```
(Note: "dark", "neutral" available via Other)

### Question 3: Typography

```
header: "Typography"
question: "Which typography style?"
options:
  - label: "geometric"
    description: "Modern sans-serif, clean"
  - label: "humanist"
    description: "Friendly, readable"
  - label: "handwritten"
    description: "Marker/brush, organic"
  - label: "editorial"
    description: "Magazine style, dramatic"
```
(Note: "technical" available via Other)

### Question 4: Density

```
header: "Density"
question: "Information density?"
options:
  - label: "balanced (Recommended)"
    description: "2-3 key points per slide"
  - label: "minimal"
    description: "One focus point, maximum whitespace"
  - label: "dense"
    description: "Multiple data points, compact"
```

## After Confirmation

1. Update `analysis.md` with confirmed preferences
2. Store `skip_outline_review` flag from Question 4
3. Store `skip_prompt_review` flag from Question 5
4. → Step 3

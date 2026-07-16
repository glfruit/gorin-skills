---
name: gorin-edu-image-optimizer
description: Optimize teaching-product image assets without overwriting source
  files, while preserving manifest entries, captions, and review evidence.
license: MIT
homepage: "https://github.com/glfruit/gorin-skills/tree/main/skills/education/gorin-edu-image-optimizer"
metadata: {"openclaw":{"emoji":"🗜️","os":["darwin","linux"],"requires":{"bins":[]}}}
---

# Edu Image Optimizer

Use this skill to prepare images for textbook, course, and training packages:
compress large images, create web-friendly derivatives, preserve originals, and
update asset evidence.

It borrows `baoyu-compress-image`'s tool-selection and format preference idea,
but Edu Team policy is stricter: never overwrite originals, never lose source
quality, and always keep manifest/provenance.

## Trigger

- "压缩教材图片"
- "优化配图体积"
- "生成 WebP/PNG 派生图"
- "图片太大"
- "optimize teaching images"

## Workflow

1. Find manifest entries or target image list.
2. Record original file path, format, dimensions, and size.
3. Create derivatives under `assets/figures/optimized/` or the product's
   approved asset directory.
4. Keep originals unchanged under `source/`, `generated/`, or external source
   path.
5. Update the image manifest or derivative report.
6. Validate that referenced delivery files still exist.

## Format Policy

- Use PNG for diagrams, screenshots with text, and line art when clarity is
  more important than size.
- Use WebP or JPEG derivatives only for delivery surfaces that support them.
- Preserve source PNG/SVG for publishing and future edits.

## Not Allowed

- Do not overwrite original images.
- Do not replace source SVG/PNG with lossy delivery derivatives.
- Do not compress images before visual QA has passed unless the task is only a
  delivery-size experiment.
- Do not update Markdown references to optimized derivatives unless the delivery
  spec requires it.

## References

- `references/image-optimization-report-template.md`

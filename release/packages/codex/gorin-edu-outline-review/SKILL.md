---
name: gorin-edu-outline-review
description: Compare an existing teaching manuscript in Markdown with its approved Excel outline and report module/knowledge-point coverage, order drift, placeholder residue, and non-observable objective verbs. Use as an outline-conformance gate before content-quality review. Do not use to rewrite the manuscript, judge teaching quality, or review a document without both inputs.
license: MIT
---

# Edu Outline Review

This is a conformance review: it maps approved outline rows to manuscript evidence and produces a read-only report.

## Inputs

- one canonical manuscript `.md`;
- one approved outline `.xlsx` whose first sheet contains `项目名称`, `任务名称`, `模块/板块`, `知识点/技能点`, and `主要内容概要` headers;
- optional `textbook` template hint when the header begins near row 5.

Missing headers or zero reviewable outline rows fail closed.

## Workflow

1. Confirm both files and whether the outline uses the textbook template.
2. Run the analyzer from the installed skill directory:

   ```bash
   uv run --isolated --no-project --with openpyxl==3.1.5 \
     python /path/to/gorin-edu-outline-review/scripts/outline_review.py \
     manuscript.md outline.xlsx --template-type textbook \
     --output outline-review.md
   ```

3. Verify the report contains total and covered knowledge points, module coverage, missing rows with Excel row numbers, order problems, objective-verb findings, placeholders, and a pass/fix/return result.
4. Report the command, output path, and any heuristic match requiring human review. Do not edit either input.

## Decision rules

- coverage below 75% or at least three missing knowledge points: `退回`;
- coverage below 95% or any order/objective/placeholder issue: `需修复`;
- otherwise: `通过`.

The analyzer uses normalized and bounded fuzzy matching. A match is evidence for review, not proof of teaching quality.

## Verification

Run the public CLI regression suite:

```bash
PYTHONDONTWRITEBYTECODE=1 \
  uv run --isolated --no-project --with openpyxl==3.1.5 \
  python -m unittest discover \
  -s /path/to/gorin-edu-outline-review/tests -v
```

The review is complete only when the command succeeds, the report is saved or returned, and no source input changed.

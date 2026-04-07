# md2pdf v3 — Design Document

## 1. Goal

Merge the full-featured `md2pdf.py` (1309 lines) with the performance-optimized `gen_pdf_v2.py` (354 lines) into a single, fast, feature-complete Markdown→PDF converter.

**Key constraint:** Eliminate the O(N×K) bottleneck in `_font_wrap()` while preserving 95%+ of the original feature set.

## 2. Architecture

```
CLI (argparse)
  ├── --input       Markdown file (required)
  ├── --output      PDF path
  ├── --title       Cover title
  ├── --author      Author
  ├── --theme       Theme name (chinese-red, warm-academic, etc.)
  ├── --toc         Generate TOC + PDF bookmarks
  ├── --watermark   Watermark text
  ├── --clean       Markdown preprocessing (markdowncleaner + mdformat)
  └── --engine      python (default) | typst

Python Engine (v3 default):
  1. Register fonts (macOS system fonts)
  2. Load theme (color palette + layout)
  3. Parse Markdown → reportlab story
  4. Build PDF with BaseDocTemplate + PageTemplates

Typst Engine (implemented):
  1. pandoc --from markdown --to typst
  2. Post-process for Typst 0.14 compatibility
  3. Inject theme template (fonts, colors, cover, TOC, watermark, header/footer)
  4. typst compile → PDF
```

## 3. Font Strategy (Performance Fix)

### Problem
`_font_wrap()` scans every character against 11 CJK Unicode ranges for every text fragment. With 10K+ lines, this creates massive overhead.

### Solution: Global CJK Font
- **Body text**: `fontName = 'Songti'` (a CJK TTC that includes Latin glyphs)
- **Headings**: `fontName = 'STHeiti'` (also CJK)
- **No `_font_wrap()` on body paragraphs** — eliminated entirely
- **`wordWrap='CJK'`** handles line breaking natively in reportlab
- **Canvas text** (cover, headers, footers): Use CJK font directly via `canvas.setFont('Songti', size)` — no mixed-font needed since Songti renders Latin acceptably

### Trade-off
Latin characters use Songti's built-in Latin glyphs instead of Palatino. For Chinese-primary documents (the target use case), this is acceptable. Future optimization: fonttools merge Songti + Palatino into a single TTF for best-of-both-worlds.

### Font Registration
```python
pdfmetrics.registerFont(TTFont('Songti', '/System/Library/Fonts/Supplemental/Songti.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('SongtiBold', '/System/Library/Fonts/Supplemental/Songti.ttc', subfontIndex=1))
pdfmetrics.registerFont(TTFont('STHeiti', '/System/Library/Fonts/STHeiti Medium.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('STHeitiLight', '/System/Library/Fonts/STHeiti Light.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('Menlo', '/System/Library/Fonts/Menlo.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('MenloBold', '/System/Library/Fonts/Menlo.ttc', subfontIndex=1))
```

## 4. Features (v3)

### From Original (md2pdf.py)
- [x] Theme system (10+ themes)
- [x] PDF bookmarks (ChapterMark → bookmarkPage + addOutlineEntry)
- [x] Clickable TOC with anchor links
- [x] Cover page (3 styles: centered, left-aligned, minimal)
- [x] Page decoration (top-bar, left-stripe, corner-marks, etc.)
- [x] Watermark (35° tiled)
- [x] Running header + 3-column footer
- [x] Markdown tables with smart column widths
- [x] Code blocks with bg/border styles
- [x] Inline markdown: **bold**, *italic*, `code`, [links]
- [x] Blockquotes
- [x] Bullet and numbered lists
- [x] CJK smart paragraph merging (no space between CJK chars)
- [x] CLI interface (argparse)
- [x] Frontispiece + back cover support
- [x] Markdown preprocessing (--clean)
- [x] Obsidian vault `![[wikilink]]` expansion

### Removed (for performance)
- [ ] `_font_wrap()` — eliminated in favor of global CJK font
- [ ] `_draw_mixed()` — simplified to direct CJK font rendering
- [ ] `_is_cjk()` — only used for paragraph merging (minimal calls)

## 5. Module Structure

Single file: `md2pdf_v3.py`

```
md2pdf_v3.py
├── Fonts — register_fonts()
├── Themes — THEMES dict + load_theme() + _TYPST_THEME_MAP
├── Markdown Parser — parse_md()
├── Flowables — ChapterMark, HRule, etc.
├── PDFBuilder (Python/ReportLab engine)
├── Typst Engine — _typst_generate_template() + _run_typst_engine()
├── Vault expansion — expand_vault_links()
├── Markdown cleanup — clean_markdown()
└── CLI — main() → _run_python_engine() / _run_typst_engine()
```

## 6. Obsidian Vault Link Expansion

Support `![[filename]]` syntax:
1. Parse `![[target]]` from markdown
2. Search vault directory for `target.md`
3. Read file content, strip frontmatter
4. Replace the `![[...]]` with file content

## 7. Markdown Cleanup (--clean)

Optional preprocessing pipeline:
1. `markdowncleaner`: remove noise, fix encoding
2. `mdformat` + `mdformat-gfm`: normalize formatting

Both are optional — skip if not installed.

## 8. Performance (实测数据)

测试文件: 职业教育政策五年汇编 (~11K lines after vault expansion, 214 TOC entries)

| Metric | Python Engine | Typst Engine |
|--------|:-----------:|:-----------:|
| 耗时 | 2.4s | 2.0s |
| PDF 大小 | 2.4 MB | 3.7 MB |
| CJK 显示 | ✅ Songti | ✅ Songti SC |
| 封面/目录/水印 | ✅ | ✅ |
| 页眉页脚 | ✅ | ✅ |

Note: 两者均使用 macOS Apple Silicon, typst 0.14.2, pandoc 3.9。

### v3.1 Updates (2026-04-07)
- [x] textbook-green theme (forest green + gold, for engineering textbooks)
- [x] textbook-cyber theme (deep indigo + cyber teal, for CS textbooks)
- [x] Subtitle no longer rendered on cover page (only in header/TOC)
- [x] H5/H6 heading support
- [x] Blockquote rendering fix (strip ">" prefix, merge consecutive lines)

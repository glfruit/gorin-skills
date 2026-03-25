---
name: pdf
description: Use this skill whenever the user wants to do anything with PDF files. This includes reading or extracting text/tables from PDFs, combining or merging multiple PDFs into one, splitting PDFs apart, rotating pages, adding watermarks, creating new PDFs, filling PDF forms, encrypting/decrypting PDFs, extracting images, and OCR on scanned PDFs to make them searchable. If the user mentions a .pdf file or asks to produce one, use this skill.
license: Proprietary. LICENSE.txt has complete terms
---

# PDF Processing Guide

## Quick Start

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")
text = ""
for page in reader.pages:
    text += page.extract_text()
```

## Quick Reference

| Task | Best Tool | Command/Code |
|------|-----------|--------------|
| Read/extract text | pdfplumber | `page.extract_text()` |
| Extract tables | pdfplumber | `page.extract_tables()` |
| Merge PDFs | pypdf | `writer.add_page(page)` |
| Split PDFs | pypdf | One page per file |
| Create PDFs | reportlab | Canvas or Platypus |
| Rotate pages | pypdf | `page.rotate(90)` |
| Add watermark | pypdf | `page.merge_page(watermark)` |
| Password protection | pypdf | `writer.encrypt(...)` |
| OCR scanned PDFs | pytesseract | Convert to image first |
| Extract images | pdfimages (CLI) | `pdfimages -j input.pdf prefix` |
| CLI merge | qpdf | `qpdf --empty --pages ...` |
| CLI text extraction | pdftotext | `pdftotext input.pdf output.txt` |
| Fill PDF forms | pdf-lib / pypdf | See FORMS.md |

## Python Libraries

- **pypdf**: Read, write, merge, split, rotate, encrypt
- **pdfplumber**: Text/table extraction with layout preservation
- **reportlab**: Create PDFs from scratch (Canvas or Platypus)

## Command-Line Tools

- **qpdf**: Merge, split, rotate, decrypt (fast, lightweight)
- **pdftotext** (poppler-utils): Text extraction
- **pdftk**: Merge, split, rotate
- **pdfimages** (poppler-utils): Extract images

详见 `references/processing-examples.md`（完整代码示例、高级表格提取、OCR、水印、密码保护）

## Important Notes

- reportlab: Never use Unicode subscripts/superscripts — use `<sub>`/`<super>` XML tags instead
- For advanced features and JavaScript libraries, see REFERENCE.md
- For PDF form filling, see FORMS.md

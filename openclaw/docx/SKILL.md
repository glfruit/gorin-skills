---
name: docx
description: "Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files). Triggers include: any mention of 'Word doc', 'word document', '.docx', or requests to produce professional documents with formatting like tables of contents, headings, page numbers, or letterheads. Also use when extracting or reorganizing content from .docx files, inserting or replacing images in documents, performing find-and-replace in Word files, working with tracked changes or comments, or converting content into a polished Word document. If the user asks for a 'report', 'memo', 'letter', 'template', or similar deliverable as a Word or .docx file, use this skill. Do NOT use for PDFs, spreadsheets, Google Docs, or general coding tasks unrelated to document generation."
license: Proprietary. LICENSE.txt has complete terms
---

# DOCX creation, editing, and analysis

## Overview

A .docx file is a ZIP archive containing XML files.

## Quick Reference

| Task | Approach |
|------|----------|
| Read/analyze content | `pandoc` or unpack for raw XML |
| Create new document | Use `docx-js` — 详见 `references/docx-js-creation.md` |
| Edit existing document | Unpack → edit XML → repack — 详见 `references/xml-editing.md` |

### Converting .doc to .docx

Legacy `.doc` files must be converted before editing:

```bash
python scripts/office/soffice.py --headless --convert-to docx document.doc
```

### Reading Content

```bash
# Text extraction with tracked changes
pandoc --track-changes=all document.docx -o output.md

# Raw XML access
python scripts/office/unpack.py document.docx unpacked/
```

### Converting to Images

```bash
python scripts/office/soffice.py --headless --convert-to pdf document.docx
pdftoppm -jpeg -r 150 document.pdf page
```

### Accepting Tracked Changes

```bash
python scripts/accept_changes.py input.docx output.docx
```

---

## Creating New Documents

Generate .docx files with JavaScript, then validate. 详见 `references/docx-js-creation.md`

Key rules:
- Set page size explicitly (docx-js defaults to A4)
- Never use unicode bullets — use `LevelFormat.BULLET`
- Tables need dual widths (`columnWidths` + cell `width`), always use DXA
- `ShadingType.CLEAR` not SOLID for table shading
- `PageBreak` must be inside a `Paragraph`
- `ImageRun` requires `type` parameter
- Include `outlineLevel` for TOC headings

## Editing Existing Documents

**Follow all 3 steps in order.**

### Step 1: Unpack
```bash
python scripts/office/unpack.py document.docx unpacked/
```
Extracts XML, pretty-prints, merges adjacent runs, converts smart quotes to XML entities.

### Step 2: Edit XML

Edit files in `unpacked/word/`. 详见 `references/xml-editing.md`

- **Use "Claude" as the author** for tracked changes and comments
- **Use the Edit tool directly** — do not write Python scripts
- Use XML entities for smart quotes: `&#x2019;`, `&#x201C;`, `&#x201D;`
- **Adding comments**: `python scripts/comment.py unpacked/ 0 "Comment text"`

### Step 3: Pack
```bash
python scripts/office/pack.py unpacked/ output.docx --original document.docx
```
Validates with auto-repair, condenses XML. Use `--validate false` to skip.

**Auto-repair fixes:** `durableId` overflow, missing `xml:space="preserve"`
**Auto-repair won't fix:** Malformed XML, invalid nesting, missing relationships

## References

| File | Content |
|------|---------|
| `references/docx-js-creation.md` | Complete JS code templates for all document elements |
| `references/xml-editing.md` | Tracked changes, comments, images, smart quotes in XML |

## Dependencies

- **pandoc**: Text extraction
- **docx**: `npm install -g docx` (new documents)
- **LibreOffice**: PDF conversion (auto-configured via `scripts/office/soffice.py`)
- **Poppler**: `pdftoppm` for images

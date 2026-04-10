# Advanced CLI Operations

Direct CLI: `/Users/gorin/doc-collab/.venv/lib/python3.12/site-packages/superdoc_sdk_cli_darwin_arm64/bin/superdoc`

All via `superdoc call <operationId> --input-json '<json>'` or wrapper script `superdoc-edit.sh`.

## Tables

| Operation | Description |
|-----------|-------------|
| `tables.get` | Retrieve table structure by locator |
| `tables.get-cells` | Get cell info, filter by row/column |
| `tables.insert-row` | Insert row |
| `tables.delete-row` | Delete row |
| `tables.insert-column` | Insert column |
| `tables.merge-cells` | Merge cell range |
| `tables.unmerge-cells` | Unmerge |
| `tables.sort` | Sort rows by column |
| `tables.set-style` | Apply table style |
| `tables.set-shading` | Background color |
| `tables.set-borders` | Border configuration |
| `tables.clear-contents` | Clear all cell content |
| `tables.delete` | Delete entire table |
| `tables.move` | Move table to new position |

## Footnotes & Endnotes

| Operation | Description |
|-----------|-------------|
| `footnotes.list` | List all footnotes/endnotes |
| `footnotes.get` | Get details by ID |
| `footnotes.insert` | Insert footnote at target |
| `footnotes.update` | Update content |
| `footnotes.remove` | Remove footnote |
| `footnotes.configure` | Set numbering/placement |

## Hyperlinks

| Operation | Description |
|-----------|-------------|
| `hyperlinks.list` | List all hyperlinks |
| `hyperlinks.wrap` | Wrap text range with link |
| `hyperlinks.insert` | Insert new linked text |
| `hyperlinks.patch` | Update URL/tooltip |
| `hyperlinks.remove` | Remove (unwrap or delete) |

## Sections & Page Setup

| Operation | Description |
|-----------|-------------|
| `sections.list` | List sections |
| `sections.set-page-margins` | Set margins |
| `sections.set-page-setup` | Size/orientation |
| `sections.set-columns` | Column layout |
| `sections.set-page-numbering` | Number format/start |

## Content Controls (SDT)

| Operation | Description |
|-----------|-------------|
| `content-controls.list` | List all controls |
| `content-controls.get` | Get by target |
| `content-controls.wrap` | Wrap content with control |
| `content-controls.unwrap` | Remove control |
| `content-controls.set-type` | Change type |
| `content-controls.text.set-value` | Set plain text value |
| `content-controls.date.set-value` | Set date value |
| `content-controls.checkbox.toggle` | Toggle checkbox |

## Document Diff & History

| Operation | Description |
|-----------|-------------|
| `diff.capture` | Snapshot current state |
| `diff.compare` | Compare against snapshot |
| `diff.apply` | Apply computed diff |
| `history.get` | Query undo/redo state |
| `history.undo` | Undo last mutation |
| `history.redo` | Redo |

## Formatting (Paragraph)

| Operation | Description |
|-----------|-------------|
| `format.paragraph.set-alignment` | Justification |
| `format.paragraph.set-indentation` | Left/right/firstLine/hanging (twips) |
| `format.paragraph.set-spacing` | Before/after/line (twips) |
| `format.paragraph.set-tab-stop` | Add tab stop |
| `format.paragraph.clear-all-tab-stops` | Remove all tab stops |

## Citations & Bibliography

| Operation | Description |
|-----------|-------------|
| `citations.list` | List citation marks |
| `citations.insert` | Insert citation mark |
| `citations.bibliography.insert` | Insert bibliography block |
| `citations.bibliography.rebuild` | Rebuild from sources |
| `citations.bibliography.configure` | Set bibliography style |

## Bookmarks & Cross-references

| Operation | Description |
|-----------|-------------|
| `bookmarks.list` | List bookmarks |
| `bookmarks.insert` | Insert named bookmark |
| `bookmarks.remove` | Remove bookmark |
| `cross-refs.list` | List cross-reference fields |
| `cross-refs.insert` | Insert cross-reference |
| `cross-refs.rebuild` | Recalculate |

## Images

| Operation | Description |
|-----------|-------------|
| `images.list` | List all images |
| `images.set-size` | Set width/height |
| `images.move` | Move to new location |
| `images.replace-source` | Replace image file |
| `images.crop` | Apply crop |
| `images.rotate` | Set rotation angle |

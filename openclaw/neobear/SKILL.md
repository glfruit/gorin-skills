---
name: neobear
description: Next-gen Bear notes integration with perfect URL encoding - Create, search, and manage Bear notes properly
homepage: https://bear.app
metadata:
  {
    "openclaw":
      {
        "emoji": "🐻💫",
        "os": ["darwin"],
        "requires": { "bins": ["python3"] },
        "install":
          [
            {
              "id": "neobear-cli",
              "kind": "download",
              "url": "https://raw.githubusercontent.com/glfruit/neobear/main/neobear_cli.py",
              "extract": false,
              "targetDir": "~/.local/bin",
              "bins": ["neobear_cli.py"],
              "label": "Install neobear_cli.py (Python script)",
            },
          ],
      },
  }
---

# 🐻💫 NeoBear - Next-Gen Bear Notes Integration

**Where old Bear links become new again.**

NeoBear is a modern Bear notes integration that properly handles URL encoding. Uses correct percent-encoding (`%20` for spaces) instead of plus-encoding (`+`), preventing the "spaces become plus signs" bug.

## Key Features

- ✅ **Perfect Encoding** — Uses `%20` not `+` for spaces
- ✅ **Modern Code** — Python 3.7+ best practices
- ✅ **Smart Validation** — Catches errors before they happen
- ✅ **Rich Output** — JSON support for automation
- ✅ **Better UX** — Clear feedback, helpful errors

## Usage in OpenClaw

### Create Notes

```
Create a Bear note titled "Meeting Notes" with content "Discussed project timeline"
Create a Bear note from the file `<path>` with title "Monthly Report"
```

With tags:
```
Create a Bear note:
- Title: "Project Ideas"
- Content: "New feature brainstorming"
- Tags: work, projects, 2026
```

### Search Notes

```
Search Bear notes for "project"
Find all Bear notes tagged with "work"
Search Bear for "meeting" and show only titles
```

### Open/Manage Notes

```
Open the Bear note titled "Daily Journal"
Append "Update: Project completed" to Bear note "Project Status"
Archive the Bear note "Old Ideas"
Delete the Bear note "Temporary Note"
```

## CLI Quick Reference

```bash
neobear_cli.py create --title "Note" --text "Content" [--tags work] [--pin] [--timestamp]
neobear_cli.py search --query "project" [--tag work] [--json] [--titles-only]
neobear_cli.py open --id "NOTE_ID" [--title "My Note"] [--new-window] [--edit]
neobear_cli.py add-text --id "NOTE_ID" --text "Content" [--mode append] [--new-line]
neobear_cli.py archive --id "NOTE_ID"
neobear_cli.py trash --id "NOTE_ID"
```

详见 `references/cli-reference.md`（安装、完整命令参考、高级用法、示例、故障排除）

## Requirements

- Bear app installed on macOS
- Python 3.6+
- Bear API token (for some operations) — see `references/cli-reference.md`

## Links

- **Bear App**: https://bear.app
- **Bear URL Scheme Docs**: https://bear.app/faq/X-callback-url%20Scheme%20documentation/

---

**Version:** 2.0.0 | **Platform:** macOS only | **License:** MIT

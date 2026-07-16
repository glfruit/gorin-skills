# NeoBear CLI Reference

## Installation

### Automatic

The skill auto-installs `neobear_cli.py` to `~/.local/bin/`. Ensure in PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Manual

```bash
curl -o ~/.local/bin/neobear_cli.py https://raw.githubusercontent.com/glfruit/neobear/main/neobear_cli.py
chmod +x ~/.local/bin/neobear_cli.py
neobear_cli.py --version
```

## Requirements

- Bear app installed and running on macOS
- Python 3.6+
- Bear API token (for some operations)

## Getting a Bear Token

1. Open Bear → Help → API Token → Copy Token
2. Save: `mkdir -p ~/.config/bear && echo "TOKEN" > ~/.config/bear/token`

## CLI Commands

### Create a Note

```bash
neobear_cli.py create --title "My Note" --text "Content here"
echo "Content" | neobear_cli.py create --title "My Note"
neobear_cli.py create --title "Report" --file report.md
neobear_cli.py create --title "Ideas" --text "Brainstorm" --tags work,projects
neobear_cli.py create --title "Note" --text "Content" --pin --timestamp --new-window
```

### Search Notes

```bash
neobear_cli.py search --query "project"
neobear_cli.py search --tag "work"
neobear_cli.py search --query "meeting" --json
neobear_cli.py search --query "ideas" --titles-only
```

### Open a Note

```bash
neobear_cli.py open --id "NOTE_ID_HERE"
neobear_cli.py open --title "My Note"
neobear_cli.py open --title "Note" --new-window --edit
```

### Add to Note

```bash
neobear_cli.py add-text --id "NOTE_ID" --text "Additional content"
neobear_cli.py add-text --id "NOTE_ID" --text "New section" --mode append --new-line
```

### Manage Notes

```bash
neobear_cli.py archive --id "NOTE_ID"
neobear_cli.py trash --id "NOTE_ID"
neobear_cli.py open --id "NOTE_ID" --pin
```

## Advanced Usage

### JSON Output

```bash
neobear_cli.py search --query "project" --json
```

Output:
```json
{
  "success": true,
  "notes": [
    {
      "identifier": "ABCD-1234",
      "title": "Project Ideas",
      "tags": ["work", "projects"],
      "created": "2026-02-03T10:00:00Z"
    }
  ]
}
```

### Dry Run Mode

```bash
neobear_cli.py create --title "Test Note" --text "Content" --dry-run
```

### Verbose Mode

```bash
neobear_cli.py create --title "Note" --text "Content" --verbose
```

## Examples

### Daily Journal

```bash
DATE=$(date +"%Y-%m-%d")
neobear_cli.py create --title "Journal $DATE" --text "Today's thoughts..." --tags journal,daily --timestamp
```

### Meeting Notes

```bash
neobear_cli.py create --title "Team Meeting $(date +%Y-%m-%d)" --file meeting-notes.md --tags meetings,team,work --pin
```

### Quick Capture

```bash
pbpaste | neobear_cli.py create --title "Quick Note" --tags inbox
```

## Bear URL Scheme

NeoBear uses Bear's x-callback-url API with proper encoding:

```
bear://x-callback-url/create?title=My%20Note&text=Content
```

Key difference: `%20` for spaces, not `+`.

Available actions: create, open-note, add-text, search, trash, archive

## Comparison with Old Tools

| Feature | Old Tools | NeoBear |
|---------|-----------|---------|
| **Space Encoding** | `+` (broken) | ✅ `%20` (correct) |
| **Error Messages** | Generic | ✅ Detailed |
| **JSON Output** | No | ✅ Yes |
| **Dry Run** | No | ✅ Yes |
| **Validation** | Basic | ✅ Smart |
| **Code Quality** | Legacy | ✅ Modern |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "open command not found" | macOS required |
| "Token required" | Set up token |
| Spaces showing as `+` | Using old tool, switch to NeoBear |
| Command not found | Check PATH includes `~/.local/bin` |

## Tips

1. Use tags liberally for easier searching
2. Pin important notes to keep at top
3. Use timestamps for tracking creation/updates
4. JSON output for scripting and automation
5. Dry run to test before executing

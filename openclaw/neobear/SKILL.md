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
              "url": "https://raw.githubusercontent.com/YOUR_USERNAME/neobear/main/neobear_cli.py",
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

NeoBear is a modern Bear notes integration for OpenClaw that properly handles URL encoding. Unlike older tools, NeoBear uses correct percent-encoding (`%20` for spaces) instead of plus-encoding (`+`), preventing the infamous "spaces become plus signs" bug.

## 🌟 What Makes It "Neo"?

### New Generation Features
- ✅ **Perfect Encoding** - Uses `%20` not `+` for spaces
- ✅ **Modern Code** - Python 3.7+ best practices
- ✅ **Smart Validation** - Catches errors before they happen
- ✅ **Rich Output** - JSON support for automation
- ✅ **Better UX** - Clear feedback, helpful errors

### The Problem (Solved)

**Old tools:**
```
Create note "My Note" → Bear shows "My+Note"  ❌
```

**NeoBear:**
```
Create note "My Note" → Bear shows "My Note"  ✅
```

## 📋 Requirements

- **Bear app** installed and running on macOS
- **Python 3.6+** (pre-installed on macOS)
- **Bear API token** (for some operations)

## 🔑 Getting a Bear Token

Some operations require authentication:

1. Open Bear → **Help** → **API Token** → **Copy Token**
2. Save it:
   ```bash
   mkdir -p ~/.config/bear
   echo "YOUR_TOKEN_HERE" > ~/.config/bear/token
   ```

## 🚀 Installation

### Automatic Installation

The skill auto-installs `neobear_cli.py` to `~/.local/bin/`.

Ensure this directory is in your PATH:

```bash
# Add to ~/.zshrc or ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"
```

### Manual Installation

```bash
# Download script
curl -o ~/.local/bin/neobear_cli.py https://raw.githubusercontent.com/YOUR_USERNAME/neobear/main/neobear_cli.py

# Make executable
chmod +x ~/.local/bin/neobear_cli.py

# Test it
neobear_cli.py --version
```

## 📖 Usage in OpenClaw

### Create Notes

**Simple note:**
```
Create a Bear note titled "Meeting Notes" with content "Discussed project timeline"
```

**With tags:**
```
Create a Bear note:
- Title: "Project Ideas"
- Content: "New feature brainstorming"
- Tags: work, projects, 2026
```

**From file:**
```
Create a Bear note from the file ~/Documents/report.md with title "Monthly Report"
```

### Search Notes

**By keyword:**
```
Search Bear notes for "project"
```

**By tag:**
```
Find all Bear notes tagged with "work"
```

**Show only titles:**
```
Search Bear for "meeting" and show only titles
```

### Open Notes

**By title:**
```
Open the Bear note titled "Daily Journal"
```

**By ID:**
```
Open Bear note with ID "ABCD-1234-EFGH"
```

### Manage Notes

**Add to note:**
```
Append "Update: Project completed" to Bear note "Project Status"
```

**Archive note:**
```
Archive the Bear note "Old Ideas"
```

**Trash note:**
```
Delete the Bear note "Temporary Note"
```

## 🛠️ Command Line Interface

### Create a Note

```bash
# From text
neobear_cli.py create --title "My Note" --text "Content here"

# From stdin
echo "Content" | neobear_cli.py create --title "My Note"

# From file
neobear_cli.py create --title "Report" --file report.md

# With tags
neobear_cli.py create --title "Ideas" --text "Brainstorm" --tags work,projects

# With options
neobear_cli.py create --title "Note" --text "Content" \
  --pin \
  --timestamp \
  --new-window
```

### Search Notes

```bash
# By keyword
neobear_cli.py search --query "project"

# By tag
neobear_cli.py search --tag "work"

# Output as JSON
neobear_cli.py search --query "meeting" --json

# Show only titles
neobear_cli.py search --query "ideas" --titles-only
```

### Open a Note

```bash
# By ID
neobear_cli.py open --id "NOTE_ID_HERE"

# By title
neobear_cli.py open --title "My Note"

# With options
neobear_cli.py open --title "Note" --new-window --edit
```

### Add to Note

```bash
# Append text
neobear_cli.py add-text --id "NOTE_ID" --text "Additional content"

# With mode
neobear_cli.py add-text --id "NOTE_ID" \
  --text "New section" \
  --mode append \
  --new-line
```

### Manage Notes

```bash
# Archive
neobear_cli.py archive --id "NOTE_ID"

# Trash
neobear_cli.py trash --id "NOTE_ID"

# Pin/Unpin
neobear_cli.py open --id "NOTE_ID" --pin
```

## 🎯 Examples

### Example 1: Daily Journal

```bash
# Create today's journal entry
DATE=$(date +"%Y-%m-%d")
neobear_cli.py create \
  --title "Journal $DATE" \
  --text "Today's thoughts..." \
  --tags journal,daily \
  --timestamp
```

### Example 2: Meeting Notes

```bash
# Capture meeting notes
neobear_cli.py create \
  --title "Team Meeting $(date +%Y-%m-%d)" \
  --file meeting-notes.md \
  --tags meetings,team,work \
  --pin
```

### Example 3: Quick Capture

```bash
# Quick note from clipboard
pbpaste | neobear_cli.py create --title "Quick Note" --tags inbox
```

### Example 4: Search and Process

```bash
# Find all work notes
neobear_cli.py search --tag "work" --json | jq '.notes[].title'

# Find recent notes
neobear_cli.py search --query "2026" --titles-only
```

## 🔧 Advanced Usage

### JSON Output

All commands support `--json` for structured output:

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

Test commands without executing:

```bash
neobear_cli.py create \
  --title "Test Note" \
  --text "Content" \
  --dry-run
```

Shows the URL that would be executed.

### Verbose Mode

See detailed execution info:

```bash
neobear_cli.py create \
  --title "Note" \
  --text "Content" \
  --verbose
```

## 🆚 Comparison with Old Tools

| Feature | Old Tools | NeoBear |
|---------|-----------|---------|
| **Space Encoding** | `+` (broken) | ✅ `%20` (correct) |
| **Error Messages** | Generic | ✅ Detailed |
| **JSON Output** | No | ✅ Yes |
| **Dry Run** | No | ✅ Yes |
| **Validation** | Basic | ✅ Smart |
| **Code Quality** | Legacy | ✅ Modern |

## 🐛 Troubleshooting

### "open command not found"
**Solution:** You're not on macOS. NeoBear requires macOS and the Bear app.

### "Token required"
**Solution:** Some operations need authentication. Set up your token (see above).

### Spaces showing as `+`
**Solution:** You may be using an old tool. NeoBear uses correct encoding.

### Command not found
**Solution:** 
1. Check installation: `ls ~/.local/bin/neobear_cli.py`
2. Check PATH: `echo $PATH | grep .local/bin`
3. Add to PATH if missing (see Installation)

## 💡 Tips

1. **Use tags liberally** - Makes searching easier
2. **Pin important notes** - Keeps them at the top
3. **Use timestamps** - Tracks when notes were created/updated
4. **JSON output** - Great for scripting and automation
5. **Dry run** - Test before executing

## 📚 Bear URL Scheme

NeoBear uses Bear's x-callback-url API with proper encoding:

```
bear://x-callback-url/create?title=My%20Note&text=Content
```

**Key difference:** NeoBear uses `%20` for spaces, not `+`.

### Available Actions

- `create` - Create new note
- `open-note` - Open existing note
- `add-text` - Add content to note
- `search` - Search notes
- `trash` - Move note to trash
- `archive` - Archive note

## 🔗 Links

- **Bear App**: https://bear.app
- **Bear URL Scheme Docs**: https://bear.app/faq/X-callback-url%20Scheme%20documentation/
- **NeoBear GitHub**: (your repository)

## 📄 License

MIT License

## 🙏 Credits

- **Bear App Team** - For the amazing note-taking app
- **OpenClaw Community** - For feedback and testing
- **Original bear-notes skill** - For the foundation

---

**Version:** 2.0.0  
**Status:** Production Ready ✅  
**Platform:** macOS only  

**"Where old Bear links become new again."** 🐻💫

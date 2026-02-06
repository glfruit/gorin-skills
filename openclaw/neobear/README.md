# 🐻💫 NeoBear - OpenClaw Skill

**Next-gen Bear Notes integration for OpenClaw**

"Where old Bear links become new again."

---

## 🌟 What is NeoBear?

NeoBear is a modern Bear notes integration for OpenClaw that **solves the infamous space encoding bug**. Unlike older tools that convert spaces to `+` signs, NeoBear uses proper percent-encoding (`%20`) for perfect compatibility.

### The Problem

**Old tools:**
```
You create: "My Important Note"
Bear shows: "My+Important+Note"  ❌
```

**NeoBear:**
```
You create: "My Important Note"
Bear shows: "My Important Note"  ✅
```

---

## ✨ Features

### Perfect Encoding
- ✅ Uses `%20` for spaces (correct)
- ✅ Not `+` for spaces (broken)
- ✅ Full Unicode support
- ✅ Special characters handled properly

### Modern Design
- ✅ Python 3.7+ best practices
- ✅ Clean, maintainable code
- ✅ Comprehensive error handling
- ✅ Rich documentation

### Powerful CLI
- ✅ Create, search, open, manage notes
- ✅ JSON output for automation
- ✅ Dry-run mode for testing
- ✅ Batch operations support

### Smart Features
- ✅ Token management
- ✅ Tag support
- ✅ Timestamp tracking
- ✅ Pin/archive/trash operations

---

## 🚀 Quick Start

### 1. Install the Skill

```bash
# Copy to OpenClaw skills directory
mkdir -p ~/.openclaw/skills/neobear
cp SKILL.md neobear_cli.py ~/.openclaw/skills/neobear/

# Restart OpenClaw
openclaw restart
```

### 2. Setup Bear Token (Optional)

For operations requiring authentication:

```bash
# Get token from Bear: Help → API Token
mkdir -p ~/.config/bear
echo "YOUR_TOKEN_HERE" > ~/.config/bear/token
```

### 3. Use in OpenClaw

**Create a note:**
```
Create a Bear note titled "Shopping List" with content "Milk, Bread, Eggs"
```

**Search notes:**
```
Search Bear notes for "project"
```

**Open a note:**
```
Open the Bear note titled "Daily Journal"
```

---

## 📖 Usage Examples

### Create Notes

**Simple:**
```
Create Bear note "Meeting Notes" with "Discussed Q1 goals"
```

**With tags:**
```
Create Bear note:
- Title: "Project Ideas"
- Content: "New feature brainstorming"  
- Tags: work, projects, brainstorming
```

**From file:**
```
Create Bear note from ~/Documents/report.md titled "Monthly Report"
```

### Search & Find

**By keyword:**
```
Find Bear notes containing "deadline"
```

**By tag:**
```
Show all Bear notes tagged with "urgent"
```

**JSON output:**
```
Search Bear for "project" and output as JSON
```

### Manage Notes

**Append content:**
```
Add "Update: Completed phase 1" to Bear note "Project Status"
```

**Archive:**
```
Archive Bear note "Old Ideas"
```

**Delete:**
```
Trash Bear note "Temporary Notes"
```

---

## 🛠️ Command Line

### Create

```bash
# Basic
neobear_cli.py create --title "My Note" --text "Content"

# With options
neobear_cli.py create \
  --title "Important" \
  --text "Content" \
  --tags work,urgent \
  --pin \
  --timestamp
```

### Search

```bash
# By keyword
neobear_cli.py search --query "project"

# By tag
neobear_cli.py search --tag "work" --json

# Titles only
neobear_cli.py search --query "meeting" --titles-only
```

### Open

```bash
# By title
neobear_cli.py open --title "Daily Journal"

# By ID
neobear_cli.py open --id "NOTE-ID-HERE"

# With options
neobear_cli.py open --title "Note" --edit --new-window
```

---

## 🆚 vs Old Tools

| Feature | Old Bear Skill | **NeoBear** |
|---------|---------------|------------|
| Space Encoding | `+` ❌ | **`%20` ✅** |
| Unicode Support | Limited | **Full** ✅ |
| Error Messages | Generic | **Detailed** ✅ |
| JSON Output | No | **Yes** ✅ |
| Dry Run | No | **Yes** ✅ |
| Documentation | Basic | **Comprehensive** ✅ |
| Code Quality | Legacy | **Modern** ✅ |

---

## 💡 Why "Neo"?

**Neo** = New, representing a new generation:

- 🌟 **Not just fixed** - Completely reimagined
- 🌟 **Not just working** - Elegant and reliable  
- 🌟 **Not just updated** - Reborn from scratch

Like Neo from The Matrix, NeoBear sees through the bugs and makes everything work perfectly.

---

## 🐛 Troubleshooting

### Spaces still showing as `+`?

You're probably using the old skill. Check:

```bash
which bear_cli.py  # Should be neobear_cli.py
```

### Command not found?

Add `~/.local/bin` to PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Token errors?

Setup your Bear token:

```bash
# Get from Bear: Help → API Token
mkdir -p ~/.config/bear
echo "YOUR_TOKEN" > ~/.config/bear/token
```

---

## 📚 Documentation

- **SKILL.md** - Complete skill reference
- **Bear URL Scheme**: https://bear.app/faq/X-callback-url%20Scheme%20documentation/
- **Bear App**: https://bear.app

---

## 🔗 Integration

### Alfred Workflow

```bash
#!/bin/bash
# Create note from Alfred
neobear_cli.py create --title "$1" --text "$2" --tags inbox
```

### Keyboard Maestro

Use "Execute Shell Script" with:
```bash
neobear_cli.py create --title "Quick Note" --text "%ClipboardText%"
```

### Cron Job

```bash
# Daily journal entry
0 9 * * * neobear_cli.py create --title "Journal $(date +\%Y-\%m-\%d)" --tags journal
```

---

## 📄 License

MIT License

---

## 🙏 Credits

- **Bear App Team** - Amazing note-taking app
- **OpenClaw Community** - Testing and feedback
- **Original bear-notes skill** - Foundation

---

## 🎯 Status

- **Version**: 2.0.0
- **Status**: Production Ready ✅
- **Platform**: macOS only
- **Requirements**: Python 3.6+, Bear app

---

**"Where old Bear links become new again."** 🐻💫

Made with ❤️ for the Bear Notes community

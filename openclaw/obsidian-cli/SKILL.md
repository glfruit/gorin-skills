---
name: obsidian-cli
description: "Interact with Obsidian vaults via CLI to read, create, search, and manage notes, tasks, and properties."
triggers: ["obsidian cli", "obsidian search", "obsidian create", "obsidian note"]
user-invocable: true
agent-usable: true
---

# Obsidian CLI

There are two CLI tools for Obsidian. They serve different purposes:

| Feature | `obsidian` (Official) | `obsidian-cli` (Community) |
|---------|----------------------|---------------------------|
| **Author** | Obsidian team | yakitrak |
| **Requirement** | Obsidian app **running** | None (works standalone) |
| **Install** | Built into Obsidian | `brew install yakitrak/yakitrak/obsidian-cli` |
| **Create notes** | ✅ (`obsidian create`) | ✅ (`obsidian-cli create`) |
| **Search** | ✅ (`obsidian search`) | ✅ (`obsidian-cli search`, `search-content`) |
| **Move/rename** | ✅ (`obsidian move`) | ✅ (`obsidian-cli move`) |
| **Delete** | ✅ (`obsidian delete`) | ✅ (`obsidian-cli delete`) |
| **Plugin dev** | ✅ reload, eval, screenshots | ❌ |
| **Daily notes** | ✅ (`obsidian daily:read`) | ❌ |
| **Properties** | ✅ (`obsidian property:set`) | ❌ |
| **Wikilink refactor** | ❌ | ✅ updates `[[links]]` automatically |

**Recommendation**: Use the official `obsidian` CLI when Obsidian is running ( richer feature set, plugin dev, daily notes, properties). Use `obsidian-cli` when Obsidian is not running or when you need safe rename/move that auto-updates wikilinks.

---

## Official `obsidian` CLI

Use the `obsidian` CLI to interact with a running Obsidian instance. Requires Obsidian to be open.

### Command reference

Run `obsidian help` to see all available commands. This is always up to date. Full docs: https://help.obsidian.md/cli

### Syntax

**Parameters** take a value with `=`. Quote values with spaces:

```bash
obsidian create name="My Note" content="Hello world"
```

**Flags** are boolean switches with no value:

```bash
obsidian create name="My Note" silent overwrite
```

For multiline content use `\n` for newline and `\t` for tab.

### File targeting

Many commands accept `file` or `path` to target a file. Without either, the active file is used.

- `file=<name>` — resolves like a wikilink (name only, no path or extension needed)
- `path=<path>` — exact path from vault root, e.g. `folder/note.md`

### Vault targeting

Commands target the most recently focused vault by default. Use `vault=<name>` as the first parameter to target a specific vault:

```bash
obsidian vault="My Vault" search query="test"
```

### Common patterns

```bash
obsidian read file="My Note"
obsidian create name="New Note" content="# Hello" template="Template" silent
obsidian append file="My Note" content="New line"
obsidian search query="search term" limit=10
obsidian daily:read
obsidian daily:append content="- [ ] New task"
obsidian property:set name="status" value="done" file="My Note"
obsidian tasks daily todo
obsidian tags sort=count counts
obsidian backlinks file="My Note"
```

Use `--copy` on any command to copy output to clipboard. Use `silent` to prevent files from opening. Use `total` on list commands to get a count.

### Plugin development

#### Develop/test cycle

After making code changes to a plugin or theme, follow this workflow:

1. **Reload** the plugin to pick up changes:
   ```bash
   obsidian plugin:reload id=my-plugin
   ```
2. **Check for errors** — if errors appear, fix and repeat from step 1:
   ```bash
   obsidian dev:errors
   ```
3. **Verify visually** with a screenshot or DOM inspection:
   ```bash
   obsidian dev:screenshot path=screenshot.png
   obsidian dev:dom selector=".workspace-leaf" text
   ```
4. **Check console output** for warnings or unexpected logs:
   ```bash
   obsidian dev:console level=error
   ```

#### Additional developer commands

Run JavaScript in the app context:

```bash
obsidian eval code="app.vault.getFiles().length"
```

Inspect CSS values:

```bash
obsidian dev:css selector=".workspace-leaf" prop=background-color
```

Toggle mobile emulation:

```bash
obsidian dev:mobile on
```

Run `obsidian help` to see additional developer commands including CDP and debugger controls.

---

## Community `obsidian-cli`

Works without Obsidian running. Good for scripting and CI/CD workflows.

### Setup

```bash
# Install
brew install yakitrak/yakitrak/obsidian-cli

# Set default vault (once)
obsidian-cli set-default "<vault-folder-name>"
obsidian-cli print-default            # Show default vault info
obsidian-cli print-default --path-only  # Just the path
```

### Vault resolution

`obsidian-cli` reads vault config from `~/Library/Application Support/obsidian/obsidian.json`. The vault name is typically the **folder name** (path suffix).

To find the active vault programmatically:

```bash
# If default is set:
obsidian-cli print-default --path-only

# Otherwise, parse the config:
cat ~/Library/Application\ Support/obsidian/obsidian.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for v in data.get('vaults', {}):
    if data['vaults'][v].get('open'):
        print(v)
"
```

### Common commands

```bash
# Search
obsidian-cli search "query"              # By note name
obsidian-cli search-content "query"       # Inside notes (shows snippets + lines)

# Create
obsidian-cli create "Folder/New note" --content "..." --open

# Move/rename (safe refactor - updates wikilinks!)
obsidian-cli move "old/path/note" "new/path/note"

# Delete
obsidian-cli delete "path/note"
```

**Note**: `create --open` requires the Obsidian URI handler (`obsidian://...`) working (Obsidian installed). Avoid creating notes under hidden dot-folders via URI — Obsidian may refuse them.

---

## Finding the Vault (either CLI)

When you don't know which vault to target:

1. **Check Obsidian config** (source of truth):
   ```bash
   cat ~/Library/Application\ Support/obsidian/obsidian.json
   ```
2. **Common vault locations**:
   - `~/Documents/` or `~/Documents/Obsidian/`
   - iCloud Drive: `~/Library/Mobile Documents/`
   - `~/.obsidian/` (rare but possible)
3. **Multiple vaults**: The config file lists all vaults; look for `"open": true` to find the active one.

> **Tip**: Avoid hardcoding vault paths in scripts. Read the config or use `obsidian-cli print-default --path-only`.

## Gotchas

- **Official CLI needs Obsidian running**: If Obsidian isn't open, `obsidian` commands will fail. Use `obsidian-cli` for offline operations.
- **Vault name vs path**: `obsidian` uses the vault name from Obsidian's config, `obsidian-cli` uses the folder name. These are usually the same but not always.
- **Wikilink-safe rename**: Only `obsidian-cli move` auto-updates `[[wikilinks]]`. The official `obsidian` CLI does not have this feature (as of current version).
- **Create in hidden folders**: Both CLIs may refuse to create notes under dot-folders (`.something/`) via URI.
- **Content escaping**: Multiline content in the official CLI uses `\n` and `\t`. If your content contains literal backslashes, you'll need double-escaping.
- **search vs search-content**: `obsidian-cli search` matches note names only; `search-content` searches inside files but may be slow on large vaults.

## Security & Portability

- Both CLIs operate on local vault files only — no data leaves the machine.
- The official CLI communicates with a running Obsidian instance via local IPC; it does not expose any network interface.
- `obsidian-cli` directly reads/writes files on disk. Ensure proper file permissions on shared/multi-user systems.
- Vault paths in config may contain spaces or special characters — always quote paths in shell commands.
- The official CLI's `eval` command runs arbitrary JavaScript in the Obsidian app context; treat it with the same caution as browser DevTools console.

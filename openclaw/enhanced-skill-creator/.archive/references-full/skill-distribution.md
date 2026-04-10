# Skill Distribution Guide

How to share and distribute skills, from personal use to public publishing.

## Distribution Channels

| Channel | Best For | Setup Effort | Audience |
|---------|----------|-------------|----------|
| **gorin-skills repo** | Your self-created skills (canonical) | Low (one-time) | You |
| Workspace skills dir | Single-agent skills tied to a workspace | Zero | Single agent |
| ClawHub | Public skills, community sharing | Medium | All OpenClaw users |
| npm package | Skills with Node.js dependencies | Medium-High | Developers |

## gorin-skills Repo (Primary for Custom Skills)

Self-created skills live in the `gorin-skills` git repo and are symlinked into `~/.openclaw/skills/`.

### Architecture

```
GORIN_SKILLS_REPO (env var)
    ↓ git clone
~/.gorin-skills/skills/<name>/SKILL.md     ← git tracked (canonical source)
    ↓ symlink
~/.openclaw/skills/<name>/SKILL.md          ← OpenClaw loads from here
```

### Configuration

```bash
# Required env var (set in ~/.zshrc or openclaw config env)
export GORIN_SKILLS_REPO=git@github.com:glfruit/gorin-skills.git

# Optional: override local clone path
export GORIN_SKILLS_DIR=~/.gorin-skills
```

The repo URL is **never hardcoded** in any script or SKILL.md. Always read from `GORIN_SKILLS_REPO` env var.

### Sync Script

`scripts/skill-repo-sync.py` handles all repo operations:

| Command | Description |
|---------|-------------|
| `clone` | Clone repo to `~/.gorin-skills` |
| `pull` | Pull latest changes |
| `push [msg]` | Commit all changes and push |
| `link` | Create symlinks in `~/.openclaw/skills/` |
| `unlink` | Remove symlinks (keep repo files) |
| `status` | Show repo, symlink, and config status |
| `list` | List skills in repo |
| `add <name>` | Copy skill from `~/.openclaw/skills/` to repo |
| `remove <name>` | Remove skill from repo |

### Workflow

**New skill (after reaching `integrated` readiness):**
```bash
python3 scripts/skill-repo-sync.py add <name>
python3 scripts/skill-repo-sync.py push "add <name>: <description>"
# link is done automatically by add
```

**Update existing skill:**
```bash
# Edit in ~/.openclaw/skills/<name>/ as usual, then:
python3 scripts/skill-repo-sync.py push "update <name>: <brief change>"
```

**New machine setup:**
```bash
export GORIN_SKILLS_REPO=git@github.com:glfruit/gorin-skills.git
python3 scripts/skill-repo-sync.py clone
python3 scripts/skill-repo-sync.py link
```

### Coexistence with Other Sources

Multiple skill sources coexist in `~/.openclaw/skills/`:
- `gorin-skills` symlinks → your custom skills (version controlled)
- `clawbrain.git` clone → shared skill collection (already git tracked)
- Directories → agent-specific or experimental skills

The `link` command only creates symlinks for skills that don't already exist locally. It never overwrites.

## Workspace Skills Directory

- Skills specific to one workspace/agent and don't need sharing
- Path: `~/.openclaw/workspace-{name}/skills/`
- Best for: agent-specific skills, disposable skills, prototyping
- Note: These skills are scoped to one agent instance

## ClawHub

- The skill is useful for other OpenClaw users
- You want versioning, searchability, and update notifications
- Best for: general-purpose skills, domain tools, design patterns
- Setup: `clawhub publish <skill-dir>` (requires ClawHub CLI)
- Update: `clawhub sync` to update to latest

## npm Package

- The skill includes Node.js scripts or dependencies
- You want `npm install`-based distribution
- Best for: complex tool integrations, skills with build steps
- Note: Overkill for most skills; prefer ClawHub

## Distribution Checklist

Before publishing any skill:

- [ ] SKILL.md has valid frontmatter with `name` and `description`
- [ ] No hardcoded user paths (`/Users/...`, specific usernames)
- [ ] No hardcoded repo URLs — use `GORIN_SKILLS_REPO` env var
- [ ] No secrets, API keys, or personal data
- [ ] Triggers are generic enough for other users (for ClawHub)
- [ ] Data persistence uses configurable paths, not fixed paths
- [ ] README is NOT needed (SKILL.md is the entry point)
- [ ] All scripts use Python (preferred) or bash (document alternatives)

## Versioning

Skills don't need formal semver for personal use. For published skills:

- Use git log for history (gorin-skills repo)
- Use git tags for stable releases
- ClawHub handles versioning automatically on publish
- Include an Updates section in SKILL.md for changelog-style notes (not a separate CHANGELOG.md)

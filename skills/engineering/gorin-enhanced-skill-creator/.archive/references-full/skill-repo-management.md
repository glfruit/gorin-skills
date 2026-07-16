# Skill Repo Management Reference

Self-created skills are version-controlled in the **gorin-skills** git repo, synced to OpenClaw via symlinks.

## Setup (One-Time)

```bash
# 1. Set repo URL (add to ~/.zshrc or openclaw config env)
export GORIN_SKILLS_REPO=git@github.com:glfruit/gorin-skills.git

# 2. Clone and link
python3 scripts/skill-repo-sync.py clone
python3 scripts/skill-repo-sync.py link

# 3. Verify
python3 scripts/skill-repo-sync.py status
```

The `GORIN_SKILLS_REPO` env var is **required** — never hardcode the URL in any script or SKILL.md. Default local clone path is `~/.gorin-skills` (override with `GORIN_SKILLS_DIR`).

## How It Works

```
~/.gorin-skills/skills/my-skill/   ← canonical source (git tracked)
        ↓ symlink
~/.openclaw/skills/my-skill/      ← OpenClaw loads from here
```

- `link` creates individual symlinks (not directory-level) so coexistence with other skill sources works
- `unlink` removes symlinks without touching repo files
- OpenClaw's `skills.load.extraDirs` is automatically updated to include the repo path

## Daily Workflow

**After creating a new skill** (reaches `integrated` readiness):
```bash
python3 scripts/skill-repo-sync.py add <skill-name>
python3 scripts/skill-repo-sync.py tag <skill-name> self  # 标记为自创建
python3 scripts/skill-repo-sync.py push "add <skill-name> skill"
python3 scripts/skill-repo-sync.py link
```

**After editing an existing skill**:
```bash
python3 scripts/skill-repo-sync.py push "update <skill-name>: <brief change>"
```

**Update third-party skills** (ClawHub):
```bash
python3 scripts/skill-repo-sync.py update --all    # 更新所有第三方
python3 scripts/skill-repo-sync.py update docx pdf  # 更新指定技能
```

**After pulling on another machine**:
```bash
python3 scripts/skill-repo-sync.py pull
python3 scripts/skill-repo-sync.py link
```

**Check status**:
```bash
python3 scripts/skill-repo-sync.py status    # repo + symlink + config status
python3 scripts/skill-repo-sync.py list      # 列出所有技能
python3 scripts/skill-repo-sync.py list --origin  # 按来源分类
```

**Tag skill origin** (override auto-detection):
```bash
python3 scripts/skill-repo-sync.py tag <name> self          # 自创建
python3 scripts/skill-repo-sync.py tag <name> third-party   # 第三方(如 baoyu-*)
python3 scripts/skill-repo-sync.py tag <name> clawhub       # 从 ClawHub 安装
```

## When Creating Skills

In Step 5 (Generate the Skill), after validation passes:
1. Create the skill in `~/.openclaw/skills/<name>/` as normal
2. Run `python3 scripts/skill-repo-sync.py add <name>` to copy to repo
3. The symlink is created automatically by `add`
4. On `push`, changes in the repo are committed

## Integration with Step 8

When a skill reaches `integrated` readiness and the user confirms acceptance, offer to:
1. `add` the skill to the repo
2. `tag` the skill origin (`self` for user-created, `third-party` for installed)
3. `push` with a descriptive commit message
4. Verify the symlink is active

Do NOT auto-push without user confirmation.

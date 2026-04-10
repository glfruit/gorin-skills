---
name: plugin-updater
description: "Safely check for and install OpenClaw plugin updates. Handles config backup/restore, local patch preservation, verification, and gateway restart. Use when an agent or user wants to update an OpenClaw plugin (lossless-claw, nowledge-mem, etc)."
triggers: ["update plugin", "upgrade plugin", "check plugin update", "plugin update", "插件更新", "插件升级", "check for updates"]
user-invocable: true
agent-usable: true
---

# Plugin Updater

> Safely update OpenClaw plugins. **Never manually replace plugin directories.**

## Core Principles

1. **Always use `openclaw plugins update <id>` for existing plugins** — `install` is for first-time only
2. **Backup before, verify after** — config entries, local patches, gateway health
3. **One plugin at a time** — sequential, with rollback on failure
4. **Check changelog first** — understand what changed before installing
5. **Restart gateway once** — batch if multiple, but verify between installs

## When to Use

- User asks to update a plugin
- Heartbeat or agent notices a plugin has a new version available
- Post-incident: plugin fix available upstream

## When NOT to Use

- OpenClaw core update → use `openclaw update` / auto-updater launchd
- Skill install/update → use `clawhub install/update`
- npm package unrelated to OpenClaw

## Risk Levels

| Risk | Default Behavior | Examples |
|------|-----------------|---------|
| **critical** | Report only, never auto-update | openclaw-runtime-guards |
| **high** | Update with full verification | lossless-claw, nowledge-mem, agent-knowledge |
| **normal** | Update with basic checks | Most plugins |
| **low** | Update freely | New/untested plugins |

Risk config: `~/.openclaw/config/plugin-updater.json` → `risk.byPlugin`

## Workflow

### Step 1: Check Current State

```bash
# Installed plugins with versions
cat ~/.openclaw/openclaw.json | python3 -c "
import sys, json
cfg = json.load(sys.stdin)
for pid, meta in cfg.get('plugins',{}).get('installs',{}).items():
    if meta.get('source') == 'npm':
        print(f'{pid}: {meta.get(\"resolvedVersion\",\"?\")}')"

# Latest versions on npm
npm view @martian-engineering/lossless-claw version
npm view openclaw-nowledge-mem version
# etc.
```

### Step 2: Review Changelog (REQUIRED before update)

```bash
# GitHub releases
curl -sL "https://api.github.com/repos/Martian-Engineering/lossless-claw/releases/latest" | python3 -c "
import sys, json; d = json.load(sys.stdin)
print(d.get('tag_name','?'))
print(d.get('body','')[:2000])"
```

Or check CHANGELOG.md in installed plugin directory:
```bash
head -80 ~/.openclaw/extensions/{plugin-id}/CHANGELOG.md
```

Report to user: **version delta + key fixes + any breaking changes**.

### Step 3: Check Risk & Policy

Read `~/.openclaw/config/plugin-updater.json`. If plugin is `critical`, ask user for explicit approval before proceeding.

### Step 4: Update the Plugin

```bash
# Update a specific plugin (reuses recorded install spec from plugins.installs)
openclaw plugins update {plugin-id}
# e.g.: openclaw plugins update lossless-claw

# Update all tracked plugins
openclaw plugins update --all

# Dry run first (recommended)
openclaw plugins update {plugin-id} --dry-run

# Update to a specific version
openclaw plugins update {plugin-id}@{version}
# e.g.: openclaw plugins update @openclaw/voice-call@beta
```

`update` reuses the recorded install spec from `plugins.installs`. Do NOT use `install` for existing plugins — that's for first-time installation.

**Do NOT:**
- Manually replace `~/.openclaw/extensions/{plugin-id}/`
- Use `npm pack` + `tar xzf` + `mv` (breaks plugin manifest registration)
- `rm -rf` any extension directory
- Use `openclaw plugins install` to update an already-installed plugin → WRONG, use `update`

### Step 5: Verify Installation

```bash
# Check plugin loaded
openclaw doctor 2>&1 | grep -i "{plugin-id}"

# Verify version
cat ~/.openclaw/extensions/{plugin-id}/package.json | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])"

# Check for local patches that may have been overwritten
find ~/.openclaw/extensions/{plugin-id}/ -name "*.patched-backup-*"
```

### Step 6: Restore Custom Config

If plugin has custom config in `openclaw.json` → `plugins.entries.{plugin-id}.config`, verify it survived the update. The `openclaw plugins update` command may reset config entries — check and restore if needed.

```bash
python3 -c "
import json
with open('$HOME/.openclaw/openclaw.json') as f:
    cfg = json.load(f)
entries = cfg.get('plugins',{}).get('entries',{})
pid = '{plugin-id}'
if pid in entries:
    print(json.dumps(entries[pid].get('config',{}), indent=2))
else:
    print('WARNING: no config entry for', pid)"
```

### Step 7: Restore Local Patches

Check if plugin had local patches (from `LOCAL_PATCHES.md` or `.patched-backup-*` files). If the install overwrote patched source files, re-apply or flag for review.

### Step 8: Restart Gateway

```bash
openclaw gateway restart
```

Wait ~10s, then verify:
```bash
# Check gateway logs for plugin errors
tail -30 ~/.openclaw/logs/gateway.err.log | grep -i "error\|fail\|{plugin-id}"
```

### Step 9: Post-Update Health Check

```bash
openclaw plugins doctor 2>&1 | tail -20
```

If anything failed: roll back using the previous version spec.

## Automated Updater (launchd)

The launchd service `ai.openclaw.plugin-updater` runs `~/.openclaw/scripts/plugin_updater.py` automatically. It handles:
- Maintenance window (04:00–06:00 CST by default)
- Risk-based allow/deny
- Config backup/restore
- Changelog extraction + Telegram notification
- Rollback on failure

Manual skill usage should follow the same safety principles but with interactive decision-making.

## Gotchas

1. **ClawHub 429 rate limit** — `openclaw plugins update` may fail with "Rate limit exceeded". Wait 60s and retry.
2. **Config wipe on update** — `openclaw plugins update` may reset `plugins.entries.{id}.config` to defaults. Always check post-update.
3. **No dist/ in source-only plugins** — Some plugins (lossless-claw) ship source only, no compiled dist/. The framework compiles at runtime. Local TS edits need tsc to take effect.
4. **Lock conflict with auto-updater** — If launchd auto-updater is running, wait for it to finish. Check `/tmp/openclaw-plugin-updater-running`.
5. **Gateway restart-defer loop** — Multiple rapid config changes can trigger exponential backoff. Change all config at once, restart once.
6. **Nowledge-mem ETIMEDOUT patch** — If updating nowledge-mem, the ETIMEDOUT fix in `src/client.js` must be re-applied. Backup at `/tmp/openclaw-nowledge-mem-0.7.1-patched-backup`.

## Error Handling

| Symptom | Cause | Fix |
|---------|-------|-----|
| "plugin already exists" | Old extension dir not cleaned | Use `openclaw plugins update <id>` instead of `install` |
| Gateway crash-loop after update | Config incompatibility | Check `gateway.err.log`, restore config backup, rollback plugin |
| Plugin not loaded after install | Missing from `plugins.allow` | Add plugin short name to `plugins.allow` in openclaw.json |
| Config reset to defaults | install command overwrites entries | Restore from backup or re-apply config |
| Changelog extraction empty | No CHANGELOG.md or version mismatch | Check GitHub releases API instead |

## Internal Acceptance
- **Happy-path**: Update lossless-claw 0.5.3 → 0.6.0
  - Step 1-2: npm check + GitHub changelog reviewed
  - Step 3: risk=high, policy allows auto-update
  - Step 4: `openclaw plugins update lossless-claw`
  - Step 5-7: version verified, config intact, no patches lost
  - Step 8-9: gateway restarted, plugins doctor passes
- **Failure mode**: ClawHub 429 → wait 60s → retry
- **Failure mode**: Config wiped → restore from backup before Step 4

## Readiness
**MVP** — core workflow proven. Trigger eval pending.

## Delivery Contract

Report "plugin update complete" only when:
- [x] Version verified matches target
- [x] Plugin loaded (no errors in gateway log)
- [x] Custom config preserved or restored
- [x] Local patches checked/re-applied
- [x] `openclaw plugins doctor` passes for this plugin

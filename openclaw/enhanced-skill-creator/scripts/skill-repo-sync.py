#!/usr/bin/env python3
"""skill-repo-sync.py — Sync skills between local dirs and the gorin-skills git repo.

环境变量:
  GORIN_SKILLS_REPO — 仓库地址 (e.g. git@github.com:glfruit/gorin-skills.git)
  GORIN_SKILLS_DIR  — 本地克隆路径 (默认: ~/.gorin-skills)
  GORIN_SKILLS_SUBDIR — 仓库内子目录 (默认: 自动检测 openclaw/ 或 skills/)

用法:
  python3 skill-repo-sync.py clone            # 首次克隆
  python3 skill-repo-sync.py pull             # 拉取最新
  python3 skill-repo-sync.py push [msg]       # 提交并推送
  python3 skill-repo-sync.py link             # 创建 symlink 到 OpenClaw
  python3 skill-repo-sync.py unlink           # 移除 symlink
  python3 skill-repo-sync.py status           # 查看状态
  python3 skill-repo-sync.py list             # 列出仓库中的技能
  python3 skill-repo-sync.py list --origin    # 按来源分类列出
  python3 skill-repo-sync.py add <name>       # 添加技能到仓库
  python3 skill-repo-sync.py remove <name>    # 从仓库移除技能
  python3 skill-repo-sync.py migrate --all    # 批量迁移
  python3 skill-repo-sync.py tag <name> <origin>  # 标记技能来源 (self/third-party/clawhub)
  python3 skill-repo-sync.py update [--all | <name>]  # 更新第三方技能
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HOME = Path.home()

# ── 配置 ────────────────────────────────────────────
REPO_URL = os.environ.get("GORIN_SKILLS_REPO", "")
REPO_DIR = Path(os.environ.get("GORIN_SKILLS_DIR", str(HOME / ".gorin-skills")))

# Subdirectory within the repo that contains OpenClaw skills
# Auto-detects: looks for openclaw/ first, then skills/, then root
REPO_SKILLS_SUBDIR = os.environ.get("GORIN_SKILLS_SUBDIR", "")  # empty = auto-detect

# OpenClaw skill directories (where skills are loaded from)
OC_SKILLS_DIR = HOME / ".openclaw" / "skills"
OC_WORKSPACE_SKILLS = HOME / ".openclaw" / "workspace" / "skills"


def _run(cmd: list[str], cwd: Path | None = None, check: bool = False) -> subprocess.CompletedProcess:
    effective_cwd = cwd if cwd is not None else (REPO_DIR if REPO_DIR.exists() else HOME)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=effective_cwd, check=check)


def _get_repo_skills_dir() -> Path:
    """Auto-detect the skills subdirectory within the repo."""
    if not REPO_DIR.exists():
        return REPO_DIR / "openclaw"  # default guess

    # If explicitly set via env var
    if REPO_SKILLS_SUBDIR:
        return REPO_DIR / REPO_SKILLS_SUBDIR

    # Auto-detect: prefer openclaw/, then skills/, then root
    for candidate in ("openclaw", "skills"):
        d = REPO_DIR / candidate
        if d.exists() and d.is_dir():
            # Verify it has at least one SKILL.md
            for child in d.iterdir():
                if child.is_dir() and (child / "SKILL.md").exists():
                    return d

    return REPO_DIR  # root fallback


# ── 来源管理 ─────────────────────────────────────────

# Known third-party skill patterns
_THIRD_PARTY_PREFIXES = ("baoyu-",)
_THIRD_PARTY_NAMES = {
    "bearclaw-native", "neobear", "log-watchdog",
    "visual-knowledge-explainer",
}
_CLAWHUB_NAMES = {
    "docx", "pdf", "pptx", "xlsx",
    "download-anything", "code-review",
    "web-reader", "web-content-fetcher",
    "openmaic", "obsidian-ontology-sync",
    "safe-mode",
}

ORIGINS_FILE = REPO_DIR / ".skill-origins.json"


def _load_origins() -> dict:
    if ORIGINS_FILE.exists():
        try:
            return json.loads(ORIGINS_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_origins(origins: dict) -> None:
    ORIGINS_FILE.write_text(json.dumps(origins, indent=2, ensure_ascii=False))


def _detect_origin(name: str) -> str:
    """Auto-detect skill origin based on naming patterns."""
    # First check for .skill-meta.json inside the skill dir
    repo_skills = _get_repo_skills_dir()
    meta_file = repo_skills / name / ".skill-meta.json"
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
            origin = meta.get("origin")
            if origin in ("self", "third-party", "clawhub"):
                return origin
        except Exception:
            pass

    # Fallback: pattern-based detection
    for prefix in _THIRD_PARTY_PREFIXES:
        if name.startswith(prefix):
            return "third-party"
    if name in _THIRD_PARTY_NAMES:
        return "third-party"
    if name in _CLAWHUB_NAMES:
        return "clawhub"
    return "self"


def _get_origin(name: str) -> str:
    """Get origin priority: .skill-meta.json > .skill-origins.json > auto-detect."""
    # Check .skill-meta.json first (canonical, travels with the skill)
    repo_skills = _get_repo_skills_dir()
    meta_file = repo_skills / name / ".skill-meta.json"
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
            origin = meta.get("origin")
            if origin in ("self", "third-party", "clawhub"):
                return origin
        except Exception:
            pass

    # Then check .skill-origins.json (local override)
    origins = _load_origins()
    if name in origins:
        return origins[name]

    # Finally auto-detect
    return _detect_origin(name)


def _origin_icon(origin: str) -> str:
    return {"self": "✨", "third-party": "📦", "clawhub": "🔌"}.get(origin, "❓")


def cmd_tag(name: str, origin: str) -> int:
    """Tag a skill's origin. Writes to both .skill-meta.json (travels with skill) and .skill-origins.json (local)."""
    valid = ("self", "third-party", "clawhub")
    if origin not in valid:
        print(f"❌ 无效来源: {origin}（可选: {', '.join(valid)}）")
        return 1

    # 1. Write .skill-meta.json in the skill dir (canonical, travels with git)
    repo_skills = _get_repo_skills_dir()
    meta_file = repo_skills / name / ".skill-meta.json"
    if not meta_file.parent.exists():
        print(f"❌ 技能 {name} 不在仓库中")
        return 1

    meta = {}
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
        except Exception:
            pass

    meta["origin"] = origin
    if origin == "self" and "author" not in meta:
        meta["author"] = "gorin"
    meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    # 2. Also update .skill-origins.json (local backup)
    origins = _load_origins()
    origins[name] = origin
    _save_origins(origins)

    print(f"✅ {name} → {origin}")
    print(f"   .skill-meta.json 已更新 (跟随技能，会进 git)")
    return 0


def cmd_update(*names: str) -> int:
    """Update third-party/clawhub skills from their upstream source.

    Currently supports ClawHub skills. Usage:
      update --all          # update all clawhub/third-party skills
      update docx pdf xlsx  # update specific skills
    """
    if not REPO_DIR.exists():
        print("❌ 仓库未克隆")
        return 1

    repo_skills = _get_repo_skills_dir()
    origins = _load_origins()

    # Determine targets
    if names and names[0] == "--all":
        targets = [d.name for d in sorted(repo_skills.iterdir())
                   if d.is_dir() and (d / "SKILL.md").exists()
                   and _get_origin(d.name) != "self"]
    elif names:
        targets = list(names)
    else:
        print("用法: update [--all | name1 name2 ...]")
        return 0

    if not targets:
        print("✅ 没有需要更新的第三方技能")
        return 0

    print(f"🔄 检查 {len(targets)} 个第三方技能的更新...")
    print("")

    updated = 0
    for name in targets:
        origin = _get_origin(name)
        icon = _origin_icon(origin)

        if origin == "clawhub":
            # Try clawhub update
            r = subprocess.run(
                ["clawhub", "update", name],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0 and "already up to date" not in r.stdout.lower():
                print(f"  {icon} {name}: 已更新")
                updated += 1
            elif "already up to date" in r.stdout.lower():
                print(f"  {icon} {name}: 已是最新")
            else:
                print(f"  {icon} {name}: ⚠️ {r.stderr.strip()[:60] or r.stdout.strip()[:60]}")
        else:
            print(f"  {icon} {name}: 非 ClawHub 来源，需手动更新")

    print(f"\n✅ 更新了 {updated} 个技能")
    return 0


def _ensure_repo() -> bool:
    if not REPO_URL:
        print("❌ GORIN_SKILLS_REPO 环境变量未设置")
        print("   export GORIN_SKILLS_REPO=git@github.com:glfruit/gorin-skills.git")
        return False
    return True


def cmd_clone() -> int:
    if not _ensure_repo():
        return 1
    if REPO_DIR.exists():
        print(f"⚠️  仓库已存在于 {REPO_DIR}")
        print("   使用 pull 更新")
        return 1
    REPO_DIR.parent.mkdir(parents=True, exist_ok=True)
    print(f"📦 克隆 {REPO_URL} → {REPO_DIR}")
    r = _run(["git", "clone", REPO_URL, str(REPO_DIR)], cwd=HOME)
    if r.returncode != 0:
        print(f"❌ 克隆失败: {r.stderr}")
        return 1
    print(f"✅ 克隆成功")
    return 0


def cmd_pull() -> int:
    if not REPO_DIR.exists():
        print("❌ 仓库未克隆，请先运行 clone")
        return 1
    print("📥 拉取最新...")
    r = _run(["git", "pull", "--rebase"])
    if r.returncode != 0:
        print(f"❌ 拉取失败: {r.stderr}")
        return 1
    print(f"✅ 已更新到最新")
    return 0


def cmd_push(msg: str | None = None) -> int:
    if not REPO_DIR.exists():
        print("❌ 仓库未克隆")
        return 1
    if not msg:
        msg = f"skill update {subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO_DIR, text=True).strip()}"
    print("📤 提交并推送...")
    _run(["git", "add", "-A"])
    r = _run(["git", "diff", "--cached", "--quiet"])
    if r.returncode == 0:
        print("ℹ️  没有变更需要提交")
        return 0
    _run(["git", "commit", "-m", msg], check=True)
    r = _run(["git", "push"])
    if r.returncode != 0:
        print(f"❌ 推送失败: {r.stderr}")
        return 1
    print(f"✅ 已推送")
    return 0


def cmd_link() -> int:
    """将 repo 中的技能 symlink 到 OpenClaw 的技能加载目录。"""
    if not REPO_DIR.exists():
        print("❌ 仓库未克隆")
        return 1

    skills_src = _get_repo_skills_dir()
    if not skills_src.exists():
        print(f"⚠️  仓库中未找到 skills/ 目录，创建中...")
        skills_src.mkdir(parents=True, exist_ok=True)

    OC_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    # We DON'T symlink the entire directory — instead symlink individual skill folders
    # This allows coexistence with skills from other sources (clawbrain.git, workspace/skills)
    linked = 0
    skipped = 0
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        target = OC_SKILLS_DIR / skill_dir.name
        if target.exists():
            if target.resolve() == skill_dir:
                skipped += 1
                continue
            # Target exists but isn't our symlink — don't overwrite
            print(f"⚠️  {skill_dir.name} 已存在于 {OC_SKILLS_DIR}（非 repo symlink，跳过）")
            skipped += 1
            continue
        target.symlink_to(skill_dir)
        linked += 1
        print(f"🔗 {skill_dir.name} → {skill_dir}")

    # Also ensure extraDirs includes the repo skills path for direct loading
    print(f"\n✅ linked={linked}, skipped={skipped}")

    # Verify OpenClaw config has the right extraDirs
    _verify_extradir()
    return 0


def _verify_extradir() -> None:
    """Check that OpenClaw config loads from the repo's skills/ dir."""
    import json
    config_path = HOME / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return
    config = json.loads(config_path.read_text())
    extra = config.get("skills", {}).get("load", {}).get("extraDirs", [])
    repo_skills = str(_get_repo_skills_dir())
    if repo_skills not in extra:
        extra.append(repo_skills)
        config["skills"]["load"]["extraDirs"] = extra
        config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))
        print(f"📝 已添加 {repo_skills} 到 openclaw.json extraDirs")


def cmd_unlink() -> int:
    """移除 repo 技能的 symlink（不删除仓库文件）。"""
    if not REPO_DIR.exists():
        print("❌ 仓库未克隆")
        return 1
    removed = 0
    for skill_dir in sorted((_get_repo_skills_dir()).iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        target = OC_SKILLS_DIR / skill_dir.name
        if target.exists() and target.is_symlink() and target.resolve() == skill_dir:
            target.unlink()
            removed += 1
            print(f"🗑️  {skill_dir.name}")
    print(f"\n✅ 移除了 {removed} 个 symlink")
    return 0


def cmd_status() -> int:
    print("=== gorin-skills 状态 ===")
    print(f"环境变量 GORIN_SKILLS_REPO: {'✅ ' + REPO_URL if REPO_URL else '❌ 未设置'}")
    print(f"本地路径: {REPO_DIR}")
    print(f"仓库存在: {'✅' if REPO_DIR.exists() else '❌'}")

    if REPO_DIR.exists():
        r = _run(["git", "status", "--short"])
        changed = r.stdout.strip().splitlines() if r.stdout.strip() else []
        print(f"未提交变更: {len(changed)} 个文件")
        if changed:
            for line in changed[:10]:
                print(f"  {line}")
            if len(changed) > 10:
                print(f"  ... 还有 {len(changed) - 10} 个")

        r = _run(["git", "log", "--oneline", "-3"])
        print(f"最近提交:")
        print(f"  {r.stdout.strip().replace(chr(10), chr(10) + '  ')}")

    # Check symlinks
    linked = 0
    if OC_SKILLS_DIR.exists():
        for d in OC_SKILLS_DIR.iterdir():
            if d.is_symlink() and str(d.resolve()).startswith(str(REPO_DIR)):
                linked += 1
    print(f"已链接技能: {linked}")

    # Check extraDirs
    import json
    config_path = HOME / ".openclaw" / "openclaw.json"
    if config_path.exists():
        config = json.loads(config_path.read_text())
        extra = config.get("skills", {}).get("load", {}).get("extraDirs", [])
        repo_skills = str(_get_repo_skills_dir())
        in_config = repo_skills in extra
        print(f"extraDirs 注册: {'✅' if in_config else '❌ 未注册'}")
    return 0


def cmd_list(show_origin: bool = False) -> int:
    if not REPO_DIR.exists():
        print("❌ 仓库未克隆")
        return 1
    repo_skills = _get_repo_skills_dir()
    if not repo_skills.exists():
        print("ℹ️  仓库中暂无技能")
        return 0

    skills = []
    for d in sorted(repo_skills.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        has_skill = (d / "SKILL.md").exists()
        is_linked = (OC_SKILLS_DIR / d.name).is_symlink()
        origin = _get_origin(d.name)
        skills.append((d.name, has_skill, is_linked, origin))

    if show_origin:
        # Group by origin
        groups: dict[str, list] = {}
        for name, has_skill, is_linked, origin in skills:
            groups.setdefault(origin, []).append((name, has_skill, is_linked))

        labels = {"self": "✨ 自创建", "third-party": "📦 第三方", "clawhub": "🔌 ClawHub"}
        for origin in ("self", "clawhub", "third-party"):
            items = groups.get(origin, [])
            if not items:
                continue
            print(f"{labels.get(origin, origin)} ({len(items)} 个)")
            for name, has_skill, is_linked in items:
                link = "🔗" if is_linked else "  "
                warn = "" if has_skill else " ⚠️"
                print(f"  {link} {name}{warn}")
            print("")
    else:
        print(f"=== 仓库中的技能 ({repo_skills}) ===")
        for name, has_skill, is_linked, origin in skills:
            link = "🔗" if is_linked else "  "
            warn = "" if has_skill else " ⚠️ 无 SKILL.md"
            o = _origin_icon(origin)
            print(f"  {link} {name} [{o} {origin}]{warn}")
    return 0


def cmd_add(name: str, origin: str = "self") -> int:
    """Add skill to repo. Copies from OC skills dir, creates .skill-meta.json.
    
    Usage: add <name> [origin]   origin: self (default), third-party, clawhub
    """
    if not REPO_DIR.exists():
        print("❌ 仓库未克隆")
        return 1

    skills_src = _get_repo_skills_dir()
    skills_src.mkdir(parents=True, exist_ok=True)
    target = skills_src / name

    source = OC_SKILLS_DIR / name
    if source.exists():
        if target.exists():
            print(f"⚠️  仓库中已有 {name}")
            return 1
        import shutil
        shutil.copytree(source, target)
        print(f"✅ 已从 {source} 复制到 {target}")

        # Create .skill-meta.json
        meta_file = target / ".skill-meta.json"
        if not meta_file.exists():
            meta = {"origin": origin, "author": "gorin" if origin == "self" else "external"}
            # Extract name/description from SKILL.md frontmatter
            skill_md = target / "SKILL.md"
            if skill_md.exists():
                text = skill_md.read_text()
                if text.startswith("---"):
                    try:
                        end = text.index("---", 3)
                        for line in text[3:end].splitlines():
                            if ":" not in line:
                                continue
                            key, val = line.split(":", 1)
                            key = key.strip()
                            val = val.strip().strip("\"'")
                            if key == "name":
                                meta["name"] = val
                            elif key == "description":
                                meta["description"] = val
                    except ValueError:
                        pass
            meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
            print(f"   📝 .skill-meta.json ({origin})")
    else:
        print(f"⚠️  {name} 不在 {OC_SKILLS_DIR} 中")
        return 1
    return 0


def cmd_migrate(*names: str) -> int:
    """Bulk migrate skills: copy to repo, replace local with symlink.
    
    Usage: migrate [name1 name2 ...]   — specific skills
           migrate --all               — all non-symlink skills in OC dir
    """
    if not REPO_DIR.exists():
        print("❌ 仓库未克隆")
        return 1

    repo_skills = _get_repo_skills_dir()

    # Determine which skills to migrate
    if names and names[0] == "--all":
        targets = []
        for d in sorted(OC_SKILLS_DIR.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            if d.is_symlink():
                # Already a symlink — skip (or re-link if target differs)
                if d.resolve().is_relative_to(REPO_DIR):
                    continue  # already points to our repo
                # Points elsewhere (clawbrain etc.) — re-link
                targets.append(d.name)
                continue
            if not (d / "SKILL.md").exists():
                continue
            targets.append(d.name)
    elif names:
        targets = list(names)
    else:
        print("用法: migrate [--all | name1 name2 ...]")
        return 1

    if not targets:
        print("✅ 没有需要迁移的技能")
        return 0

    print(f"📦 准备迁移 {len(targets)} 个技能到 {repo_skills}")
    print("")

    migrated = 0
    skipped = 0
    for name in targets:
        source = OC_SKILLS_DIR / name
        target = repo_skills / name

        if not source.exists():
            print(f"  ⚠️  {name}: 源目录不存在")
            skipped += 1
            continue

        if not (source / "SKILL.md").exists():
            print(f"  ⚠️  {name}: 无 SKILL.md，跳过")
            skipped += 1
            continue

        if source.is_symlink():
            # Re-link: remove old symlink, create new one
            if source.resolve() == target:
                print(f"  ⏭️  {name}: 已是指向 repo 的 symlink")
                skipped += 1
                continue
            source.unlink()
            target.mkdir(parents=True, exist_ok=True)
            source.symlink_to(target)
            print(f"  🔄 {name}: 重新链接 → repo")
            migrated += 1
            continue

        # Copy to repo
        import shutil
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)

        # Replace local with symlink
        shutil.rmtree(source)
        source.symlink_to(target)
        print(f"  ✅ {name}: 复制 → repo, 本地替换为 symlink")
        migrated += 1

    print(f"\n✅ 迁移完成: {migrated} 成功, {skipped} 跳过")
    print(f"下一步: python3 skill-repo-sync.py push \"migrate {migrated} skills to gorin-skills\"")
    return 0


def cmd_remove(name: str) -> int:
    """从仓库移除技能（不删除本地 symlink）。"""
    if not REPO_DIR.exists():
        print("❌ 仓库未克隆")
        return 1
    target = _get_repo_skills_dir() / name
    if not target.exists():
        print(f"❌ 仓库中无 {name}")
        return 1
    import shutil
    shutil.rmtree(target)
    print(f"✅ 已从仓库移除 {name}")
    # Note: symlink in OC_SKILLS_DIR will become dangling — user should unlink or replace
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 0

    cmd = sys.argv[1]
    show_origin = "--origin" in sys.argv
    cmds = {
        "clone": lambda: cmd_clone(),
        "pull": lambda: cmd_pull(),
        "push": lambda: cmd_push(sys.argv[2] if len(sys.argv) > 2 else None),
        "link": lambda: cmd_link(),
        "unlink": lambda: cmd_unlink(),
        "status": lambda: cmd_status(),
        "list": lambda: cmd_list(show_origin=show_origin),
        "add": lambda: cmd_add(
            sys.argv[2],
            sys.argv[3] if len(sys.argv) > 3 else "self"
        ) if len(sys.argv) > 2 else (print("用法: add <skill-name> [self|third-party|clawhub]"), 1),
        "migrate": lambda: cmd_migrate(*sys.argv[2:]) if len(sys.argv) > 2 else (
            print("用法: migrate [--all | skill1 skill2 ...]") or 1
        ),
        "remove": lambda: cmd_remove(sys.argv[2]) if len(sys.argv) > 2 else (print("用法: remove <skill-name>"), 1),
        "tag": lambda: cmd_tag(sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else (
            print("用法: tag <skill-name> self|third-party|clawhub"), 1
        ),
        "update": lambda: cmd_update(*sys.argv[2:]) if len(sys.argv) > 2 else (
            print("用法: update [--all | skill1 skill2 ...]"), 1
        ),
    }

    fn = cmds.get(cmd)
    if fn:
        return fn()
    print(f"❌ 未知命令: {cmd}")
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

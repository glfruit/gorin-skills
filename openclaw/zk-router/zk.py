#!/usr/bin/env python3
"""ZK Router - Python implementation (python-first policy)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT = sys.argv[1] if len(sys.argv) > 1 else ""
SOURCE_CONTEXT = sys.argv[2] if len(sys.argv) > 2 else "user"
FORCE_MODE = os.environ.get("ZK_FORCE", "0") == "1"

VAULT_CONFIG_PATH = Path.home() / ".gorin-skills/openclaw/pkm-core/vault-config.yaml"

DEFAULT_CONFIG = {
    "vault": str(Path.home() / "Workspace/PKM/octopus"),
    "default_vault": "octopus",
    "web_reader_candidates": [
        str(Path.home() / ".gorin-skills/openclaw/web-reader/scripts/web-reader.sh"),
        str(Path.home() / ".openclaw/skills/web-reader/scripts/web-reader.sh"),
    ],
    "dedup_policy_path": str(Path.home() / ".openclaw/workspace-daily-tl/scripts/pkm_dedup_policy.json"),
    "dedup_behavior_for_intentional": "skip",
    "dedup_index_path": "",
    "dedup_index_max_age_seconds": 21600,
}

WEB_CONTENT_FILE: Path | None = None
WEB_TITLE = ""
WEB_META: dict[str, str] = {}
DATE = time.strftime("%Y-%m-%d")
ID = time.strftime("%Y%m%d%H%M")
USAGE_LOG_PATH = Path.home() / ".openclaw/logs/pkm-entry-usage.jsonl"


def echo(msg: str = "") -> None:
    print(msg, flush=True)


def log_entry_usage(entry: str, status: str, **kwargs: Any) -> None:
    try:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "entry": entry,
            "status": status,
        }
        payload.update(kwargs)
        USAGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with USAGE_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def error_exit(msg: str) -> None:
    log_entry_usage("zk", "error", message=msg)
    print(f"❌ 错误: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def load_vault_config() -> dict[str, Any]:
    """Load vault-config.yaml (multi-vault definitions)."""
    import yaml
    try:
        if VAULT_CONFIG_PATH.exists():
            data = yaml.safe_load(VAULT_CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except ImportError:
        # Fallback: minimal YAML parsing without PyYAML
        pass
    except Exception:
        pass
    return {"vaults": {}, "default_vault": "octopus"}


def resolve_vault_path(vault_name: str, vault_config: dict[str, Any]) -> Path:
    """Resolve a vault name to its filesystem path."""
    vaults = vault_config.get("vaults", {})
    if vault_name in vaults:
        raw_path = vaults[vault_name].get("path", "")
        return Path(raw_path).expanduser()
    # Fallback: treat as literal path
    return Path(vault_name).expanduser()


def get_type_mapping(vault_name: str, vault_config: dict[str, Any]) -> dict[str, str]:
    """Get type→directory mapping for a specific vault."""
    vaults = vault_config.get("vaults", {})
    if vault_name in vaults:
        return vaults[vault_name].get("type_mapping", {})
    return vault_config.get("type_mapping", {})


def get_lit_subtypes(vault_name: str, vault_config: dict[str, Any]) -> dict[str, str]:
    """Get literature subtype mapping for a specific vault (papers/books/articles...)."""
    vaults = vault_config.get("vaults", {})
    if vault_name in vaults:
        return vaults[vault_name].get("lit_subtypes", {})
    return {}


def load_config() -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    cfg_path = SCRIPT_DIR / "pkm_pipeline_config.json"
    if cfg_path.exists():
        try:
            loaded = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                cfg.update(loaded)
        except Exception:
            pass
    return cfg


def load_dedup_policy(path_str: str) -> dict[str, Any]:
    default = {"keep_source_urls": [], "keep_titles": [], "notes": {}}
    try:
        p = Path(path_str).expanduser()
        if not p.exists():
            return default
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return default
        return {
            "keep_source_urls": data.get("keep_source_urls", []) or [],
            "keep_titles": data.get("keep_titles", []) or [],
            "notes": data.get("notes", {}) or {},
        }
    except Exception:
        return default


def is_intentional_duplicate(url: str, title: str, policy: dict[str, Any]) -> bool:
    keep_urls = set(policy.get("keep_source_urls", []))
    keep_titles = set(policy.get("keep_titles", []))
    return (url and url in keep_urls) or (title and title in keep_titles)


def resolve_dedup_index_path(config: dict[str, Any], vault: Path) -> Path:
    raw = str(config.get("dedup_index_path", "")).strip()
    if raw:
        return Path(raw).expanduser()
    return vault / ".zk-router/dedup_index.json"


def ensure_dedup_index(config: dict[str, Any], vault: Path, index_path: Path) -> bool:
    script = SCRIPT_DIR / "dedup_index.py"
    if not script.exists():
        return False

    max_age = int(config.get("dedup_index_max_age_seconds", 21600) or 21600)
    need_rebuild = True
    if index_path.exists():
        age = time.time() - index_path.stat().st_mtime
        if age <= max(60, max_age):
            need_rebuild = False

    if not need_rebuild:
        return True

    try:
        proc = subprocess.run(
            ["python3", str(script), "build", "--vault", str(vault), "--output", str(index_path)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        return proc.returncode == 0 and index_path.exists()
    except Exception:
        return False


def load_dedup_index(index_path: Path) -> dict[str, Any] | None:
    try:
        if not index_path.exists():
            return None
        data = json.loads(index_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        return None
    except Exception:
        return None


def find_existing_from_index(
    vault: Path,
    index_data: dict[str, Any] | None,
    source_url: str,
    title: str,
) -> Path | None:
    if not index_data:
        return None

    by_source = index_data.get("by_source_url", {}) if isinstance(index_data.get("by_source_url", {}), dict) else {}
    by_title = index_data.get("by_title", {}) if isinstance(index_data.get("by_title", {}), dict) else {}

    rel_candidates: list[str] = []
    seen = set()
    for rel in by_source.get(source_url, []) if source_url else []:
        if rel not in seen:
            seen.add(rel)
            rel_candidates.append(rel)
    for rel in by_title.get(title, []) if title else []:
        if rel not in seen:
            seen.add(rel)
            rel_candidates.append(rel)

    path_candidates: list[Path] = []
    for rel in rel_candidates:
        p = vault / rel
        if p.exists() and p.is_file():
            path_candidates.append(p)

    return _pick_best_candidate(path_candidates, title)


def update_dedup_index_entry(index_path: Path, rel_path: str, title: str, source_url: str) -> None:
    try:
        data = load_dedup_index(index_path) or {
            "version": 1,
            "generated_at": int(time.time()),
            "by_source_url": {},
            "by_title": {},
        }
        by_source = data.setdefault("by_source_url", {})
        by_title = data.setdefault("by_title", {})

        if source_url:
            arr = by_source.setdefault(source_url, [])
            if rel_path not in arr:
                arr.append(rel_path)
                arr.sort()
        if title:
            arr = by_title.setdefault(title, [])
            if rel_path not in arr:
                arr.append(rel_path)
                arr.sort()

        data["generated_at"] = int(time.time())
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        return


def extract_url(text: str) -> str:
    m = re.search(r"https?://\S+", text)
    return m.group(0) if m else ""


def generate_title(text: str) -> str:
    clean = re.sub(r"https?://\S+", "", text).strip()
    first_line = clean.splitlines()[0].strip() if clean.splitlines() else ""
    if len(first_line) > 30:
        return first_line[:30] + "..."
    return first_line


def run_router(input_text: str, source_context: str) -> dict:
    router = SCRIPT_DIR / "router.sh"
    if not router.exists():
        error_exit(f"路由脚本不存在: {router}")
    proc = subprocess.run(
        ["bash", str(router), input_text, source_context],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        error_exit("路由判断失败")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        error_exit("解析路由结果失败")


def inspect_web_reader_candidates(config: dict[str, Any]) -> tuple[Path | None, list[Path], list[Path]]:
    configured = [Path(str(c)).expanduser() for c in config.get("web_reader_candidates", [])]
    existing = [c for c in configured if c.exists() and c.is_file()]
    selected = existing[0] if existing else None
    return selected, configured, existing


def resolve_web_reader(config: dict[str, Any]) -> Path | None:
    selected, _, _ = inspect_web_reader_candidates(config)
    return selected


def parse_frontmatter(raw_text: str) -> tuple[dict, str]:
    lines = raw_text.splitlines()
    if len(lines) >= 3 and lines[0].strip() == "---":
        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break
        if end_idx is not None:
            fm_lines = lines[1:end_idx]
            body = "\n".join(lines[end_idx + 1 :]).strip()
            meta = {}
            for ln in fm_lines:
                if ":" in ln:
                    k, v = ln.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"')
            return meta, body
    return {}, raw_text.strip()


def fetch_web_content(url: str, config: dict[str, Any]) -> tuple[bool, str, Path | None, dict[str, str]]:
    web_reader, _, existing = inspect_web_reader_candidates(config)
    if web_reader is None:
        return False, "", None, {}

    print("🌐 使用 web-reader 抓取网页...", file=sys.stderr, flush=True)
    print(f"ℹ️ web-reader selected: {web_reader}", file=sys.stderr, flush=True)
    if len(existing) > 1:
        print(
            "⚠️ 检测到多个可用 web-reader 实现，已按候选顺序选择第一项；请定期收敛避免漂移",
            file=sys.stderr,
            flush=True,
        )

    for attempt in (1, 2, 3):
        with tempfile.NamedTemporaryFile(delete=False) as rf:
            raw_path = Path(rf.name)
        clean_path = raw_path.with_suffix(".clean.md")
        try:
            proc = subprocess.run(
                ["bash", str(web_reader), url, "--save", str(raw_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if proc.returncode == 0 and raw_path.exists() and raw_path.stat().st_size > 200:
                text = raw_path.read_text(encoding="utf-8", errors="ignore")
                meta, body = parse_frontmatter(text)
                clean_path.write_text(body + "\n", encoding="utf-8")
                title = meta.get("title", "")
                raw_path.unlink(missing_ok=True)
                return True, title, clean_path, {k: str(v) for k, v in meta.items()}
        finally:
            raw_path.unlink(missing_ok=True)

        clean_path.unlink(missing_ok=True)
        if attempt < 3:
            print(f"⚠️  抓取失败，准备重试 ({attempt}/3)...", file=sys.stderr, flush=True)
            time.sleep(attempt)

    return False, "", None, {}


def get_save_path(
    note_type: str,
    subtype: str,
    type_mapping: dict[str, str] | None = None,
    lit_subtypes: dict[str, str] | None = None,
) -> str:
    if type_mapping:
        # Use vault-specific mapping
        # Handle literature subtypes
        if note_type == "literature" and subtype:
            # Prefer dedicated literature subtype mapping from vault-config.yaml
            if lit_subtypes and subtype in lit_subtypes:
                return str(lit_subtypes[subtype])
            subtype_key = f"{note_type}_{subtype}"
            for suffix in (subtype, subtype_key):
                if suffix in type_mapping:
                    return type_mapping[suffix]
        if note_type in type_mapping:
            return type_mapping[note_type]
        # Fallback for unmapped types
        return "Zettels/1-Fleeting" if note_type in ("fleeting", "idea") else "Zettels/3-Permanent"
    # Legacy octopus mapping (backward compatible)
    if note_type == "literature":
        if subtype == "papers":
            return "Zettels/2-Literature/Papers"
        if subtype == "books":
            return "Zettels/2-Literature/Books"
        return "Zettels/2-Literature/Articles"
    if note_type == "idea":
        return "Zettels/1-Fleeting"
    if note_type in {"meeting", "plan"}:
        return "Efforts/1-Projects"
    if note_type == "review":
        return "Calendar/Reviews"
    if note_type in {"decision", "summary", "question"}:
        return "Zettels/3-Permanent"
    return "Zettels/1-Fleeting"


def iter_note_files(vault: Path):
    for p in vault.rglob("*.md"):
        if p.is_file():
            yield p


def _title_slug(title: str) -> str:
    s = re.sub(r'[/:*?"<>|]+', " ", title)
    return re.sub(r"\s+", " ", s).strip().replace(" ", "-")


def _path_quality_score(path: Path, expected_title: str = "") -> int:
    stem = path.stem
    score = 0

    # 惩罚明显退化文件名（例如 2025.md）
    if re.fullmatch(r"\d{4}", stem):
        score -= 100
    elif re.fullmatch(r"\d{4}-\d{2}", stem):
        score -= 80

    # 偏好信息量更高的文件名
    score += min(len(stem), 80)

    # 含中文通常比纯数字文件名信息量更高
    if re.search(r"[\u4e00-\u9fff]", stem):
        score += 30

    if expected_title:
        slug = _title_slug(expected_title)
        if stem == slug:
            score += 60
        elif slug and slug in stem:
            score += 30

    return score


def _pick_best_candidate(candidates: list[Path], expected_title: str = "") -> Path | None:
    if not candidates:
        return None
    return max(candidates, key=lambda p: (_path_quality_score(p, expected_title), -len(str(p))))


def find_existing_by_source_url(vault: Path, source_url: str, expected_title: str = "") -> Path | None:
    if not source_url:
        return None
    needle = f'source_url: "{source_url}"'
    candidates: list[Path] = []
    for p in iter_note_files(vault):
        try:
            if needle in p.read_text(encoding="utf-8", errors="ignore"):
                candidates.append(p)
        except Exception:
            continue
    return _pick_best_candidate(candidates, expected_title)


def find_existing_by_title(vault: Path, title: str) -> Path | None:
    if not title:
        return None
    needle = f'title: "{title}"'
    candidates: list[Path] = []
    for p in iter_note_files(vault):
        try:
            if needle in p.read_text(encoding="utf-8", errors="ignore"):
                candidates.append(p)
        except Exception:
            continue
    return _pick_best_candidate(candidates, title)


def generate_filename(title: str, note_type: str, url: str) -> str:
    clean_title = re.sub(r'[/:*?"<>|]+', " ", title)
    clean_title = re.sub(r"\s+", " ", clean_title).strip().replace(" ", "-")

    if not clean_title or len(clean_title) < 3:
        if url:
            clean_title = url.rstrip("/").split("/")[-1][:60]
        if not clean_title or len(clean_title) < 3:
            clean_title = f"note-{ID}"

    if note_type in {"literature", "decision", "summary", "question"}:
        return f"{clean_title}.md"
    if note_type in {"idea", "fleeting"}:
        return f"idea-{ID}.md"
    if note_type == "meeting":
        return f"meeting-{ID}.md"
    if note_type == "plan":
        return f"plan-{ID}.md"
    if note_type == "review":
        return f"review-{ID}.md"
    return f"note-{ID}.md"


def generate_frontmatter(note_type: str, title: str, url: str, metadata: dict[str, str] | None = None) -> str:
    metadata = metadata or {}
    if note_type == "literature":
        author = metadata.get("author", "")
        published = metadata.get("published", "")
        site = metadata.get("site", "")
        captured_via = metadata.get("captured_via", "")
        return (
            "---\n"
            f'title: "{title}"\n'
            "type: literature\n"
            f"date: {DATE}\n"
            f'source_url: "{url}"\n'
            f'author: "{author}"\n'
            f'published: "{published}"\n'
            f'site: "{site}"\n'
            f'captured_via: "{captured_via}"\n'
            "tags: []\n"
            "---\n\n"
        )
    if note_type == "idea":
        return (
            "---\n"
            f'title: "{title}"\n'
            "type: idea\n"
            f"date: {DATE}\n"
            "tags: []\n"
            "---\n\n"
        )
    if note_type == "meeting":
        return (
            "---\n"
            f'title: "{title}"\n'
            "type: meeting\n"
            f"date: {DATE}\n"
            "participants: []\n"
            "tags: []\n"
            "---\n\n"
        )
    if note_type == "plan":
        return (
            "---\n"
            f'title: "{title}"\n'
            "type: plan\n"
            f"date: {DATE}\n"
            "due: \n"
            "tags: []\n"
            "---\n\n"
        )
    if note_type == "review":
        return (
            "---\n"
            f'title: "{title}"\n'
            "type: review\n"
            f"date: {DATE}\n"
            "period: \n"
            "tags: []\n"
            "---\n\n"
        )
    if note_type == "decision":
        return (
            "---\n"
            f'title: "{title}"\n'
            "type: decision\n"
            f"date: {DATE}\n"
            "decision_status: proposed\n"
            "tags: []\n"
            "---\n\n"
        )
    if note_type == "summary":
        return (
            "---\n"
            f'title: "{title}"\n'
            "type: summary\n"
            f"date: {DATE}\n"
            "topics: []\n"
            "tags: []\n"
            "---\n\n"
        )
    if note_type == "question":
        return (
            "---\n"
            f'title: "{title}"\n'
            "type: question\n"
            f"date: {DATE}\n"
            "status: open\n"
            "tags: []\n"
            "---\n\n"
        )
    return (
        "---\n"
        f'title: "{title}"\n'
        "type: fleeting\n"
        f"date: {DATE}\n"
        "tags: []\n"
        "---\n\n"
    )


def process_content(input_text: str) -> str:
    if WEB_CONTENT_FILE and WEB_CONTENT_FILE.exists() and WEB_CONTENT_FILE.stat().st_size > 0:
        return WEB_CONTENT_FILE.read_text(encoding="utf-8", errors="ignore").strip()
    content = re.sub(r"https?://\S+", "", input_text)
    content = re.sub(r"\n\s*\n+", "\n\n", content).strip()
    return content


def is_feature_enabled(config: dict[str, Any], env_name: str, feature_key: str, default: bool = True) -> bool:
    raw = os.environ.get(env_name)
    if raw is not None:
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}
    features = config.get("features", {}) if isinstance(config.get("features", {}), dict) else {}
    return bool(features.get(feature_key, default))


def run_relation_discovery(
    config: dict[str, Any],
    vault: Path,
    title: str,
    source_url: str,
    content: str,
    current_note: Path,
) -> dict[str, Any] | None:
    enabled = is_feature_enabled(config, "ENABLE_RELATION_DISCOVERY", "relation_discovery", default=True)
    if not enabled:
        return None

    script = SCRIPT_DIR / "relation_discovery.py"
    if not script.exists():
        return None

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as tf:
            tmp_path = Path(tf.name)
            tmp_path.write_text(content, encoding="utf-8")

        proc = subprocess.run(
            [
                "python3",
                str(script),
                "--vault",
                str(vault),
                "--title",
                title,
                "--source-url",
                source_url,
                "--content-file",
                str(tmp_path),
                "--current-note",
                str(current_note),
                "--top-k",
                "5",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return None

        out = (proc.stdout or "").strip()
        if not out:
            return None
        return json.loads(out.splitlines()[-1])
    except Exception:
        return None
    finally:
        if tmp_path:
            tmp_path.unlink(missing_ok=True)


def append_relation_section(note_path: Path, relation_data: dict[str, Any] | None) -> None:
    if not relation_data or relation_data.get("status") != "ok":
        return
    related = relation_data.get("related", [])
    if not related:
        return

    lines = ["\n---\n\n", "## 关联笔记（自动发现）\n\n"]
    for item in related:
        rel_path = str(item.get("path", "")).strip()
        if not rel_path:
            continue
        relation = str(item.get("relation", "related"))
        score = item.get("score", 0)
        wikilink = rel_path[:-3] if rel_path.endswith(".md") else rel_path
        lines.append(f"- {relation} · [[{wikilink}]] (score={score})\n")

    if len(lines) <= 2:
        return

    with note_path.open("a", encoding="utf-8") as f:
        f.write("".join(lines))


def run_frontmatter_validate(config: dict[str, Any], note_type: str, title: str, source_url: str) -> dict[str, Any] | None:
    enabled = is_feature_enabled(config, "ENABLE_FM_VALIDATE", "frontmatter_validate", default=True)
    if not enabled:
        return None

    script = SCRIPT_DIR / "frontmatter_validate.py"
    if not script.exists():
        return None

    try:
        proc = subprocess.run(
            [
                "python3",
                str(script),
                "--note-type",
                note_type,
                "--title",
                title,
                "--date",
                DATE,
                "--source-url",
                source_url,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = (proc.stdout or "").strip()
        if not out:
            return None
        data = json.loads(out.splitlines()[-1])
        if proc.returncode != 0:
            return data
        return data
    except Exception:
        return None


def run_atomic_extract(config: dict[str, Any], content: str) -> dict[str, Any] | None:
    enabled = is_feature_enabled(config, "ENABLE_ATOMIC_EXTRACTION", "atomic_extraction", default=True)
    if not enabled:
        return None

    script = SCRIPT_DIR / "atomic_extract.py"
    if not script.exists():
        return None

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as tf:
            tmp_path = Path(tf.name)
            tmp_path.write_text(content, encoding="utf-8")

        proc = subprocess.run(
            ["python3", str(script), "--content-file", str(tmp_path), "--max", "5"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if proc.returncode != 0:
            return None
        out = (proc.stdout or "").strip()
        if not out:
            return None
        return json.loads(out.splitlines()[-1])
    except Exception:
        return None
    finally:
        if tmp_path:
            tmp_path.unlink(missing_ok=True)


def _sanitize_file_stem(title: str) -> str:
    stem = re.sub(r'[/:*?"<>|]+', " ", title or "").strip()
    stem = re.sub(r"\s+", "-", stem)
    return stem[:80] or f"atomic-{ID}"


def save_atomic_notes(
    vault: Path,
    source_note_rel: str,
    atomic_data: dict[str, Any] | None,
    atomic_target: str = "Zettels/3-Permanent",
) -> list[str]:
    if not atomic_data or atomic_data.get("status") != "ok":
        return []

    points = atomic_data.get("points", [])
    if not points:
        return []

    out_dir = vault / atomic_target
    out_dir.mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    source_wikilink = source_note_rel[:-3] if source_note_rel.endswith(".md") else source_note_rel

    for idx, point in enumerate(points[:5], 1):
        p_title = str(point.get("title", f"atomic-insight-{idx}")).strip()
        p_content = str(point.get("content", "")).strip()
        if not p_content:
            continue

        filename = f"{time.strftime('%Y%m%d%H%M%S')}-{_sanitize_file_stem(p_title)}.md"
        path = out_dir / filename
        # 防冲突
        if path.exists():
            path = out_dir / f"{path.stem}-{idx}.md"

        text = (
            "---\n"
            f'title: "{p_title}"\n'
            "type: permanent\n"
            f"date: {DATE}\n"
            "tags: [atomic, literature]\n"
            f"up: [[{source_wikilink}]]\n"
            "---\n\n"
            f"# {p_title}\n\n"
            f"{p_content}\n"
        )
        path.write_text(text, encoding="utf-8")
        created.append(str(path.relative_to(vault)))

    return created


def append_atomic_section(note_path: Path, created_rel_paths: list[str]) -> None:
    if not created_rel_paths:
        return
    lines = ["\n---\n\n", "## 原子笔记（自动提炼）\n\n"]
    for rel in created_rel_paths:
        wikilink = rel[:-3] if rel.endswith(".md") else rel
        lines.append(f"- [[{wikilink}]]\n")
    with note_path.open("a", encoding="utf-8") as f:
        f.write("".join(lines))


def _parse_vault_arg(argv: list[str]) -> str | None:
    """Parse --vault NAME from command-line arguments."""
    for i, arg in enumerate(argv):
        if arg == "--vault" and i + 1 < len(argv):
            return argv[i + 1]
    return None


def main() -> int:
    global WEB_CONTENT_FILE, WEB_TITLE, WEB_META

    config = load_config()
    vault_config = load_vault_config()

    # Resolve vault from --vault argument
    vault_arg = _parse_vault_arg(sys.argv)
    if vault_arg:
        vault = resolve_vault_path(vault_arg, vault_config)
        type_mapping = get_type_mapping(vault_arg, vault_config)
        lit_subtypes = get_lit_subtypes(vault_arg, vault_config)
    else:
        # Default vault (backward compatible)
        default_name = config.get("default_vault", vault_config.get("default_vault", "octopus"))
        vault = resolve_vault_path(default_name, vault_config)
        type_mapping = get_type_mapping(default_name, vault_config)
        lit_subtypes = get_lit_subtypes(default_name, vault_config)
        if not vault.exists():
            # Final fallback to hardcoded default
            vault = Path(str(config.get("vault", DEFAULT_CONFIG["vault"]))).expanduser()
            type_mapping = {}
            lit_subtypes = {}

    dedup_policy = load_dedup_policy(str(config.get("dedup_policy_path", "")))
    intentional_behavior = str(config.get("dedup_behavior_for_intentional", "skip")).lower()
    dedup_index_path = resolve_dedup_index_path(config, vault)

    ensure_dedup_index(config, vault, dedup_index_path)
    dedup_index_data = load_dedup_index(dedup_index_path)

    if not vault.exists() or not vault.is_dir():
        error_exit(f"Vault 不存在: {vault}")
    if not INPUT:
        error_exit("请输入内容")

    echo("🔍 分析内容类型...")
    route = run_router(INPUT, SOURCE_CONTEXT)

    note_type = route.get("type")
    subtype = route.get("subtype", "")
    score = int(route.get("score", 0))

    if not note_type:
        error_exit("无法确定笔记类型")

    title = generate_title(INPUT)
    url = extract_url(INPUT)

    if url and note_type == "literature":
        echo("🌐 抓取网页内容...")
        ok, web_title, clean_file, web_meta = fetch_web_content(url, config)
        if ok:
            echo("✅ 网页内容已抓取")
            WEB_CONTENT_FILE = clean_file
            WEB_TITLE = web_title
            WEB_META = web_meta or {}
            if WEB_TITLE:
                title = WEB_TITLE
        else:
            echo("⚠️  无法抓取网页，仅保存URL")

    save_dir = get_save_path(note_type, subtype, type_mapping, lit_subtypes)
    vault_name = vault_arg or config.get("default_vault", vault_config.get("default_vault", "octopus"))
    vaults = vault_config.get("vaults", {}) if isinstance(vault_config.get("vaults", {}), dict) else {}
    atomic_target = "Zettels/3-Permanent"
    if vault_name in vaults:
        atomic_target = str(vaults[vault_name].get("atomic_target", atomic_target))
    abs_save_dir = vault / save_dir
    abs_save_dir.mkdir(parents=True, exist_ok=True)

    intentional_dup = is_intentional_duplicate(url, title, dedup_policy)

    existing = find_existing_from_index(vault, dedup_index_data, url, title)
    if existing is None:
        # 索引 miss / 索引不可用时回退全量扫描
        existing = find_existing_by_source_url(vault, url, title) if url else None
        if existing is None:
            existing = find_existing_by_title(vault, title)

    if existing and not FORCE_MODE:
        if intentional_dup and intentional_behavior == "allow_create":
            rel = existing.relative_to(vault)
            echo("ℹ️  命中 intentional duplicate policy，继续新建")
            echo(f"📁 已有: {rel}")
        else:
            rel = existing.relative_to(vault)
            reason = "intentional_duplicate" if intentional_dup else "duplicate"
            echo()
            echo("⏭️  检测到同源/同标题笔记已存在，跳过新建")
            echo(f"📁 复用: {rel}")
            if intentional_dup:
                echo("🧭 该条目命中 intentional duplicate policy（默认行为: skip）")
            echo()
            echo(
                json.dumps(
                    {
                        "status": "skipped",
                        "reason": reason,
                        "path": str(rel),
                        "title": title,
                    },
                    ensure_ascii=False,
                )
            )
            log_entry_usage(
                "zk",
                "skipped",
                reason=reason,
                title=title,
                path=str(rel),
                note_type=note_type,
                source_url=url,
                force=FORCE_MODE,
            )
            if WEB_CONTENT_FILE:
                WEB_CONTENT_FILE.unlink(missing_ok=True)
            return 0

    if existing and FORCE_MODE:
        rel = existing.relative_to(vault)
        echo("ℹ️  检测到重复，但 ZK_FORCE=1，继续新建")
        echo(f"📁 已有: {rel}")

    filename = generate_filename(title, note_type, url)
    filepath = abs_save_dir / filename
    if filepath.exists():
        base = filepath.stem
        filepath = abs_save_dir / f"{base}-{ID}.md"
        filename = filepath.name

    frontmatter = generate_frontmatter(note_type, title, url, WEB_META)
    content = process_content(INPUT)

    fm_validation = run_frontmatter_validate(config, note_type, title, url)
    if fm_validation and fm_validation.get("status") == "error":
        code = fm_validation.get("code", "FM_VALIDATE_ERROR")
        missing = ",".join(fm_validation.get("missing", []))
        error_exit(f"Frontmatter 校验失败 [{code}] 缺失字段: {missing}")

    parts = [frontmatter]

    if note_type == "literature":
        parts += [f"# {title}\n\n"]
        if url:
            source_lines = [f"> 来源: [{url}]({url})"]
            author = WEB_META.get("author", "").strip()
            published = WEB_META.get("published", "").strip()
            site = WEB_META.get("site", "").strip()
            captured_via = WEB_META.get("captured_via", "").strip()
            if author:
                source_lines.append(f"> 作者: {author}")
            if published:
                source_lines.append(f"> 发布时间: {published}")
            if site:
                source_lines.append(f"> 来源站点: {site}")
            if captured_via:
                source_lines.append(f"> 抓取方式: {captured_via}")
            parts += ["\n".join(source_lines) + "\n\n"]
    elif note_type == "meeting":
        parts += [f"# 会议记录: {title}\n\n", f"**时间**: {DATE}\n\n", "**参与者**: \n\n"]
    elif note_type == "plan":
        parts += [f"# 计划: {title}\n\n", f"**创建时间**: {DATE}\n\n"]
    elif note_type == "review":
        parts += [f"# 回顾: {title}\n\n", f"**时间**: {DATE}\n\n"]
    elif note_type == "question":
        parts += [f"# 问题: {title}\n\n", f"**提出时间**: {DATE}\n\n", "**状态**: 🟡 待解决\n\n"]

    parts += [content + "\n"]

    if note_type == "literature":
        parts += ["\n---\n\n", "## 摘录时间\n\n", f"{DATE}\n"]
    elif note_type == "meeting":
        parts += ["\n---\n\n", "## 行动项\n\n", "- [ ] \n"]
    elif note_type == "plan":
        parts += ["\n---\n\n", "## 进度\n\n", "- [ ] 待开始\n"]
    elif note_type == "question":
        parts += ["\n---\n\n", "## 思考过程\n\n", "## 可能的答案\n\n", "## 相关资源\n"]

    filepath.write_text("".join(parts), encoding="utf-8")
    update_dedup_index_entry(dedup_index_path, str(filepath.relative_to(vault)), title, url)

    relation_data = None
    atomic_created: list[str] = []
    if note_type == "literature":
        source_rel = str(filepath.relative_to(vault))
        relation_data = run_relation_discovery(config, vault, title, url, content, filepath)
        append_relation_section(filepath, relation_data)

        atomic_data = run_atomic_extract(config, content)
        atomic_created = save_atomic_notes(vault, source_rel, atomic_data, atomic_target=atomic_target)
        append_atomic_section(filepath, atomic_created)

    echo()
    if score >= 80:
        echo(f"✅ 已保存为 {note_type} 笔记 (置信度: {score}%)")
    elif score >= 50:
        echo(f"✅ 已保存为 {note_type} 笔记 (置信度: {score}%)")
        echo()
        echo("💡 如需调整类型，回复: 改zku(文献)/zki(想法)/zkm(会议)/zkt(计划)")
    else:
        echo(f"⚠️  已保存为 {note_type} 笔记 (置信度较低: {score}%)")
        echo()
        echo("💡 建议检查类型是否正确，可回复改zku/zki/zkm/zkt调整")

    echo()
    echo(f"📄 标题: {title}")
    echo(f"📁 位置: {save_dir}/{filename}")
    echo(f"📅 日期: {DATE}")

    echo()
    payload = {
        "status": "success",
        "type": note_type,
        "score": score,
        "title": title,
        "path": f"{save_dir}/{filename}",
        "relation_count": len((relation_data or {}).get("related", [])) if relation_data else 0,
        "atomic_count": len(atomic_created),
        "frontmatter_validation": (fm_validation or {}).get("status", "disabled") if fm_validation else "disabled",
        "metadata": {
            "author": WEB_META.get("author", "") if note_type == "literature" else "",
            "published": WEB_META.get("published", "") if note_type == "literature" else "",
            "site": WEB_META.get("site", "") if note_type == "literature" else "",
            "captured_via": WEB_META.get("captured_via", "") if note_type == "literature" else "",
        },
    }

    echo(json.dumps(payload, ensure_ascii=False))

    log_entry_usage(
        "zk",
        "success",
        note_type=note_type,
        score=score,
        title=title,
        path=f"{save_dir}/{filename}",
        source_url=url,
        relation_count=payload.get("relation_count", 0),
        atomic_count=payload.get("atomic_count", 0),
        frontmatter_validation=payload.get("frontmatter_validation", "disabled"),
        force=FORCE_MODE,
    )

    if WEB_CONTENT_FILE:
        WEB_CONTENT_FILE.unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

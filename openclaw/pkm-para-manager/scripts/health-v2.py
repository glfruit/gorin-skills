#!/usr/bin/env python3
"""PKM Health v2 scanner

Full-vault health scoring for Obsidian PKM (Zettelkasten + PARA + Ideaverse).
No third-party dependency required.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
ASCII_KEY_RE = re.compile(r"^[\x00-\x7F]+$")


@dataclass
class Note:
    path: Path
    rel: str
    content: str
    body: str
    fm_raw: str
    fm: Dict[str, str]


def load_type_mapping(config_path: Path) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not config_path.exists():
        return mapping
    in_block = False
    for line in config_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("type_mapping:"):
            in_block = True
            continue
        if in_block:
            if not line.startswith("  ") and line.strip():
                break
            m = re.match(r"\s{2}([a-zA-Z0-9_-]+):\s+(.+?)\s*$", line)
            if m:
                mapping[m.group(1).strip()] = m.group(2).strip()
    return mapping


def parse_frontmatter(text: str) -> Tuple[str, Dict[str, str], str]:
    if not text.startswith("---\n"):
        return "", {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", {}, text
    fm_raw = text[4:end]
    body = text[end + 5 :]
    fm: Dict[str, str] = {}
    current_key = None
    for line in fm_raw.splitlines():
        if re.match(r"^\s*#", line):
            continue
        if re.match(r"^[A-Za-z0-9_-]+:\s*", line):
            key, value = line.split(":", 1)
            current_key = key.strip()
            fm[current_key] = value.strip()
        elif current_key and re.match(r"^\s*-\s+", line):
            fm[current_key] = (fm[current_key] + "\n" + line).strip()
    return fm_raw, fm, body


def read_notes(vault: Path) -> List[Note]:
    notes: List[Note] = []
    for p in vault.rglob("*.md"):
        rel = p.relative_to(vault).as_posix()
        if rel.startswith(".obsidian/"):
            continue
        if rel.startswith("Archives/"):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        fm_raw, fm, body = parse_frontmatter(text)
        notes.append(Note(path=p, rel=rel, content=text, body=body, fm_raw=fm_raw, fm=fm))
    return notes


def fm_rule_violations(note: Note) -> List[str]:
    v: List[str] = []
    lines = note.fm_raw.splitlines() if note.fm_raw else []
    if not lines:
        v.append("missing_frontmatter")
        return v

    # 1) list item inline comment
    for line in lines:
        if re.search(r"^\s*-\s+.+\s+[—–-]\s+.+$", line):
            v.append("list_inline_comment")
            break

    # 2) wikilink in frontmatter must be quoted
    keys_need_quote = {"up", "project", "area", "related"}
    for key, value in note.fm.items():
        if key not in keys_need_quote:
            continue
        if "[[" in value:
            for frag in re.findall(r"\[\[[^\]]+\]\]", value):
                if f'"{frag}"' not in value and f"'{frag}'" not in value:
                    v.append("wikilink_not_quoted")
                    break

    # 3) ASCII keys
    for line in lines:
        m = re.match(r"^([A-Za-z0-9_\-\u0080-\uFFFF]+):", line)
        if m and not ASCII_KEY_RE.match(m.group(1)):
            v.append("non_ascii_key")
            break

    # 4) date format
    for k in ("date", "created", "modified"):
        if k in note.fm and note.fm[k]:
            value = note.fm[k].strip('"\'')
            if not DATE_RE.match(value):
                v.append(f"bad_{k}")

    # 5) tags mixed style
    if "tags" in note.fm:
        tags_val = note.fm["tags"]
        has_inline = bool(re.search(r"\[[^\]]*\]", tags_val))
        has_multiline = "\n" in tags_val and bool(re.search(r"^\s*-\s+", tags_val, re.M))
        if has_inline and has_multiline:
            v.append("mixed_tags_style")

    return sorted(set(v))


def parse_created(note: Note) -> dt.date | None:
    c = note.fm.get("created", "").strip('"\'')
    if DATE_RE.match(c):
        try:
            return dt.date.fromisoformat(c)
        except Exception:
            return None
    return None


def get_outgoing_targets(text: str) -> List[str]:
    return [m.group(1).strip() for m in WIKILINK_RE.finditer(text)]


def normalize_tokens(text: str) -> set[str]:
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text.lower())
    tokens = [t for t in text.split() if len(t) >= 2]
    return set(tokens)


def score_bucket(value: float, thresholds: List[Tuple[float, float]]) -> float:
    for cond, score in thresholds:
        if value <= cond:
            return score
    return thresholds[-1][1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", default=str(Path.home() / "Workspace/PKM/octopus"))
    parser.add_argument("--config", default=str(Path.home() / ".gorin-skills/openclaw/pkm-core/vault-config.yaml"))
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser()
    config = Path(args.config).expanduser()
    out_dir = Path(args.out).expanduser() if args.out else vault / "Calendar/Logs"
    out_dir.mkdir(parents=True, exist_ok=True)

    notes = read_notes(vault)
    now = dt.date.today()
    mapping = load_type_mapping(config)

    by_name: Dict[str, List[Note]] = defaultdict(list)
    for n in notes:
        by_name[n.path.stem].append(n)

    all_note_names = set(by_name.keys())

    # A) structure
    total = len(notes) or 1
    type_mismatch = 0
    bad_names = 0
    naming_checked = 0

    for n in notes:
        ntype = n.fm.get("type", "").strip().lower()
        if ntype in mapping:
            expected = mapping[ntype].rstrip("/") + "/"
            if not n.rel.startswith(expected):
                type_mismatch += 1

        if ntype:
            naming_checked += 1
            stem = n.path.stem
            if ntype in {"meeting", "plan"} and not re.match(r"^\d{12}-", stem):
                bad_names += 1
            elif ntype == "review" and not re.match(r"^\d{8}-", stem):
                bad_names += 1

    directory_compliance = max(0.0, 1 - type_mismatch / total)
    naming_compliance = 1.0 if naming_checked == 0 else max(0.0, 1 - bad_names / naming_checked)

    # B) metadata
    invalid_fm = 0
    missing_required = 0
    bad_dates = 0
    for n in notes:
        v = fm_rule_violations(n)
        if v:
            invalid_fm += 1
        if any(x.startswith("bad_") for x in v):
            bad_dates += 1
        req = ["title", "type", "created", "tags"]
        if any(not n.fm.get(k) for k in req):
            missing_required += 1

    fm_compliance = max(0.0, 1 - invalid_fm / total)
    required_completeness = max(0.0, 1 - missing_required / total)
    date_validity = max(0.0, 1 - bad_dates / total)

    # C) graph
    incoming = Counter()
    broken_links = 0
    total_links = 0
    structure_notes = [n for n in notes if n.rel.startswith("Zettels/4-Structure/")]
    structure_ref = set()

    for s in structure_notes:
        for t in get_outgoing_targets(s.content):
            structure_ref.add(t)

    for n in notes:
        outs = get_outgoing_targets(n.content)
        total_links += len(outs)
        for target in outs:
            incoming[target] += 1
            if target not in all_note_names:
                broken_links += 1

    permanent = [n for n in notes if n.rel.startswith("Zettels/3-Permanent/")]
    orphans = [n for n in permanent if incoming[n.path.stem] == 0]

    has_outgoing = 0
    for n in notes:
        if get_outgoing_targets(n.content):
            has_outgoing += 1
    outgoing_coverage = has_outgoing / total

    moc_covered = 0
    for n in permanent:
        if n.path.stem in structure_ref:
            moc_covered += 1
    moc_coverage = 1.0 if not permanent else moc_covered / len(permanent)

    orphan_rate = 0.0 if not permanent else len(orphans) / len(permanent)
    broken_link_rate = 0.0 if total_links == 0 else broken_links / total_links

    # D) content
    # duplicate title rate
    title_counter = Counter(n.fm.get("title", "").strip().lower() for n in notes if n.fm.get("title"))
    dup_title_notes = sum(c for c in title_counter.values() if c > 1)
    dup_title_rate = 0.0 if total == 0 else dup_title_notes / total

    # near-duplicate lexical similarity among recent permanent notes
    recent_perm = []
    for n in permanent:
        c = parse_created(n)
        if c and (now - c).days <= 45:
            recent_perm.append(n)

    near_dup_pairs = 0
    checked_pairs = 0
    token_cache = {n.rel: normalize_tokens(n.body) for n in recent_perm}
    for i in range(len(recent_perm)):
        for j in range(i + 1, len(recent_perm)):
            a = token_cache[recent_perm[i].rel]
            b = token_cache[recent_perm[j].rel]
            if not a or not b:
                continue
            checked_pairs += 1
            jac = len(a & b) / max(1, len(a | b))
            if jac >= 0.85:
                near_dup_pairs += 1
    near_dup_rate = 0.0 if checked_pairs == 0 else near_dup_pairs / checked_pairs

    # fleeting backlog
    fleeting = [n for n in notes if n.rel.startswith("Zettels/1-Fleeting/")]
    backlog = 0
    for n in fleeting:
        c = parse_created(n)
        status = n.fm.get("status", "").lower()
        if c and (now - c).days > 14 and status not in {"archived", "done"}:
            backlog += 1
    backlog_rate = 0.0 if not fleeting else backlog / len(fleeting)

    # scoring
    # Structure 25
    structure_score = 25 * (0.45 * directory_compliance + 0.55 * naming_compliance)
    # Metadata 25
    metadata_score = 25 * (0.5 * fm_compliance + 0.3 * required_completeness + 0.2 * date_validity)
    # Graph 30
    graph_score = 30 * (
        0.35 * (1 - orphan_rate) +
        0.25 * outgoing_coverage +
        0.2 * moc_coverage +
        0.2 * (1 - broken_link_rate)
    )
    # Content 20
    content_score = 20 * (
        0.3 * (1 - min(1.0, dup_title_rate)) +
        0.35 * (1 - min(1.0, near_dup_rate)) +
        0.35 * (1 - min(1.0, backlog_rate))
    )

    total_score = round(structure_score + metadata_score + graph_score + content_score, 2)

    grade = "A" if total_score >= 90 else "B" if total_score >= 80 else "C" if total_score >= 70 else "D"

    week = now.isocalendar().week
    report_name = f"{now.strftime('%Y%m%d')}-PKM-Health-Report-W{week:02d}.md"
    report_path = vault / "Zettels/4-Structure" / report_name
    report_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "date": now.isoformat(),
        "total_notes": len(notes),
        "score": total_score,
        "grade": grade,
        "dimensions": {
            "structure": round(structure_score, 2),
            "metadata": round(metadata_score, 2),
            "graph": round(graph_score, 2),
            "content": round(content_score, 2),
        },
        "metrics": {
            "directory_compliance": round(directory_compliance, 4),
            "naming_compliance": round(naming_compliance, 4),
            "frontmatter_compliance": round(fm_compliance, 4),
            "required_completeness": round(required_completeness, 4),
            "date_validity": round(date_validity, 4),
            "orphan_rate": round(orphan_rate, 4),
            "outgoing_coverage": round(outgoing_coverage, 4),
            "moc_coverage": round(moc_coverage, 4),
            "broken_link_rate": round(broken_link_rate, 4),
            "duplicate_title_rate": round(dup_title_rate, 4),
            "near_duplicate_rate": round(near_dup_rate, 4),
            "fleeting_backlog_rate": round(backlog_rate, 4),
        },
        "counts": {
            "type_mismatch": type_mismatch,
            "bad_names": bad_names,
            "invalid_frontmatter": invalid_fm,
            "missing_required": missing_required,
            "orphans": len(orphans),
            "broken_links": broken_links,
            "total_links": total_links,
            "fleeting_backlog": backlog,
        },
    }

    latest_json = out_dir / "pkm-health-latest.json"
    latest_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    top_orphans = "\n".join([f"- [[{n.path.stem}]]" for n in orphans[:12]]) or "- 无"
    md = f"""---
title: "PKM Health Report W{week:02d}"
type: review
tags: [pkm, health, governance]
created: {now.isoformat()}
score: {total_score}
grade: {grade}
---

# PKM 健康报告（W{week:02d}）

- 总分：**{total_score} / 100**（等级 **{grade}**）
- 扫描笔记：{len(notes)}

## 四维得分
- Structure：{structure_score:.2f} / 25
- Metadata：{metadata_score:.2f} / 25
- Graph：{graph_score:.2f} / 30
- Content：{content_score:.2f} / 20

## 关键指标
- 目录合规率：{directory_compliance:.1%}
- Frontmatter 合规率：{fm_compliance:.1%}
- 孤儿率（Permanent）：{orphan_rate:.1%}
- 出链覆盖率：{outgoing_coverage:.1%}
- MOC 覆盖率：{moc_coverage:.1%}
- 断链率：{broken_link_rate:.1%}
- 近重复率：{near_dup_rate:.1%}
- Fleeting 积压率（>14天）：{backlog_rate:.1%}

## 风险清单（Top）
### 孤儿笔记
{top_orphans}

## 治理建议（自动生成）
1. 若孤儿率 > 15%，本周优先给 Permanent 增加 up/related 或挂到 MOC。
2. 若断链率 > 3%，优先修复目标不存在的 wikilinks。
3. 若 Fleeting 积压率 > 30%，执行一次 pkp 清仓升级。
4. 若 Frontmatter 合规率 < 95%，优先批量修复 metadata。

> 机器可读明细：`{latest_json}`
"""
    report_path.write_text(md, encoding="utf-8")

    print(f"PKM Health v2 completed: score={total_score}, grade={grade}")
    print(f"Report: {report_path}")
    print(f"JSON: {latest_json}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
atlas-ingest: Dropbox raw/ 增量扫描 & Clippings 编译管线

Usage:
    python3 ingest.py --source dropbox [--dry-run] [--file PATH]
    python3 ingest.py --source clippings [--dry-run]
    python3 ingest.py --source all [--dry-run]
"""

import argparse
import glob
import hashlib
import html
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import pymupdf4llm
except Exception:
    pymupdf4llm = None

try:
    import magic_pdf
except Exception:
    magic_pdf = None

MINERU_ENV_VAR = "ATLAS_ENABLE_MINERU"
MINERU_MIN_MAGIC_PDF_VERSION = (1, 0, 0)
MINERU_MODEL_REPO_ID = "opendatalab/PDF-Extract-Kit-1.0"
MINERU_LAYOUTREADER_REPO_ID = "hantian/layoutreader"
MINERU_REQUIRED_MODEL_PATHS = [
    "Layout/YOLO/doclayout_yolo_docstructbench_imgsz1280_2501.pt",
    "OCR/paddleocr_torch/ch_PP-OCRv5_det_infer.pth",
    "OCR/paddleocr_torch/ch_PP-OCRv5_rec_infer.pth",
]
MINERU_CACHE_DIR = os.path.expanduser("~/.cache/atlas-ingest/mineru")
MINERU_MODELS_DIR = os.path.join(MINERU_CACHE_DIR, "models")
MINERU_LAYOUTREADER_DIR = os.path.join(MINERU_CACHE_DIR, "layoutreader")
MINERU_CONFIG_PATH = os.path.join(MINERU_CACHE_DIR, "magic-pdf.json")
MINERU_NON_PAPER_SHORT_TEXT_CHARS = 1800
MINERU_NON_PAPER_GARBLED_RATIO = 0.12
MINERU_NON_PAPER_MARKER_HITS = 2
MINERU_NON_PAPER_LONG_MARKER_TEXT_CHARS = 6000
_mineru_warning_keys = set()
_mineru_health_cache = None

NON_PAPER_MINERU_MARKER_PATTERNS = [
    r"\btable\s+\d+\b",
    r"\bfig(?:ure)?\.?\s+\d+\b",
    r"\beq(?:uation)?\.?\s*\(?\d+\)?\b",
    r"\\(?:begin|end)\{(?:equation|align|table|tabular|figure)\}",
    r"\$[^$\n]{3,}\$",
    r"\b(?:precision|recall|f1|accuracy)\b",
    r"\b(?:dataset|benchmark|ablation)\b",
]

# ── LLM Availability ───────────────────────────────────────────────────

_llm_cache = {}  # 缓存 LLM 结果供 post_process 使用
LLM_AVAILABLE = False
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from llm import llm_chat, process_with_llm, extract_concepts_llm, extract_atoms_llm, review_with_local, is_omlx_online
    LLM_AVAILABLE = True
    print("  🤖 LLM module loaded (DeepSeek)")
except ImportError as e:
    print(f"  ⚠️ LLM module ImportError: {e}")
except Exception as e:
    print(f"  ⚠️ LLM module error: {e}")

# Try importing review functions separately (may fail on older installs)
LOCAL_REVIEW_AVAILABLE = False
try:
    if not LLM_AVAILABLE:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from llm import review_with_local as _rvl, is_omlx_online as _iomlx
        LOCAL_REVIEW_AVAILABLE = True
    else:
        # Already imported above
        LOCAL_REVIEW_AVAILABLE = True
except Exception:
    pass
except ImportError as e:
    print(f"  ⚠️ LLM module ImportError: {e}")
except Exception as e:
    print(f"  ⚠️ LLM module error: {e}")


def cache_llm_result(cache_key: str, llm_result: dict) -> None:
    if cache_key and llm_result:
        _llm_cache[cache_key] = llm_result


def peek_cached_llm_result(note_stem: str) -> Optional[dict]:
    if not note_stem:
        return None
    return _llm_cache.get(note_stem)


def pop_cached_llm_result(note_stem: str) -> Optional[dict]:
    if not note_stem:
        return None
    exact = _llm_cache.pop(note_stem, None)
    if exact is not None:
        return exact
    return None

# ── Concept Merge State ───────────────────────────────────────────────
_merge_count_this_run = 0
MAX_MERGES_PER_RUN = 10
MERGE_COOLDOWN_SECONDS = 24 * 3600  # 24 hours

MERGE_PROMPT = """你是一个知识库维护助手。现在有一个已有概念页面和一篇新文献，请将新文献的相关信息合并到概念页面中。

## 已有概念页面内容：
{existing_content}

## 新文献信息：
- 标题：{new_source_title}
- 摘要：{new_source_summary}
- 关键发现：{new_source_key_findings}

## 要求：
1. 保持已有内容不变，只做追加或标记
2. 如果新信息补充了概念定义，更新"## 定义"章节（保留原有定义，追加补充）
3. 如果新信息提供了新的研究发现，追加到"## 研究进展"章节，格式：
   ### YYYY-MM-DD · {new_source_title}
   {findings}
4. 如果新信息与已有内容矛盾，追加到"## 待验证（矛盾）"章节，格式：
   - [来源: {new_source_title}] 已有观点: {{existing}} vs 新观点: {{new}}
5. 如果没有新信息可合并，只返回 "NO_MERGE_NEEDED" 这六个字符
6. 返回完整的更新后概念页面内容（包含 frontmatter）
7. 确保页面结构为：定义 → 研究进展 → 待验证（矛盾）→ 跨领域关联 → 见于
"""


def merge_concept_with_new_source(concept_path: Path, new_source_title: str,
                                  new_source_summary: str = "",
                                  new_source_key_findings: str = "") -> bool:
    """使用 LLM 将新文献的信息合并到已有概念页面中。

    Returns True if merge was performed, False if skipped.
    """
    global _merge_count_this_run

    # 频率限制：每次 ingest 最多 10 个 merge
    if _merge_count_this_run >= MAX_MERGES_PER_RUN:
        print(f"    ⏭️  达到本次 merge 上限 ({MAX_MERGES_PER_RUN})，跳过")
        return False

    # 频率限制：同一概念 24h 内只 merge 一次
    try:
        mtime = concept_path.stat().st_mtime
        if (time.time() - mtime) < MERGE_COOLDOWN_SECONDS:
            print(f"    ⏭️  概念最近 24h 已更新，跳过 merge")
            return False
    except OSError:
        pass

    # 检查 frontmatter updated 字段（如果有的话）
    try:
        content = concept_path.read_text(encoding="utf-8", errors="ignore")
        fm, _ = parse_frontmatter(content)
        updated_str = fm.get("updated", "")
        if updated_str:
            try:
                from datetime import datetime as _dt
                updated_dt = _dt.fromisoformat(updated_str.replace("Z", "+00:00").replace("+08:00", "+08:00"))
                # Handle naive datetime strings
                if updated_dt.tzinfo is None:
                    updated_dt = updated_dt.replace(tzinfo=TZ)
                elapsed = (datetime.now(TZ) - updated_dt).total_seconds()
                if elapsed < MERGE_COOLDOWN_SECONDS:
                    print(f"    ⏭️  概念 frontmatter updated 最近 24h 已更新，跳过 merge")
                    return False
            except (ValueError, TypeError):
                pass
    except Exception:
        pass

    # 检查是否有足够的摘要信息可合并
    if not new_source_summary and not new_source_key_findings:
        print(f"    ⏭️  无摘要/发现信息，跳过 merge")
        return False

    if not LLM_AVAILABLE:
        print(f"    ⏭️  LLM 不可用，跳过 merge")
        return False

    try:
        existing_content = concept_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"    ⚠️  读取概念页面失败: {e}")
        return False

    _merge_count_this_run += 1
    print(f"    🔄 合并概念: {concept_path.stem} (已有定义，追加新发现) [{_merge_count_this_run}/{MAX_MERGES_PER_RUN}]")

    # 构建 findings 文本
    findings_text = new_source_key_findings
    if isinstance(new_source_key_findings, list):
        findings_text = "\n".join(f"- {f}" for f in new_source_key_findings)

    prompt = MERGE_PROMPT.format(
        existing_content=existing_content[:15000],
        new_source_title=new_source_title,
        new_source_summary=new_source_summary or "(无)",
        new_source_key_findings=findings_text or "(无)",
    )

    messages = [
        {"role": "system", "content": "你是知识库维护助手，擅长合并文献信息到概念页面。"},
        {"role": "user", "content": prompt},
    ]

    try:
        result = llm_chat(messages, max_tokens=8192)

        if "NO_MERGE_NEEDED" in result and len(result.strip()) < 30:
            print(f"    ℹ️  无新信息需要合并: {concept_path.stem}")
            return False

        # 更新文件
        concept_path.write_text(result.strip(), encoding="utf-8")
        print(f"    ✅ 概念合并完成: {concept_path.stem}")
        return True

    except Exception as e:
        print(f"    ⚠️  LLM merge 失败 ({concept_path.stem}): {e}")
        return False


# ── Synthesis & Research Suggestions ───────────────────────────────────────

SYNTHESIS_COOLDOWN_SECONDS = 12 * 3600  # 12 hours between synthesis updates per area

SYNTHESIS_PROMPT = """你是一个知识库维护助手。请更新以下领域的综合认知页面。

## 领域：{area_name}

## 当前综合认知：
{existing_synthesis}

## 新增信息（来自：{new_source_title}）：
- 摘要：{new_source_summary}
- 关键发现：{new_source_key_findings}

## 要求：
1. 保持已有内容结构，只做追加和微调
2. 将新发现整合到相应章节
3. 如果新信息改变了已有结论，标记为"更新：xxx"
4. 更新"最后更新"和"基于文献"数量
5. 如果"新兴方向"中有已变为共识的内容，移到"当前共识"
6. 输出完整的更新后 synthesis 内容

## 页面结构：
# {area_name} 领域综合认知

> 最后更新: YYYY-MM-DD | 基于文献: N 篇

## 当前共识
...

## 活跃争议
...

## 新兴方向
...

## 关键文献
- [[文献链接|标题]]
"""

SYNTHESIS_INIT_PROMPT = """你是一个知识库维护助手。请基于以下领域中的所有文献，生成初始的综合认知页面。

## 领域：{area_name}

## 文献列表：
{literature_list}

## 要求：
1. 综合所有文献的核心发现，按主题组织
2. 识别当前共识、活跃争议、新兴方向
3. 每个条目尽量引用来源文献
4. 关键文献列表用 wikilink 格式

## 页面结构：
# {area_name} 领域综合认知

> 最后更新: YYYY-MM-DD | 基于文献: N 篇

## 当前共识
...

## 活跃争议
...

## 新兴方向
...

## 关键文献
- [[文献链接|标题]]
"""

RESEARCH_SUGGESTIONS_PROMPT = """基于当前知识库状态，建议 2-3 个值得深入探索的研究方向或应该寻找的文献类型。

知识库状态：
- 文献总数: {total_literature}
- 概念总数: {total_concepts}
- 矛盾标记: {total_contradictions}
- 领域分布: {area_distribution}
- 最近添加: {recent_titles}

要求：
1. 建议要具体，不要笼统
2. 基于知识库中的空白领域或活跃争议
3. 如果有矛盾标记，建议可以关注的方向
4. 每个建议 1-2 句话
"""


def update_area_synthesis(area_name: str, new_source_title: str,
                          new_source_summary: str = "",
                          new_source_key_findings: str = "") -> bool:
    """Update area synthesis page with new literature info.

    Returns True if synthesis was updated, False if skipped.
    """
    if not area_name or area_name == "未分类":
        return False
    if not LLM_AVAILABLE:
        print(f"    ⏭️  LLM 不可用，跳过 synthesis 更新")
        return False
    if not new_source_summary and not new_source_key_findings:
        return False

    area_dir = Path(CONFIG["atlas_vault"]) / "5-Areas" / area_name
    area_dir.mkdir(parents=True, exist_ok=True)
    synthesis_path = area_dir / "synthesis.md"

    # 频率限制：每领域 12h 最多更新一次
    if synthesis_path.exists():
        try:
            mtime = synthesis_path.stat().st_mtime
            if (time.time() - mtime) < SYNTHESIS_COOLDOWN_SECONDS:
                print(f"    ⏭️  Synthesis 最近 12h 已更新，跳过 ({area_name})")
                return False
        except OSError:
            pass

    # Build findings text
    if isinstance(new_source_key_findings, list):
        findings_text = "\n".join(f"- {f}" for f in new_source_key_findings)
    else:
        findings_text = new_source_key_findings or "(无)"

    # Read existing synthesis
    existing_synthesis = "(尚无内容，请根据新信息初始化)"
    if synthesis_path.exists():
        try:
            existing_synthesis = synthesis_path.read_text(encoding="utf-8", errors="ignore")[:15000]
        except Exception:
            pass

    print(f"    🔄 更新 synthesis: {area_name}")

    prompt = SYNTHESIS_PROMPT.format(
        area_name=area_name,
        existing_synthesis=existing_synthesis,
        new_source_title=new_source_title,
        new_source_summary=new_source_summary or "(无)",
        new_source_key_findings=findings_text,
    )

    messages = [
        {"role": "system", "content": "你是知识库维护助手，擅长综合多文献信息生成领域认知页面。"},
        {"role": "user", "content": prompt},
    ]

    try:
        result = llm_chat(messages, max_tokens=8192)
        synthesis_path.write_text(result.strip(), encoding="utf-8")
        print(f"    ✅ Synthesis 更新完成: {area_name}/synthesis.md")
        return True
    except Exception as e:
        print(f"    ⚠️  Synthesis 更新失败 ({area_name}): {e}")
        return False


def synthesize_all_areas():
    """Scan all literature notes, group by area, and generate initial synthesis for each."""
    if not LLM_AVAILABLE:
        print("❌ LLM 模块不可用，无法生成 synthesis")
        return

    print("\n🔄 Synthesizing all areas...")

    # Group literature notes by area
    area_notes: Dict[str, list] = {}
    for note_path in iter_literature_notes():
        fm, body = load_note_frontmatter(note_path)
        if fm.get("type") != "literature":
            continue
        area = fm.get("area", "")
        if not area or area == "未分类":
            continue
        title = fm.get("title", note_path.stem)
        summary = ""
        findings = ""

        # Extract summary from body
        sm = re.search(r"## 摘要\n\n(.{20,500}?)(?=\n## |\n---|$)", body, re.DOTALL)
        if sm:
            summary = re.sub(r"\s+", " ", sm.group(1).strip())[:400]

        # Extract key findings from body
        fm_section = re.search(r"## 关键发现\n\n(.{20,1000}?)(?=\n## |\n---|$)", body, re.DOTALL)
        if fm_section:
            findings = re.sub(r"\s+", " ", fm_section.group(1).strip())[:600]

        note_rel = os.path.relpath(str(note_path), CONFIG["atlas_vault"])
        if note_rel.endswith(".md"):
            note_rel = note_rel[:-3]

        if area not in area_notes:
            area_notes[area] = []
        area_notes[area].append({
            "title": title,
            "wikilink": f"[[{note_rel}|{title}]]",
            "summary": summary,
            "findings": findings,
        })

    if not area_notes:
        print("  ⚠️  未找到带 area 字段的文献笔记")
        return

    for area_name, notes in sorted(area_notes.items()):
        area_dir = Path(CONFIG["atlas_vault"]) / "5-Areas" / area_name
        area_dir.mkdir(parents=True, exist_ok=True)
        synthesis_path = area_dir / "synthesis.md"

        # Build literature list for prompt
        lit_parts = []
        for i, note in enumerate(notes, 1):
            part = f"### {i}. {note['title']}\n\n"
            if note["summary"]:
                part += f"摘要: {note['summary']}\n\n"
            if note["findings"]:
                part += f"关键发现: {note['findings']}\n\n"
            lit_parts.append(part)
        literature_list = "\n".join(lit_parts)

        print(f"\n  📂 {area_name} ({len(notes)} 篇文献)")

        prompt = SYNTHESIS_INIT_PROMPT.format(
            area_name=area_name,
            literature_list=literature_list[:25000],
        )

        messages = [
            {"role": "system", "content": "你是知识库维护助手，擅长综合多文献信息生成领域认知页面。"},
            {"role": "user", "content": prompt},
        ]

        try:
            result = llm_chat(messages, max_tokens=8192)
            synthesis_path.write_text(result.strip(), encoding="utf-8")
            print(f"  ✅ {area_name}/synthesis.md 生成完成")
        except Exception as e:
            print(f"  ❌ {area_name} synthesis 生成失败: {e}")

    print(f"\n✅ Synthesis 完成: {len(area_notes)} 个领域")
    auto_git_commit("synthesize", f"{len(area_notes)} areas")


def generate_research_suggestions() -> str:
    """Generate research suggestions based on current vault state.

    Returns the suggestions text, or empty string if unavailable.
    Should be called once after all files are processed (not per-file).
    """
    if not LLM_AVAILABLE:
        return ""

    # Gather statistics
    lit_dir = Path(CONFIG["literature_dir"])
    lit_count = 0
    area_counts: Dict[str, int] = {}
    recent_titles: List[str] = []

    if lit_dir.exists():
        for md_file in lit_dir.rglob("*.md"):
            fm, _ = load_note_frontmatter(md_file)
            if fm.get("type") == "literature":
                lit_count += 1
                area = fm.get("area", "未分类")
                area_counts[area] = area_counts.get(area, 0) + 1
                title = fm.get("title", md_file.stem)
                date_val = fm.get("date", "")
                recent_titles.append(f"{title} ({area}, {date_val})")

    recent_titles.sort()
    recent_titles.reverse()
    recent_titles = recent_titles[:5]

    concept_count = 0
    concepts_dir = Path(CONFIG["concepts_dir"])
    if concepts_dir.exists():
        for md_file in concepts_dir.glob("*.md"):
            fm, _ = load_note_frontmatter(md_file)
            if fm.get("type") == "concept":
                concept_count += 1

    contradiction_count = count_contradictions()

    # Build area distribution text
    area_dist_parts = []
    for area, count in sorted(area_counts.items(), key=lambda x: x[1], reverse=True):
        area_dist_parts.append(f"{area}: {count} 篇")
    area_distribution = ", ".join(area_dist_parts) if area_dist_parts else "(无)"

    recent_text = "\n".join(f"- {t}" for t in recent_titles) if recent_titles else "(无)"

    prompt = RESEARCH_SUGGESTIONS_PROMPT.format(
        total_literature=str(lit_count),
        total_concepts=str(concept_count),
        total_contradictions=str(contradiction_count),
        area_distribution=area_distribution,
        recent_titles=recent_text,
    )

    messages = [
        {"role": "system", "content": "你是知识库分析助手，擅长识别研究空白和机会。"},
        {"role": "user", "content": prompt},
    ]

    try:
        result = llm_chat(messages, max_tokens=1024)
        return result.strip()
    except Exception as e:
        print(f"  ⚠️  研究建议生成失败: {e}")
        return ""


def append_suggestions_to_log(suggestions: str) -> None:
    """Append research suggestions to today's log.md entry."""
    if not suggestions:
        return

    log_path = Path(CONFIG["atlas_vault"]) / "log.md"
    if not log_path.exists():
        return

    try:
        content = log_path.read_text(encoding="utf-8", errors="ignore")
        section = f"\n## 💡 建议关注\n\n{suggestions}\n"
        log_path.write_text(content.rstrip() + "\n" + section, encoding="utf-8")
        print(f"  💡 研究建议已写入 log.md")
    except Exception as e:
        print(f"  ⚠️  Log 写入建议失败: {e}")


def read_today_suggestions() -> str:
    """Read today's research suggestions from log.md."""
    log_path = Path(CONFIG["atlas_vault"]) / "log.md"
    if not log_path.exists():
        return ""
    try:
        content = log_path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"## 💡 建议关注\n\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return ""


def count_contradictions() -> int:
    """统计概念页面中的矛盾条目数。"""
    concepts_dir = Path(CONFIG["concepts_dir"]).expanduser()
    count = 0
    if not concepts_dir.exists():
        return 0
    for f in concepts_dir.glob("*.md"):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            if "## 待验证（矛盾）" in content:
                # Count actual bullet entries under this section
                section = content.split("## 待验证（矛盾）")[-1]
                # Count lines starting with - that are content (not empty or another heading)
                for line in section.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("- ") and "[来源" in stripped:
                        count += 1
        except Exception:
            pass
    return count


# ── Git Auto-Commit ────────────────────────────────────────────────────

def auto_git_commit(operation, title):
    """Git commit atlas vault changes after each ingest operation."""
    atlas_dir = Path(CONFIG["atlas_vault"])
    if not (atlas_dir / ".git").exists():
        return
    try:
        subprocess.run(["git", "add", "-A"], cwd=atlas_dir, capture_output=True, text=True)
        result = subprocess.run(
            ["git", "commit", "-m", f"{operation} | {title}"],
            cwd=atlas_dir, capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  🔒 Git: {result.stdout.strip().splitlines()[-1]}")
    except Exception:
        pass  # git failure should not break ingest


# ── Operation Log ───────────────────────────────────────────────────────────

def append_to_log(operation: str, title: str, details: dict) -> None:
    """Append an entry to ~/pkm/atlas/log.md (Karpathy-style, grep-friendly).

    Args:
        operation: e.g. 'ingest', 'clippings', 'review | Gemma 4 补充'
        title: literature note title
        details: dict with keys like type, source, summary, concepts, atoms,
                 elapsed, model, file (wikilink)
    """
    log_path = Path(CONFIG["atlas_vault"]) / "log.md"
    now = datetime.now(TZ)
    timestamp = now.strftime("%Y-%m-%d %H:%M")

    # Ensure file exists with header
    if not log_path.exists():
        log_path.write_text("# Atlas 操作日志\n\n", encoding="utf-8")

    lines = [f"## [{timestamp}] {operation} | {title}"]

    entry_type = details.get("type", "")
    source = details.get("source", "")
    if entry_type or source:
        parts = []
        if entry_type:
            parts.append(entry_type)
        if source:
            parts.append(source)
        lines.append(f"- 类型: {' | '.join(parts)}")

    summary = details.get("summary", "")
    if summary:
        lines.append(f"- 摘要: {summary}")

    concepts = details.get("concepts", "")
    if concepts:
        lines.append(f"- 概念: {concepts}")

    atoms = details.get("atoms", "")
    if atoms:
        lines.append(f"- 原子笔记: {atoms}")

    elapsed = details.get("elapsed", "")
    model = details.get("model", "")
    if elapsed or model:
        time_str = elapsed
        if model:
            time_str = f"{elapsed} ({model})"
        lines.append(f"- 处理时间: {time_str}")

    file_wikilink = details.get("file", "")
    if file_wikilink:
        lines.append(f"- 文件: [[{file_wikilink}]]")

    entry = "\n".join(lines) + "\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)


# ── Configuration ──────────────────────────────────────────────────────────

TZ = timezone(timedelta(hours=8))  # Asia/Shanghai

CONFIG = {
    # Source paths
    "dropbox_raw": os.path.expanduser("~/pkm/raw"),
    "backup_dir": os.path.expanduser("~/Dropbox/OpenClaw/raw"),
    "clippings_dir": os.path.expanduser("~/pkm/atlas/9-Clippings/"),

    # Atlas vault paths
    "atlas_vault": os.path.expanduser("~/pkm/atlas/"),
    "literature_dir": os.path.expanduser("~/pkm/atlas/1-Literature/"),
    "concepts_dir": os.path.expanduser("~/pkm/atlas/2-Concepts/"),
    "permanent_dir": os.path.expanduser("~/pkm/atlas/3-Permanent/"),
    "index_dir": os.path.expanduser("~/pkm/atlas/4-Structure/Index/"),
    "reports_dir": os.path.expanduser("~/.openclaw/reports/atlas/"),

    # SQLite / state
    "db_path": os.path.expanduser("~/pkm/atlas/.state/dropbox.db"),
    "hash_state_path": os.path.expanduser("~/pkm/atlas/.state/ingest-hashes.json"),

    # Temp dir for locked file copies
    "temp_dir": "/tmp/atlas-ingest",

    # Retry config
    "max_retries": 5,
    "retry_delays": [1, 2, 4, 8, 16],
}

# ── Paper detection keywords ───────────────────────────────────────────────

PAPER_KEYWORDS = [
    "abstract", "method", "results", "conclusion", "introduction",
    "related work", "experiments", "evaluation", "dataset",
    "arxiv", "preprint", "conference", "journal",
]

BOOK_KEYWORDS = [
    "table of contents", "chapter", "preface", "foreword",
    "acknowledgment", "appendix", "bibliography", "index of",
]

NOISY_CONCEPT_NAMES = {
    "appendix",
    "ppendix",
    "abstract",
    "introduction",
    "conclusion",
    "related work",
    "proceedings",
    "in proceedings of the",
    "of skills",
    "the",
    "and",
}

ALLOWED_ACRONYM_CONCEPTS = {
    "AI", "AGI", "API", "BERT", "GMM", "GPT", "LLM", "NLP",
    "OCR", "PCA", "RAG", "RL", "SFT", "UMAP",
}

ROMAN_SECTION_LABELS = {
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
    "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII",
    "XIX", "XX",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".tiff", ".tif", ".bmp", ".gif"}
EPUB_CHAPTER_SKIP_TOKENS = {
    "about", "about the author", "also by", "copyright", "cover", "dedication",
    "footnote", "index", "nav", "title", "about the publisher",
}
MAX_BOOK_CHAPTERS = 30
MAX_CHAPTER_CHARS = 25000
MIN_CHAPTER_TEXT = 500

# ── Helpers ────────────────────────────────────────────────────────────────

def now_iso():
    return datetime.now(TZ).isoformat()


def extract_pdf_info(filepath: str) -> dict:
    """Best-effort PDF metadata via pdfinfo."""
    try:
        result = subprocess.run(
            ["pdfinfo", filepath],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return {}
        info = {}
        for line in result.stdout.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            info[key.strip().lower()] = value.strip()
        return info
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}
    except Exception:
        return {}


def ensure_dirs():
    """Create output directories if needed."""
    for d in [
        CONFIG["literature_dir"] + "Papers/",
        CONFIG["literature_dir"] + "Books/",
        CONFIG["literature_dir"] + "Articles/",
        CONFIG["concepts_dir"],
        CONFIG["permanent_dir"],
        CONFIG["index_dir"],
        CONFIG["temp_dir"],
        CONFIG["reports_dir"],
    ]:
        os.makedirs(d, exist_ok=True)
    # Ensure source dir and backup dir exist
    Path(CONFIG["dropbox_raw"]).expanduser().mkdir(parents=True, exist_ok=True)
    Path(CONFIG["backup_dir"]).expanduser().mkdir(parents=True, exist_ok=True)


def _safe_slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip())
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "unknown"


def write_ingest_run_report(source: str, stats: dict, dry_run: bool) -> tuple[str, str]:
    ensure_dirs()
    stamp = datetime.now(TZ).strftime("%Y%m%d-%H%M%S")
    base = f"ingest-{_safe_slug(source)}-{stamp}"
    json_path = os.path.join(CONFIG["reports_dir"], f"{base}.json")
    md_path = os.path.join(CONFIG["reports_dir"], f"{base}.md")

    payload = {
        "timestamp": now_iso(),
        "source": source,
        "dry_run": dry_run,
        "found": stats.get("found", 0),
        "new": stats.get("new", 0),
        "updated": stats.get("updated", 0),
        "skipped": stats.get("skipped", 0),
        "error_count": len(stats.get("errors", [])),
        "errors": stats.get("errors", []),
        "items": stats.get("items", []),
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    lines = [
        "# Atlas Ingest Run Report",
        "",
        f"- timestamp: {payload['timestamp']}",
        f"- source: {source}",
        f"- dry_run: {str(dry_run).lower()}",
        f"- found: {payload['found']}",
        f"- new: {payload['new']}",
        f"- updated: {payload['updated']}",
        f"- skipped: {payload['skipped']}",
        f"- error_count: {payload['error_count']}",
        "",
        "## Item Results",
    ]

    items = payload["items"] or []
    if not items:
        lines.append("- (none)")
    else:
        for item in items:
            note = item.get("note_path", "")
            detail = item.get("detail", "")
            suffix = []
            if note:
                suffix.append(f"note={note}")
            if detail:
                suffix.append(detail)
            suffix_text = f" ({'; '.join(suffix)})" if suffix else ""
            lines.append(f"- {item.get('filename', '?')} | {item.get('status', 'unknown')}{suffix_text}")

    lines.extend(["", "## Errors"])
    if payload["errors"]:
        lines.extend([f"- {err}" for err in payload["errors"]])
    else:
        lines.append("- none")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return json_path, md_path


def get_db():
    """Get SQLite connection with row factory."""
    conn = sqlite3.connect(CONFIG["db_path"])
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    """Ensure required tables exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS processed (
            path TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            mtime INTEGER NOT NULL,
            sha256 TEXT,
            file_type TEXT NOT NULL,
            processed_at TEXT NOT NULL,
            target_note TEXT,
            status TEXT DEFAULT 'success'
        );
        CREATE INDEX IF NOT EXISTS idx_mtime ON processed(mtime);
        CREATE INDEX IF NOT EXISTS idx_status ON processed(status);

        CREATE TABLE IF NOT EXISTS scan_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scanned_at TEXT NOT NULL,
            files_found INTEGER,
            files_new INTEGER,
            files_updated INTEGER,
            files_skipped INTEGER,
            errors TEXT
        );
    """)
    conn.commit()


def compute_sha256(filepath, chunk_size=1024 * 1024):
    """Compute SHA256 hash of a file with chunked reads."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def load_ingest_hash_state() -> dict:
    """Load PDF content-hash dedup state from disk."""
    state_path = Path(CONFIG["hash_state_path"]).expanduser()
    if not state_path.exists():
        return {}
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items() if k and v}
    except Exception as e:
        print(f"  ⚠️  ingest hash state 读取失败，回退为空: {e}")
    return {}


def save_ingest_hash_state(state: dict) -> None:
    """Persist PDF content-hash dedup state atomically."""
    state_path = Path(CONFIG["hash_state_path"]).expanduser()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = state_path.with_suffix(state_path.suffix + ".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(temp_path, state_path)


def sanitize_filename(name, max_len=80):
    """Sanitize a string for use as a filename."""
    # Remove/replace special characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '-', name.strip())
    name = re.sub(r'-+', '-', name)
    # Truncate
    if len(name) > max_len:
        name = name[:max_len].rstrip('-')
    return name or "untitled"


def normalize_text_key(value: str) -> str:
    """Normalize a text value for duplicate detection."""
    if not value:
        return ""
    normalized = value.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def normalize_source_url(url: str) -> str:
    """Normalize source URLs so the same paper/article can be matched reliably."""
    if not url:
        return ""
    normalized = str(url).strip()
    normalized = re.sub(r"#.*$", "", normalized)
    normalized = normalized.rstrip("/")
    return normalized.lower()


def is_valid_concept_name(concept_name: str) -> bool:
    """Reject OCR artifacts, section labels, and generic structural phrases."""
    if not concept_name:
        return False

    raw = concept_name.strip()
    normalized = normalize_text_key(raw)
    if not normalized:
        return False

    if normalized in NOISY_CONCEPT_NAMES:
        return False

    upper_raw = raw.upper()

    if upper_raw in ROMAN_SECTION_LABELS:
        return False

    if re.fullmatch(r"(?:I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)(?:-[A-Z])?", upper_raw):
        return False

    if re.match(r"^(of|in|for|the|and)\b", normalized):
        return False

    if re.search(r"\b(proceedings|appendix|section|figure|table|chapter)\b", normalized):
        return False

    if raw.isupper():
        compact = re.sub(r"[^A-Z0-9]", "", raw)
        if compact and compact not in ALLOWED_ACRONYM_CONCEPTS:
            if len(compact) <= 3:
                return False
            if re.search(r"[0-9-]", raw):
                return False
            return False

    if len(normalized) < 3:
        return False

    return True


def filter_concept_payloads(concepts) -> list:
    """Drop noisy concept payloads before creating nodes or writing links."""
    filtered = []
    seen = set()
    for concept in concepts or []:
        name = ""
        if isinstance(concept, dict):
            name = concept.get("name", "")
        else:
            name = str(concept)
        if not is_valid_concept_name(name):
            continue
        key = normalize_text_key(name)
        if key in seen:
            continue
        seen.add(key)
        filtered.append(concept)
    return filtered


def render_frontmatter(fm: dict) -> str:
    """Render a simple YAML frontmatter block without external dependencies."""
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(str(x) for x in v)}]")
        elif isinstance(v, str) and any(c in v for c in ':#{}[]|>!&*?\'"'):
            lines.append(f'{k}: "{v}"')
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def load_note_frontmatter(note_path: Path):
    """Best-effort frontmatter loader for an existing markdown note."""
    try:
        content = note_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}, ""
    return parse_frontmatter(content)


def iter_literature_notes():
    """Yield all literature markdown notes under the Atlas literature directory."""
    lit_dir = Path(CONFIG["literature_dir"])
    if not lit_dir.exists():
        return
    yield from lit_dir.rglob("*.md")


def find_existing_literature_note(source_path=None, source_url=None, title=None):
    """Find an existing literature note by source path, source URL, or title."""
    normalized_source_path = ""
    if source_path:
        normalized_source_path = os.path.abspath(os.path.expanduser(str(source_path)))
    normalized_source_url = normalize_source_url(source_url)
    normalized_title = normalize_text_key(title)

    best_match = None
    best_score = 0

    for note_path in iter_literature_notes() or []:
        fm, _ = load_note_frontmatter(note_path)
        if fm.get("type") != "literature":
            continue

        score = 0

        existing_source = fm.get("source", "")
        if existing_source and normalized_source_path:
            existing_source = os.path.abspath(os.path.expanduser(str(existing_source)))
            if existing_source == normalized_source_path:
                score = max(score, 100)

        existing_source_url = normalize_source_url(fm.get("source_url", ""))
        if existing_source_url and normalized_source_url and existing_source_url == normalized_source_url:
            score = max(score, 90)

        existing_title = normalize_text_key(fm.get("title", ""))
        if existing_title and normalized_title and existing_title == normalized_title:
            score = max(score, 70)

        if score > best_score:
            best_match = (str(note_path), fm)
            best_score = score

    if best_match:
        return best_match
    return None, {}


# ── File Classification ────────────────────────────────────────────────────

def classify_pdf(filepath):
    """Classify a PDF file as paper, book, or article based on text content."""
    pdf_info = extract_pdf_info(filepath)
    text = extract_text_from_pdf(filepath, allow_mineru=False)
    text_lower = text.lower()

    if not text or len(text) < 50:
        return "article"

    # Count keyword matches
    paper_score = sum(1 for kw in PAPER_KEYWORDS if kw in text_lower)
    book_score = sum(1 for kw in BOOK_KEYWORDS if kw in text_lower)
    pages = int(pdf_info.get("pages", "0") or "0")
    title = pdf_info.get("title", "")
    author = pdf_info.get("author", "")
    preview = text_lower[:4000]

    # Strong book signals first
    if pages >= 120:
        strong_book_tokens = (
            "isbn", "praise for", "about the author", "table of contents",
            "copyright", "oreilly", "o'reilly",
        )
        if any(token in preview for token in strong_book_tokens):
            return "book"
        if title and author and not re.fullmatch(r"\d+(?:\.\d+)?", title.strip()):
            return "book"

    if paper_score >= 3:
        return "paper"
    elif book_score >= 2:
        return "book"
    else:
        # Check for typical paper markers more aggressively
        if "abstract" in text_lower and ("method" in text_lower or "results" in text_lower):
            return "paper"
        return "article"


def classify_file(filepath):
    """Classify any file by extension and content."""
    ext = Path(filepath).suffix.lower()

    if ext == ".pdf":
        return classify_pdf(filepath)
    elif ext in (".md", ".markdown", ".txt"):
        content = ""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(5000).lower()
        except Exception:
            pass

        # Check if it looks like a web clipping
        if "http" in content or "source_url" in content or "url:" in content:
            return "article"
        return "article"
    elif ext in (".epub", ".mobi"):
        return "book"
    elif ext in IMAGE_EXTENSIONS:
        return "article"
    else:
        return "article"


def _markdown_to_plain_text(markdown: str) -> str:
    """Collapse markdown-ish output to readable plain text."""
    if not markdown:
        return ""
    text = markdown.replace("\r", "\n")
    text = re.sub(r"```.*?```", "\n", text, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^[ \t]*[-+*][ \t]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[ \t]*\d+\.[ \t]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\|", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()[:50000]


def _is_good_pdf_text(text: str, min_chars: int = 200) -> bool:
    """Heuristic quality gate for extracted PDF text."""
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) < min_chars:
        return False
    sample = stripped[:4000]
    words = re.findall(r"[A-Za-z]{2,}|[\u4e00-\u9fff]", sample)
    if len(words) < 40:
        return False
    weird = len(re.findall(r"[{}<>\\]{2,}|\bobj\b|\bendobj\b|/Type|stream|xref", sample, re.IGNORECASE))
    return weird <= 6


def _get_env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        _warn_once(f"env-int-{name}", f"  ⚠️  {name}={raw!r} 不是整数，回退默认值 {default}。")
        return default


def _get_env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        _warn_once(f"env-float-{name}", f"  ⚠️  {name}={raw!r} 不是数字，回退默认值 {default}。")
        return default


def _estimate_pdf_text_garbled_ratio(text: str) -> float:
    if not text:
        return 1.0
    sample = text[:6000]
    if not sample:
        return 1.0
    suspicious_chars = 0
    for ch in sample:
        code = ord(ch)
        if ch == "�":
            suspicious_chars += 1
        elif code < 32 and ch not in "\n\r\t":
            suspicious_chars += 1
        elif 0xE000 <= code <= 0xF8FF:
            suspicious_chars += 1
    weird_sequences = re.findall(r"[A-Za-z0-9][^\w\s]{3,}[A-Za-z0-9]|(?:cid:\d+)|(?:\(cid:\d+\))", sample)
    suspicious_chars += sum(len(item) for item in weird_sequences)
    return suspicious_chars / max(len(sample), 1)


def _count_non_paper_mineru_markers(text: str) -> int:
    if not text:
        return 0
    sample = text[:12000]
    total = 0
    for pattern in NON_PAPER_MINERU_MARKER_PATTERNS:
        total += len(re.findall(pattern, sample, flags=re.IGNORECASE))
    return total


def should_try_mineru_for_non_paper(text: str, ocr_fallback_signal: bool = False) -> Tuple[bool, List[str], Dict[str, float]]:
    """Lightweight heuristic for escalating suspicious non-paper PDFs to MinerU."""
    stripped = (text or "").strip()
    text_len = len(stripped)
    short_text_threshold = _get_env_int("ATLAS_MINERU_NON_PAPER_SHORT_TEXT_CHARS", MINERU_NON_PAPER_SHORT_TEXT_CHARS)
    garbled_ratio_threshold = _get_env_float("ATLAS_MINERU_NON_PAPER_GARBLED_RATIO", MINERU_NON_PAPER_GARBLED_RATIO)
    marker_hits_threshold = _get_env_int("ATLAS_MINERU_NON_PAPER_MARKER_HITS", MINERU_NON_PAPER_MARKER_HITS)
    long_marker_text_threshold = _get_env_int("ATLAS_MINERU_NON_PAPER_LONG_MARKER_TEXT_CHARS", MINERU_NON_PAPER_LONG_MARKER_TEXT_CHARS)

    garbled_ratio = _estimate_pdf_text_garbled_ratio(stripped)
    marker_hits = _count_non_paper_mineru_markers(stripped)

    reasons = []
    if text_len < short_text_threshold:
        reasons.append("short_text")
    if garbled_ratio >= garbled_ratio_threshold:
        reasons.append("garbled_text")
    if marker_hits >= marker_hits_threshold and text_len < long_marker_text_threshold:
        reasons.append("formula_markers")
    if ocr_fallback_signal:
        reasons.append("ocr_fallback_signal")

    stats = {
        "text_len": float(text_len),
        "garbled_ratio": garbled_ratio,
        "marker_hits": float(marker_hits),
        "short_text_threshold": float(short_text_threshold),
        "garbled_ratio_threshold": garbled_ratio_threshold,
        "marker_hits_threshold": float(marker_hits_threshold),
        "long_marker_text_threshold": float(long_marker_text_threshold),
    }
    return bool(reasons), reasons, stats


def _warn_once(key: str, message: str) -> None:
    if key in _mineru_warning_keys:
        return
    _mineru_warning_keys.add(key)
    print(message)


def _parse_version_tuple(version_text: str) -> Tuple[int, ...]:
    if not version_text:
        return tuple()
    parts = []
    for token in re.findall(r"\d+", version_text):
        try:
            parts.append(int(token))
        except ValueError:
            continue
    return tuple(parts)


def _get_magic_pdf_version() -> str:
    if magic_pdf is None:
        return ""
    try:
        return importlib_metadata.version("magic-pdf")
    except importlib_metadata.PackageNotFoundError:
        return getattr(magic_pdf, "__version__", "") or ""
    except Exception:
        return getattr(magic_pdf, "__version__", "") or ""


def _find_mineru_command() -> str:
    local_cmds = [
        os.path.join(os.path.dirname(sys.executable), "mineru"),
        os.path.join(os.path.dirname(sys.executable), "magic-pdf"),
    ]
    for candidate in [*local_cmds, shutil.which("mineru"), shutil.which("magic-pdf")]:
        if candidate and os.path.exists(candidate):
            return candidate
    return ""


def _is_truthy_env(value: Optional[str]) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _is_falsy_env(value: Optional[str]) -> bool:
    return str(value).strip().lower() in {"0", "false", "no", "off"}


def _resolve_mineru_env_policy() -> Tuple[bool, str]:
    raw = os.environ.get(MINERU_ENV_VAR)
    if raw is None or not str(raw).strip():
        return True, "default enabled"
    if _is_falsy_env(raw):
        return False, "disabled by env"
    if _is_truthy_env(raw):
        return True, "forced by env"
    _warn_once("mineru-env-invalid", f"  ⚠️  {MINERU_ENV_VAR}={raw!r} 无法识别，按默认开启处理。")
    return True, f"default enabled (invalid env: {raw})"


def _probe_mineru_health() -> Dict[str, str]:
    global _mineru_health_cache
    if _mineru_health_cache is not None:
        return _mineru_health_cache

    env_enabled, env_reason = _resolve_mineru_env_policy()
    if not env_enabled:
        _mineru_health_cache = {"enabled": "0", "reason": env_reason, "command": "", "version": ""}
        return _mineru_health_cache

    if magic_pdf is None:
        reason = "magic-pdf package unavailable"
        _warn_once("mineru-no-package", f"  ⚠️  MinerU skipped: {reason}.")
        _mineru_health_cache = {"enabled": "0", "reason": reason, "command": "", "version": ""}
        return _mineru_health_cache

    version_text = _get_magic_pdf_version()
    version_tuple = _parse_version_tuple(version_text)
    if version_tuple and version_tuple < MINERU_MIN_MAGIC_PDF_VERSION:
        reason = f"magic-pdf {version_text} is too old (< {'.'.join(map(str, MINERU_MIN_MAGIC_PDF_VERSION))})"
        _warn_once("mineru-old-version", f"  ⚠️  MinerU skipped: {reason}.")
        _mineru_health_cache = {"enabled": "0", "reason": reason, "command": "", "version": version_text}
        return _mineru_health_cache

    command = _find_mineru_command()
    if not command:
        reason = "mineru/magic-pdf CLI not found"
        _warn_once("mineru-no-cli", f"  ⚠️  MinerU skipped: {reason}.")
        _mineru_health_cache = {"enabled": "0", "reason": reason, "command": "", "version": version_text}
        return _mineru_health_cache

    cmd_name = Path(command).name
    help_args = [command, "--help"]
    try:
        result = subprocess.run(
            help_args,
            capture_output=True,
            text=True,
            timeout=15,
            env=os.environ.copy(),
        )
        help_output = "\n".join(part for part in [result.stdout, result.stderr] if part)
        if result.returncode != 0 or "Usage:" not in help_output:
            reason = f"{cmd_name} CLI incompatible"
            _warn_once("mineru-bad-cli", f"  ⚠️  MinerU skipped: {reason}.")
            _mineru_health_cache = {"enabled": "0", "reason": reason, "command": command, "version": version_text}
            return _mineru_health_cache
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        reason = f"CLI health check failed: {e}"
        _warn_once("mineru-health-check", f"  ⚠️  MinerU skipped: {reason}.")
        _mineru_health_cache = {"enabled": "0", "reason": reason, "command": command, "version": version_text}
        return _mineru_health_cache
    except Exception as e:
        reason = f"CLI health check error: {e}"
        _warn_once("mineru-health-check-generic", f"  ⚠️  MinerU skipped: {reason}.")
        _mineru_health_cache = {"enabled": "0", "reason": reason, "command": command, "version": version_text}
        return _mineru_health_cache

    _mineru_health_cache = {"enabled": "1", "reason": f"healthy ({env_reason})", "command": command, "version": version_text}
    return _mineru_health_cache


def _extract_pdf_text_via_pymupdf4llm(filepath: str, keep_markdown: bool = False) -> str:
    if pymupdf4llm is None:
        return ""
    try:
        markdown = pymupdf4llm.to_markdown(filepath)
        if keep_markdown:
            return markdown
        return _markdown_to_plain_text(markdown)
    except Exception as e:
        print(f"  ⚠️  PyMuPDF4LLM 提取失败: {e}")
        return ""


def _build_mineru_config(models_dir: str) -> Dict[str, object]:
    return {
        "models-dir": models_dir,
        "layoutreader-model-dir": MINERU_LAYOUTREADER_DIR,
        "device-mode": "cpu",
        "bucket_info": {"[default]": ["dummy", "dummy", "dummy"]},
        "layout-config": {"model": "doclayout_yolo"},
        "formula-config": {
            "mfd_model": "yolo_v8_mfd",
            "mfr_model": "unimernet_small",
            "enable": False,
        },
        "table-config": {
            "model": "rapid_table",
            "enable": False,
            "max_time": 400,
        },
        "latex-delimiter-config": {},
    }


def _ensure_mineru_config(config_path: str = MINERU_CONFIG_PATH, models_dir: str = MINERU_MODELS_DIR) -> str:
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)
    config = _build_mineru_config(models_dir)
    existing = None
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
    except Exception:
        existing = None
    if existing != config:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    return config_path


def _find_cached_mineru_model(relative_path: str) -> str:
    filename = os.path.basename(relative_path)
    candidates = [
        os.path.join(MINERU_MODELS_DIR, relative_path),
        os.path.expanduser(f"~/.cache/huggingface/hub/**/{filename}"),
        os.path.expanduser(f"~/.cache/modelscope/**/{filename}"),
    ]
    for pattern in candidates:
        for match in glob.glob(pattern, recursive=True):
            if os.path.isfile(match):
                return match
    return ""


def _find_cached_layoutreader_dir() -> str:
    if os.path.isdir(MINERU_LAYOUTREADER_DIR) and os.path.exists(os.path.join(MINERU_LAYOUTREADER_DIR, "config.json")):
        return MINERU_LAYOUTREADER_DIR
    for match in sorted(glob.glob(os.path.expanduser("~/.cache/huggingface/hub/models--hantian--layoutreader/snapshots/*")), reverse=True):
        if os.path.exists(os.path.join(match, "config.json")):
            return match
    return ""


def _ensure_mineru_layoutreader_model() -> Tuple[bool, str]:
    cached = _find_cached_layoutreader_dir()
    if cached == MINERU_LAYOUTREADER_DIR:
        return True, cached
    if cached:
        os.makedirs(MINERU_LAYOUTREADER_DIR, exist_ok=True)
        for name in ["config.json", "model.safetensors"]:
            src = os.path.join(cached, name)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(MINERU_LAYOUTREADER_DIR, name))
        if os.path.exists(os.path.join(MINERU_LAYOUTREADER_DIR, "config.json")):
            return True, MINERU_LAYOUTREADER_DIR

    try:
        from huggingface_hub import snapshot_download

        snapshot_download(repo_id=MINERU_LAYOUTREADER_REPO_ID, local_dir=MINERU_LAYOUTREADER_DIR)
        return True, MINERU_LAYOUTREADER_DIR
    except Exception as e:
        return False, str(e)


def _ensure_mineru_models(models_dir: str = MINERU_MODELS_DIR) -> Tuple[bool, str]:
    layoutreader_ready, layoutreader_detail = _ensure_mineru_layoutreader_model()
    if not layoutreader_ready:
        return False, f"layoutreader bootstrap failed: {layoutreader_detail}"

    missing = []
    for relative_path in MINERU_REQUIRED_MODEL_PATHS:
        target = os.path.join(models_dir, relative_path)
        if os.path.exists(target):
            continue

        os.makedirs(os.path.dirname(target), exist_ok=True)

        cached = _find_cached_mineru_model(relative_path)
        if cached and os.path.abspath(cached) != os.path.abspath(target):
            shutil.copy2(cached, target)
            continue

        missing.append((relative_path, target))

    if not missing:
        return True, models_dir

    try:
        from huggingface_hub import hf_hub_download

        for relative_path, target in missing:
            downloaded = hf_hub_download(
                repo_id=MINERU_MODEL_REPO_ID,
                filename=f"models/{relative_path}",
            )
            shutil.copy2(downloaded, target)
        return True, models_dir
    except Exception as e:
        return False, str(e)


def _build_mineru_repair_commands(models_dir: str = MINERU_MODELS_DIR) -> List[str]:
    hf_dir = os.path.join(MINERU_CACHE_DIR, "hf")
    return [
        (
            f"mkdir -p \"{models_dir}/Layout/YOLO\" "
            f"\"{models_dir}/OCR/paddleocr_torch\""
        ),
        (
            f"hf download {MINERU_MODEL_REPO_ID} "
            '"models/Layout/YOLO/doclayout_yolo_docstructbench_imgsz1280_2501.pt" '
            '"models/OCR/paddleocr_torch/ch_PP-OCRv5_det_infer.pth" '
            '"models/OCR/paddleocr_torch/ch_PP-OCRv5_rec_infer.pth" '
            f"--local-dir \"{hf_dir}\""
        ),
        (
            f"cp \"{hf_dir}/models/Layout/YOLO/doclayout_yolo_docstructbench_imgsz1280_2501.pt\" "
            f"\"{models_dir}/Layout/YOLO/doclayout_yolo_docstructbench_imgsz1280_2501.pt\""
        ),
        (
            f"cp \"{hf_dir}/models/OCR/paddleocr_torch/ch_PP-OCRv5_det_infer.pth\" "
            f"\"{models_dir}/OCR/paddleocr_torch/ch_PP-OCRv5_det_infer.pth\""
        ),
        (
            f"cp \"{hf_dir}/models/OCR/paddleocr_torch/ch_PP-OCRv5_rec_infer.pth\" "
            f"\"{models_dir}/OCR/paddleocr_torch/ch_PP-OCRv5_rec_infer.pth\""
        ),
    ]


def _mineru_manual_download_hint(models_dir: str = MINERU_MODELS_DIR) -> str:
    return "手动补齐命令:\n" + "\n".join(_build_mineru_repair_commands(models_dir))


def _collect_mineru_preflight() -> Dict[str, object]:
    health = _probe_mineru_health()
    config_exists = os.path.exists(MINERU_CONFIG_PATH)
    models = []
    missing_models = []

    for relative_path in MINERU_REQUIRED_MODEL_PATHS:
        target_path = os.path.join(MINERU_MODELS_DIR, relative_path)
        resolved_path = target_path if os.path.exists(target_path) else _find_cached_mineru_model(relative_path)
        exists = bool(resolved_path and os.path.exists(resolved_path))
        if not exists:
            missing_models.append(relative_path)
        models.append(
            {
                "name": relative_path,
                "exists": exists,
                "path": resolved_path or target_path,
            }
        )

    ready = health.get("enabled") == "1" and config_exists and not missing_models
    repair_commands = _build_mineru_repair_commands()
    return {
        "enabled": health.get("enabled") == "1",
        "reason": health.get("reason", "unknown"),
        "command": health.get("command", ""),
        "version": health.get("version", ""),
        "config_path": MINERU_CONFIG_PATH,
        "config_exists": config_exists,
        "models": models,
        "missing_models": missing_models,
        "conclusion": "ready" if ready else "will fallback",
        "repair_commands": repair_commands if missing_models or not ready else [],
    }


def _extract_pdf_text_via_mineru(filepath: str) -> str:
    """Best-effort MinerU extraction via local CLI output markdown."""
    health = _probe_mineru_health()
    if health.get("enabled") != "1":
        return ""

    command = health.get("command") or _find_mineru_command()
    if not command:
        return ""

    temp_dir = tempfile.mkdtemp(prefix="atlas-mineru-", dir=CONFIG["temp_dir"])
    try:
        config_path = _ensure_mineru_config()
        models_ready, models_detail = _ensure_mineru_models()
        if not models_ready:
            _warn_once(
                "mineru-model-bootstrap-failed",
                "  ⚠️  MinerU 模型准备失败，已回退到主链路: "
                f"{models_detail}. {_mineru_manual_download_hint()}",
            )
            return ""

        env = os.environ.copy()
        env.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        env.setdefault("MINERU_LMDEPLOY_DEVICE", "maca")
        env["MINERU_TOOLS_CONFIG_JSON"] = config_path

        cmd_name = Path(command).name
        if cmd_name == "magic-pdf":
            cli_args = [command, "-p", filepath, "-o", temp_dir, "-m", "auto"]
        else:
            cli_args = [command, "-p", filepath, "-o", temp_dir, "-b", "pipeline", "-m", "auto"]

        result = subprocess.run(
            cli_args,
            capture_output=True,
            text=True,
            timeout=900,
            env=env,
        )
        if result.returncode != 0:
            stderr = "\n".join(part.strip() for part in [result.stderr or "", result.stdout or ""] if part and part.strip())
            reason = stderr[:700] if stderr else "non-zero exit"
            _warn_once("mineru-runtime-failed", f"  ⚠️  MinerU 运行失败，已回退到主链路: {reason}")
            return ""

        stem = Path(filepath).stem
        candidates = []
        for md_path in Path(temp_dir).rglob("*.md"):
            name = md_path.name
            if name.endswith(("_middle.md", "_model.md")):
                continue
            score = 0
            if name == f"{stem}.md":
                score += 1000
            try:
                score += md_path.stat().st_size
            except OSError:
                pass
            candidates.append((score, md_path))
        if not candidates:
            _warn_once("mineru-no-markdown", "  ⚠️  MinerU 未产出可用 markdown，已回退到主链路")
            return ""

        best_md = max(candidates, key=lambda item: item[0])[1]
        markdown = best_md.read_text(encoding="utf-8", errors="ignore")
        return _markdown_to_plain_text(markdown)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        _warn_once("mineru-unavailable", f"  ⚠️  MinerU 不可用或超时，已回退到主链路: {e}")
        return ""
    except Exception as e:
        _warn_once("mineru-exception", f"  ⚠️  MinerU 提取异常，已回退到主链路: {e}")
        return ""
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def extract_text_from_pdf(filepath: str, allow_mineru: bool = True, keep_markdown: bool = False) -> str:
    """Extract text from PDF via PyMuPDF4LLM, optional MinerU, then OCR fallback."""
    best_text = ""
    mineru_health = {"enabled": "0", "reason": "classification mode" if not allow_mineru else "disabled"}
    if allow_mineru:
        mineru_health = _probe_mineru_health()

    chain_steps = ["PyMuPDF4LLM"]
    if allow_mineru:
        if mineru_health.get("enabled") == "1":
            chain_steps.append("MinerU (paper + heuristic non-paper)")
        else:
            chain_steps.append(f"MinerU skipped ({mineru_health.get('reason', 'disabled')})")
    else:
        chain_steps.append("MinerU skipped (classification mode)")
    chain_steps.append("OCR fallback")
    print(f"  ℹ️  PDF 提取候选链路: {' -> '.join(chain_steps)}")

    pymupdf_text = _extract_pdf_text_via_pymupdf4llm(filepath, keep_markdown=keep_markdown)
    if pymupdf_text:
        best_text = pymupdf_text

    pdf_kind = "article"
    mineru_attempted = False
    if allow_mineru and mineru_health.get("enabled") == "1":
        try:
            pdf_kind = classify_pdf(filepath)
        except Exception:
            pdf_kind = "article"
        print(f"  ℹ️  PDF 分类结果: {pdf_kind}")

        should_try_non_paper_mineru = False
        non_paper_reasons: List[str] = []
        non_paper_stats: Dict[str, float] = {}
        if pdf_kind != "paper":
            likely_needs_ocr = not _is_good_pdf_text(pymupdf_text)
            should_try_non_paper_mineru, non_paper_reasons, non_paper_stats = should_try_mineru_for_non_paper(
                pymupdf_text,
                ocr_fallback_signal=likely_needs_ocr,
            )

        if pdf_kind == "paper":
            mineru_attempted = True
            mineru_text = _extract_pdf_text_via_mineru(filepath)
            if _is_good_pdf_text(mineru_text):
                print("  ✅ PDF 最终采用链路: MinerU")
                return mineru_text
            if mineru_text and len(mineru_text) > len(best_text):
                best_text = mineru_text
        elif should_try_non_paper_mineru:
            reason_text = " + ".join(non_paper_reasons)
            print(
                "  ℹ️  non-paper MinerU triggered: "
                f"{reason_text} "
                f"(len={int(non_paper_stats.get('text_len', 0))}, "
                f"garbled_ratio={non_paper_stats.get('garbled_ratio', 0.0):.3f}, "
                f"marker_hits={int(non_paper_stats.get('marker_hits', 0))})"
            )
            mineru_attempted = True
            mineru_text = _extract_pdf_text_via_mineru(filepath)
            if _is_good_pdf_text(mineru_text):
                print("  ✅ PDF 最终采用链路: MinerU")
                return mineru_text
            if mineru_text and len(mineru_text) > len(best_text):
                best_text = mineru_text
        else:
            fallback_stats = non_paper_stats or {
                "text_len": float(len((pymupdf_text or "").strip())),
                "garbled_ratio": _estimate_pdf_text_garbled_ratio(pymupdf_text),
                "marker_hits": float(_count_non_paper_mineru_markers(pymupdf_text)),
            }
            print(
                "  ℹ️  non-paper MinerU skipped: no heuristic trigger "
                f"(len={int(fallback_stats.get('text_len', 0))}, "
                f"garbled_ratio={fallback_stats.get('garbled_ratio', 0.0):.3f}, "
                f"marker_hits={int(fallback_stats.get('marker_hits', 0))})"
            )

    if _is_good_pdf_text(pymupdf_text):
        if mineru_attempted:
            print("  ✅ PDF 最终采用链路: PyMuPDF4LLM（MinerU 已尝试并回退）")
        else:
            print("  ✅ PDF 最终采用链路: PyMuPDF4LLM")
        return pymupdf_text

    ocr_text = extract_text_from_pdf_via_ocr(filepath)
    if _is_good_pdf_text(ocr_text) or ocr_text:
        print("  ✅ PDF 最终采用链路: OCR fallback")
        return ocr_text

    if best_text:
        print("  ℹ️  PDF 文本提取返回最佳可得结果")
    return best_text


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self._skip_depth += 1
        elif tag in {"p", "div", "section", "article", "li", "br", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag in {"p", "div", "section", "article", "li", "br", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip_depth and data and data.strip():
            self.parts.append(data)

    def get_text(self):
        text = html.unescape(" ".join(self.parts))
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"( [。！？.!?])", r"\1", text)
        return text.strip()


def _html_to_text(raw: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(raw)
    return parser.get_text()


def _extract_html_heading(raw: str) -> str:
    for pattern in (
        r"<h1[^>]*>(.*?)</h1>",
        r"<h2[^>]*>(.*?)</h2>",
        r"<title[^>]*>(.*?)</title>",
    ):
        m = re.search(pattern, raw, re.IGNORECASE | re.DOTALL)
        if m:
            text = re.sub(r"<[^>]+>", " ", m.group(1))
            text = html.unescape(re.sub(r"\s+", " ", text)).strip()
            if text:
                return text
    return ""


def _epub_member_basename(name: str) -> str:
    base = Path(name).stem
    base = re.sub(r"^\d+[_-]?", "", base)
    base = re.sub(r"^[A-Za-z0-9]+_", "", base)
    return base.strip()


def _is_probably_epub_chapter(name: str, raw: str, text: str) -> bool:
    base = _epub_member_basename(name).lower()
    if any(token in base for token in EPUB_CHAPTER_SKIP_TOKENS):
        return False
    if len(text) < 400:
        return False
    heading = _extract_html_heading(raw).lower()
    if heading in EPUB_CHAPTER_SKIP_TOKENS:
        return False
    if base.startswith("chapter") or re.fullmatch(r"chapter\d+", base):
        return True
    if re.match(r"^[ivxlcdm]+\b", heading):
        return True
    if heading.startswith("chapter "):
        return True
    if base in {"preface", "foreword", "prologue", "introduction", "epilogue", "afterword"}:
        return True
    return False


def extract_text_from_epub(filepath: str) -> str:
    """Extract text from EPUB/MOBI-like zipped content with pure Python fallback."""
    try:
        with zipfile.ZipFile(filepath) as zf:
            members = [
                name for name in zf.namelist()
                if name.lower().endswith((".xhtml", ".html", ".htm", ".xml"))
                and not name.startswith("__MACOSX/")
            ]
            if not members:
                return ""
            chunks = []
            for name in sorted(members):
                try:
                    raw = zf.read(name).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                text = _html_to_text(raw)
                if len(text) >= 50:
                    chunks.append(text)
                if sum(len(c) for c in chunks) >= 50000:
                    break
            return "\n\n".join(chunks)[:50000]
    except zipfile.BadZipFile:
        return ""
    except Exception:
        return ""


def extract_epub_chapters(filepath: str) -> list[dict]:
    """Extract chapter-like sections from EPUB for chapter-level companion notes."""
    chapters = []
    try:
        with zipfile.ZipFile(filepath) as zf:
            members = [
                name for name in zf.namelist()
                if name.lower().endswith((".xhtml", ".html", ".htm", ".xml"))
                and not name.startswith("__MACOSX/")
            ]
            for name in sorted(members):
                try:
                    raw = zf.read(name).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                text = _html_to_text(raw)
                if not _is_probably_epub_chapter(name, raw, text):
                    continue
                title = _extract_html_heading(raw) or _epub_member_basename(name).replace("_", " ").strip()
                text = text[:MAX_CHAPTER_CHARS].strip()
                if not text:
                    continue
                chapter_no = len(chapters) + 1
                slug = sanitize_filename(f"{chapter_no:02d}-{title}")[:80]
                chapters.append({
                    "index": chapter_no,
                    "member": name,
                    "title": title,
                    "slug": slug,
                    "text": text,
                })
                if len(chapters) >= MAX_BOOK_CHAPTERS:
                    break
    except zipfile.BadZipFile:
        return []
    except Exception:
        return []
    return chapters


def _normalize_pdf_heading(line: str) -> str:
    text = re.sub(r"\s+", " ", (line or "").strip())
    text = re.sub(r"^#+\s*", "", text).strip()
    text = re.sub(r"^[\-\*•]+", "", text).strip()
    text = re.sub(r"\*+$", "", text).strip()
    return text


def _format_pdf_explicit_heading(kind: str, label: str, subtitle: str = "") -> str:
    base = f"{'Chapter' if kind == 'chapter' else 'Part'} {label.upper()}"
    cleaned = re.sub(r"\s+", " ", (subtitle or "").strip(" :-"))
    cleaned = re.sub(r"^\((.+)\)$", r"\1", cleaned).strip()
    cleaned = re.sub(r"\s*\[[^\]]+\]\.?$", "", cleaned).strip()
    if cleaned:
        return f"{base}: {cleaned}"
    return base


def _looks_like_pdf_sentence_tail(text: str) -> bool:
    candidate = re.sub(r"\s*\[[^\]]+\]\.?$", "", (text or "").strip())
    lower = candidate.lower()
    if len(candidate.split()) > 16:
        return True
    if re.search(
        r"\b(now|describes?|discusses?|explains?|shows?|presents?|covers?|focuses?|introduces?|is|are|was|were|has|have|can|may|should|will)\b",
        lower,
    ):
        return True
    if re.search(r"[a-z]{3,}\s+[a-z]{3,}\s+[a-z]{3,}", candidate):
        return True
    return False


def _match_pdf_explicit_chapter_heading(line: str) -> tuple[str, str] | None:
    text = _normalize_pdf_heading(line)
    if not text:
        return None

    chapter_match = re.match(r"^chapter\s+([0-9]+|[ivxlcdm]+)\b(?:\s*[:.\-]\s*|\s+)?(.*)$", text, re.I)
    if chapter_match:
        label = chapter_match.group(1)
        subtitle = chapter_match.group(2).strip()
        if subtitle and _looks_like_pdf_sentence_tail(subtitle):
            return None
        return ("chapter", _format_pdf_explicit_heading("chapter", label, subtitle))

    part_match = re.match(r"^part\s+([0-9]+|[ivxlcdm]+)\b(?:\s*[:.\-]\s*|\s+)?(.*)$", text, re.I)
    if part_match:
        label = part_match.group(1)
        subtitle = part_match.group(2).strip()
        if subtitle and _looks_like_pdf_sentence_tail(subtitle):
            return None
        return ("part", _format_pdf_explicit_heading("part", label, subtitle))

    numbered_match = re.match(r"^(\d+)\.\s+(.+)$", text)
    if numbered_match:
        subtitle = numbered_match.group(2).strip()
        word_count = len(subtitle.split())
        if subtitle and word_count <= 14 and any(ch.isupper() for ch in subtitle) and not _looks_like_pdf_sentence_tail(subtitle):
            return ("chapter", f"{numbered_match.group(1)}. {subtitle}")

    return None


def _looks_like_pdf_toc_entry(line: str) -> bool:
    text = _normalize_pdf_heading(line)
    if not text or len(text) > 120:
        return False
    if _match_pdf_explicit_chapter_heading(text):
        return True
    if re.match(r"^(chapter|part)\s+([0-9]+|[ivxlcdm]+)\b.*\d+$", text, re.I):
        return True
    return False


def _looks_like_substantial_pdf_paragraph(line: str) -> bool:
    text = _normalize_pdf_heading(line)
    if not text:
        return False
    return len(text) >= 100 or (len(text.split()) >= 18 and bool(re.search(r"[,.:;]", text)))


def _line_has_pdf_page_break_marker(line: str) -> bool:
    text = _normalize_pdf_heading(line)
    if not text:
        return False
    return text == "---" or bool(re.fullmatch(r"[-_*=]{3,}", text))


def _has_substantial_body_after(lines: list[str], normalized_lines: list[str], idx: int) -> bool:
    chars = 0
    non_empty = 0
    heading_continuations = 0
    for j in range(idx + 1, min(len(lines), idx + 20)):
        candidate = normalized_lines[j]
        if not candidate or re.fullmatch(r"\d+", candidate):
            continue
        if _match_pdf_explicit_chapter_heading(candidate):
            break
        if _is_probably_pdf_book_heading(candidate):
            if non_empty == 0 and heading_continuations < 2 and len(candidate) <= 80:
                heading_continuations += 1
                continue
            break
        non_empty += 1
        chars += len(candidate)
        if _looks_like_substantial_pdf_paragraph(candidate):
            return True
        if non_empty >= 3 and chars >= MIN_CHAPTER_TEXT:
            return True
    return False


def _detect_and_skip_toc(lines: list[str], normalized_lines: list[str]) -> int:
    """Return the index where actual content starts, skipping dense TOC blocks."""
    scan_limit = min(len(lines), 200)
    toc_refs = [idx for idx in range(scan_limit) if _looks_like_pdf_toc_entry(normalized_lines[idx])]
    if len(toc_refs) < 5:
        return 0

    run_start = run_end = toc_refs[0]
    best_start = best_end = toc_refs[0]
    best_count = 1
    count = 1
    for idx in toc_refs[1:]:
        if idx - run_end <= 5:
            run_end = idx
            count += 1
        else:
            if count > best_count:
                best_start, best_end, best_count = run_start, run_end, count
            run_start = run_end = idx
            count = 1
    if count > best_count:
        best_start, best_end, best_count = run_start, run_end, count
    if best_count < 3:
        return 0

    search_start = best_end + 1
    blank_streak = 0
    for idx in range(search_start, min(len(lines), search_start + 120)):
        line = normalized_lines[idx]
        if not line:
            blank_streak += 1
            continue
        if _line_has_pdf_page_break_marker(line):
            blank_streak = 0
            continue
        if _is_probably_pdf_book_heading(line) and _has_substantial_body_after(lines, normalized_lines, idx):
            return idx
        if (blank_streak >= 2 or idx == search_start) and _looks_like_substantial_pdf_paragraph(line):
            probe = idx
            while probe > 0 and probe - 1 > best_end and normalized_lines[probe - 1]:
                prev = normalized_lines[probe - 1]
                if _is_probably_pdf_book_heading(prev):
                    return probe - 1
                if len(prev) > 100:
                    break
                probe -= 1
            return idx
        blank_streak = 0

    return search_start if search_start < len(lines) else 0


def _is_pdf_heading_continuation(line: str) -> bool:
    text = _normalize_pdf_heading(line)
    if not text or len(text) > 100:
        return False
    plain = re.sub(r"^\((.+)\)$", r"\1", text).strip()
    if not plain:
        return False
    if _looks_like_pdf_sentence_tail(plain):
        return False
    if text.startswith("(") and text.endswith(")"):
        return True
    if plain == plain.title() or plain.isupper():
        return True
    return len(plain.split()) <= 12 and bool(re.fullmatch(r"[A-Za-z0-9 '&/,\-]+", plain))


def _combine_pdf_heading_title(primary_title: str, extra_lines: list[str]) -> str:
    title = primary_title.strip()
    extras = []
    for extra in extra_lines:
        cleaned = _normalize_pdf_heading(extra)
        if not cleaned:
            continue
        cleaned = re.sub(r"^\((.+)\)$", r"\1", cleaned).strip()
        cleaned = re.sub(r"\s*\[[^\]]+\]\.?$", "", cleaned).strip()
        if not cleaned:
            continue
        if title.startswith(("Chapter ", "Part ")) and not re.search(r":\s*", title):
            title = f"{title}: {cleaned}"
        else:
            extras.append(cleaned)
    if extras:
        title = f"{title} {' '.join(extras)}".strip()
    return re.sub(r"\s+", " ", title)


def _is_probably_pdf_book_heading(line: str) -> bool:
    text = _normalize_pdf_heading(line)
    lower = text.lower()
    if len(text) < 4 or len(text) > 120:
        return False
    if any(token in lower for token in ("......", " . . . ", "\t")):
        return False
    if lower in EPUB_CHAPTER_SKIP_TOKENS:
        return False
    if _match_pdf_explicit_chapter_heading(text):
        return True
    if re.match(r"^[ivxlcdm]+\.\s+[A-Z]", text):
        return True
    if re.match(r"^[ivxlcdm]+\s+[A-Z]", text):
        return True
    if lower in {"preface", "foreword", "prologue", "introduction", "afterword", "epilogue"}:
        return True
    if len(text.split()) <= 10 and text == text.title() and not re.search(r"[.!?]$", text):
        return True
    if len(text.split()) <= 8 and text.isupper() and any(ch.isalpha() for ch in text):
        return True
    return False


def _finalize_pdf_book_chapters(chapters: list[dict]) -> list[dict]:
    finalized = []
    i = 0
    while i < len(chapters):
        chapter = dict(chapters[i])
        if chapter["title"].startswith("Part ") and i + 1 < len(chapters):
            merged_next = dict(chapters[i + 1])
            merged_next["text"] = f"{chapter['text'].rstrip()}\n\n{merged_next['text'].lstrip()}"[:MAX_CHAPTER_CHARS]
            chapters[i + 1] = merged_next
            i += 1
            continue
        finalized.append(chapter)
        i += 1

    for idx, chapter in enumerate(finalized, start=1):
        chapter["index"] = idx
        chapter["slug"] = sanitize_filename(f"{idx:02d}-{chapter['title']}")[:80]
    return finalized


def extract_pdf_book_chapters(text: str) -> list[dict]:
    """Split book-like PDF text into chapter-ish chunks using heading heuristics."""
    lines = [line.rstrip() for line in (text or "").splitlines()]
    chapters = []
    current_title = ""
    current_lines = []
    normalized_lines = [_normalize_pdf_heading(line) for line in lines]
    content_start = _detect_and_skip_toc(lines, normalized_lines)
    if content_start > 0:
        lines = lines[content_start:]
        normalized_lines = normalized_lines[content_start:]
    has_explicit_chapter_markers = any(_match_pdf_explicit_chapter_heading(ln) for ln in normalized_lines)
    prefer_markdown_headings = sum(1 for raw in lines if re.match(r"^#\s+", raw.lstrip())) >= 3
    front_matter_headings = {"preface", "foreword", "prologue", "introduction", "afterword", "epilogue"}
    seen_explicit_heading = False

    def flush_current(force: bool = False):
        nonlocal current_title, current_lines
        chunk = "\n".join(current_lines).strip()
        if current_title and len(chunk) >= MIN_CHAPTER_TEXT:
            chapter_no = len(chapters) + 1
            chapters.append({
                "index": chapter_no,
                "title": current_title,
                "slug": sanitize_filename(f"{chapter_no:02d}-{current_title}")[:80],
                "text": chunk[:MAX_CHAPTER_CHARS],
            })
        elif current_title and chunk and chapters and not force:
            merged = f"{chapters[-1]['text'].rstrip()}\n\n{chunk}".strip()
            chapters[-1]["text"] = merged[:MAX_CHAPTER_CHARS]
        current_title = ""
        current_lines = []

    def start_new_chapter(title: str):
        nonlocal current_title, current_lines
        flush_current()
        current_title = title.strip()
        current_lines = [current_title]

    i = 0
    while i < len(lines):
        raw_line = lines[i]
        line = normalized_lines[i]
        line_has_heading_marker = bool(re.match(r"^#\s+", raw_line.lstrip()))
        if not line:
            if current_lines:
                current_lines.append("")
            i += 1
            continue

        explicit_heading = _match_pdf_explicit_chapter_heading(line)
        explicit_heading_allowed = (not prefer_markdown_headings) or line_has_heading_marker
        if explicit_heading and explicit_heading_allowed and _has_substantial_body_after(lines, normalized_lines, i):
            seen_explicit_heading = True
            title_extras = []
            j = i + 1
            while j < len(lines):
                nxt = normalized_lines[j]
                if not nxt:
                    if title_extras:
                        break
                    j += 1
                    continue
                if len(nxt) > 120 or re.fullmatch(r"\d+", nxt):
                    break
                if _match_pdf_explicit_chapter_heading(nxt):
                    break
                if _looks_like_substantial_pdf_paragraph(nxt):
                    break
                if not _is_pdf_heading_continuation(nxt):
                    break
                if _is_probably_pdf_book_heading(nxt) and title_extras:
                    break
                title_extras.append(nxt)
                j += 1
                if len(title_extras) >= 2:
                    break
            start_new_chapter(_combine_pdf_heading_title(explicit_heading[1], title_extras))
            i = j
            if len(chapters) >= MAX_BOOK_CHAPTERS:
                break
            continue

        if has_explicit_chapter_markers:
            lower = line.lower()
            if (
                (not prefer_markdown_headings or line_has_heading_marker)
                and not seen_explicit_heading
                and lower in front_matter_headings
                and _has_substantial_body_after(lines, normalized_lines, i)
            ):
                current_len = len("\n".join(current_lines).strip())
                if not current_title or current_len >= MIN_CHAPTER_TEXT:
                    start_new_chapter(line.title() if line.islower() else line)
                    i += 1
                    continue
            if current_title:
                current_lines.append(line)
            i += 1
            continue

        if ((not prefer_markdown_headings) or line_has_heading_marker) and _is_probably_pdf_book_heading(line) and _has_substantial_body_after(lines, normalized_lines, i):
            start_new_chapter(line)
            if len(chapters) >= MAX_BOOK_CHAPTERS:
                break
            i += 1
            continue
        if current_title:
            current_lines.append(line)
        i += 1

    if len(chapters) < MAX_BOOK_CHAPTERS:
        flush_current(force=True)
    return _finalize_pdf_book_chapters(chapters)


def _debug_pdf_book_chapters(source_path: str, chapters: list[dict]) -> None:
    if os.environ.get("ATLAS_DEBUG_BOOK_CHAPTERS", "").lower() not in {"1", "true", "yes", "on"}:
        return
    source_name = Path(source_path).name if source_path else "<unknown>"
    print(f"  🧪 PDF chapter detection for {source_name}: {len(chapters)} chapters")
    for chapter in chapters:
        print(f"     - {chapter['index']:02d}. {chapter['title'][:70]} ({len(chapter['text'])} chars)")


def relocate_literature_note(note_path: str, file_type: str) -> str:
    """Move an existing literature note into the canonical subdir if needed."""
    current = Path(note_path)
    subdir_map = {
        "paper": "Papers",
        "book": "Books",
        "article": "Articles",
        "repo": "Repos",
        "podcast": "Podcasts",
        "tweet": "Tweets",
    }
    desired_dir = Path(CONFIG["literature_dir"]) / subdir_map.get(file_type, "Articles")
    desired_dir.mkdir(parents=True, exist_ok=True)
    desired_path = desired_dir / current.name
    if current.parent == desired_dir:
        return str(current)
    try:
        shutil.move(str(current), str(desired_path))
        return str(desired_path)
    except Exception:
        return str(current)


def extract_text_from_image(filepath: str) -> str:
    """Extract OCR text from image files via local tesseract."""
    real_path = os.path.realpath(filepath)
    try:
        result = subprocess.run(
            ["tesseract", real_path, "stdout", "-l", "eng+chi_sim", "--psm", "6"],
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            result = subprocess.run(
                ["tesseract", real_path, "stdout", "-l", "eng", "--psm", "6"],
                capture_output=True,
                timeout=120,
            )
        if result.returncode == 0:
            text = result.stdout.decode("utf-8", errors="ignore")
            text = re.sub(r"\s+", " ", text).strip()
            return text[:50000]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


def extract_text_from_pdf_via_ocr(filepath: str, max_pages: int = 5) -> str:
    """OCR fallback for scanned PDFs using pdftoppm + tesseract."""
    temp_dir = tempfile.mkdtemp(prefix="atlas-pdf-ocr-", dir=CONFIG["temp_dir"])
    try:
        prefix = os.path.join(temp_dir, "page")
        convert = subprocess.run(
            ["pdftoppm", "-f", "1", "-l", str(max_pages), "-png", filepath, prefix],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if convert.returncode != 0:
            return ""
        texts = []
        for image_path in sorted(Path(temp_dir).glob("page-*.png")):
            text = extract_text_from_image(str(image_path))
            if text:
                texts.append(text)
            if sum(len(t) for t in texts) >= 50000:
                break
        return "\n\n".join(texts)[:50000]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ── Locked File Handling ──────────────────────────────────────────────────

def copy_with_retry(src_path, retries=None, delays=None):
    """
    Copy file to temp dir with exponential backoff.
    Returns (temp_path, success).
    """
    if retries is None:
        retries = CONFIG["max_retries"]
    if delays is None:
        delays = CONFIG["retry_delays"]

    os.makedirs(CONFIG["temp_dir"], exist_ok=True)
    src_suffix = Path(src_path).suffix
    src_stem = Path(src_path).stem

    def _make_temp_path():
        fd, temp_path = tempfile.mkstemp(
            prefix=f"{sanitize_filename(src_stem)}-",
            suffix=src_suffix,
            dir=CONFIG["temp_dir"],
        )
        os.close(fd)
        return temp_path

    def _stream_copy(src, dst):
        with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
            shutil.copyfileobj(fsrc, fdst, length=1024 * 1024)

    def _copy_once(src, dst):
        try:
            shutil.copy2(src, dst)
            return
        except (OSError, IOError, PermissionError) as e:
            # Dropbox/iCloud file providers can fail with EDEADLK on copy2.
            # Fall back to a plain stream copy without metadata to avoid clone/stat issues.
            if getattr(e, "errno", None) != 11:
                raise
        _stream_copy(src, dst)

    for i in range(retries):
        temp_path = _make_temp_path()
        try:
            _copy_once(src_path, temp_path)
            return temp_path, True
        except (OSError, IOError, PermissionError) as e:
            try:
                os.remove(temp_path)
            except OSError:
                pass
            if i < retries - 1:
                delay = delays[i] if i < len(delays) else 16
                print(f"  ⚠️  Copy failed ({e}), retrying in {delay}s... ({i+1}/{retries})")
                time.sleep(delay)
            else:
                print(f"  ❌ Copy failed after {retries} attempts: {e}")
                return None, False

    return None, False


# ── Concept & Atomic Extraction ──────────────────────────────────────────

UPPERCASE_TERM = re.compile(r"\b[A-Z]{2,}(?:[-_][A-Z0-9]+)*\b")
QUOTED_TERM = re.compile(r"[“\"「『]([\u4e00-\u9fffA-Za-z0-9\-\s]{2,40})[”\"」』]")
EN_NOUN_PHRASE = re.compile(r"\b([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+){1,3})\b")
ZH_TERM = re.compile(r"[\u4e00-\u9fff]{2,8}")
ATOM_SENT_SPLIT = re.compile(r"(?<=[。！？.!?])\s+|\n+")
ATOM_PREFIX = ("发现", "结果表明", "实验证明", "关键洞察", "important")
FREQUENCY_THRESHOLD = 3


def _normalize_term(term: str) -> str:
    return re.sub(r"\s+", " ", (term or "").strip())


def _load_note_text(path: str) -> str:
    try:
        ext = Path(path).suffix.lower()
        if ext in {".md", ".markdown", ".txt"}:
            return Path(path).read_text(encoding="utf-8", errors="ignore")
        if ext == ".pdf":
            return extract_text_from_pdf(path)
        if ext in {".epub", ".mobi"}:
            return extract_text_from_epub(path)
        if ext in IMAGE_EXTENSIONS:
            return extract_text_from_image(path)
    except Exception:
        return ""
    return ""


def extract_concept_candidates(text: str) -> list[str]:
    """Rule-based concept extraction: uppercase terms, quoted Chinese terms, frequent noun phrases."""
    if not text:
        return []

    freq: dict[str, int] = {}

    # 1) Uppercase English terms
    for m in UPPERCASE_TERM.findall(text):
        t = _normalize_term(m)
        if len(t) >= 2:
            freq[t] = freq.get(t, 0) + 1

    # 2) Quoted Chinese/English terms
    for m in QUOTED_TERM.findall(text):
        t = _normalize_term(m)
        if len(t) >= 2:
            freq[t] = freq.get(t, 0) + 1

    # 3) Frequent noun phrases (English)
    for m in EN_NOUN_PHRASE.findall(text):
        t = _normalize_term(m)
        if len(t) >= 6:
            freq[t] = freq.get(t, 0) + 1

    # 3) Frequent noun-like Chinese terms
    for m in ZH_TERM.findall(text):
        t = _normalize_term(m)
        if len(t) >= 2:
            freq[t] = freq.get(t, 0) + 1

    # Keep >=3 and filter noisy tokens
    candidates = []
    for term, count in freq.items():
        if count < FREQUENCY_THRESHOLD:
            continue
        if term.lower() in {"abstract", "introduction", "results", "method", "figure", "table"}:
            continue
        candidates.append((term, count))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return [term for term, _ in candidates[:15]]


def _extract_title_from_frontmatter(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        if not content.startswith("---"):
            return path.stem
        parts = content.split("---", 2)
        if len(parts) < 3:
            return path.stem
        for line in parts[1].splitlines():
            if line.strip().startswith("title:"):
                return line.split(":", 1)[1].strip().strip('"\'')
    except Exception:
        pass
    return path.stem


def find_concept_note_path(concept_title: str):
    """Find concept note by filename or frontmatter title."""
    concepts_dir = Path(CONFIG["concepts_dir"]).expanduser()
    safe_name = sanitize_filename(concept_title)

    direct = concepts_dir / f"{safe_name}.md"
    if direct.exists():
        return direct

    for p in concepts_dir.glob("*.md"):
        if _extract_title_from_frontmatter(p).strip().lower() == concept_title.strip().lower():
            return p
    return None


def _upsert_list_item_in_frontmatter(note_path: Path, key: str, new_item: str) -> None:
    """Append item to YAML list key in frontmatter if absent (best-effort, no external deps)."""
    try:
        raw = note_path.read_text(encoding="utf-8", errors="ignore")
        if not raw.startswith("---"):
            return
        parts = raw.split("---", 2)
        if len(parts) < 3:
            return

        fm_lines = parts[1].splitlines()
        body = parts[2].lstrip("\n")

        # Already present
        if re.search(rf"^\s*-\s+['\"]?{re.escape(new_item)}['\"]?\s*$", "\n".join(fm_lines), re.MULTILINE):
            return

        key_idx = None
        for i, ln in enumerate(fm_lines):
            if ln.strip().startswith(f"{key}:"):
                key_idx = i
                break

        if key_idx is None:
            fm_lines.append(f"{key}:")
            fm_lines.append(f'  - "{new_item}"')
        else:
            # inline list: key: [a, b]
            line = fm_lines[key_idx]
            if "[" in line and "]" in line:
                prefix, inline = line.split(":", 1)
                val = inline.strip().strip("[]")
                items = [x.strip().strip('"\'') for x in val.split(",") if x.strip()]
                if new_item not in items:
                    items.append(new_item)
                quoted_items = ", ".join('"{}"'.format(x) for x in items)
                fm_lines[key_idx] = f"{prefix}: [{quoted_items}]"
            else:
                insert_at = key_idx + 1
                while insert_at < len(fm_lines) and (fm_lines[insert_at].startswith("  -") or fm_lines[insert_at].strip() == ""):
                    insert_at += 1
                fm_lines.insert(insert_at, f'  - "{new_item}"')

        rebuilt = "---\n" + "\n".join(fm_lines).rstrip() + "\n---\n\n" + body
        note_path.write_text(rebuilt, encoding="utf-8")
    except Exception as e:
        print(f"    ⚠️  Frontmatter list update failed ({note_path.name}): {e}")


def create_or_update_concept_node(concept_title, source_note_wikilink,
                                source_url="", definition=None,
                                related_concepts=None, category=None,
                                summary=None, key_findings=None,
                                source_title=None):
    """Create concept node if absent; otherwise append source link to related.
    
    Args:
        concept_title: 概念名称
        source_note_wikilink: 来源文献笔记的 wikilink
        source_url: 来源 URL
        definition: LLM 生成的概念定义（可选）
        related_concepts: 相关概念列表（可选）
        category: 概念分类（可选）
        summary: 新文献摘要（可选，用于概念合并）
        key_findings: 新文献关键发现（可选，用于概念合并）
        source_title: 新文献标题（可选，用于概念合并显示）
    """
    if not is_valid_concept_name(concept_title):
        print(f"    ⏭️  跳过噪声概念: {concept_title}")
        return None

    concepts_dir = Path(CONFIG["concepts_dir"]).expanduser()
    concepts_dir.mkdir(parents=True, exist_ok=True)

    concept_path = find_concept_note_path(concept_title)
    if concept_path is None:
        safe_name = sanitize_filename(concept_title)
        concept_path = concepts_dir / f"{safe_name}.md"
        now = datetime.now(TZ)
        sources_items = [f"[[{source_note_wikilink}]]"]
        if source_url:
            sources_items.append(f"[{source_url}]({source_url})")

        def_section = definition if definition else f"{concept_title} 是一个待完善的概念节点。"
        
        related_section = ""
        valid_related = [rc for rc in (related_concepts or []) if is_valid_concept_name(rc)]
        if valid_related:
            related_section = "\n".join(f"- {rc}" for rc in valid_related)
        else:
            related_section = "<!-- TODO -->"

        cat_section = ""
        if category:
            cat_section = f"\n分类：{category}"

        content = (
            "---\n"
            f'title: "{concept_title}"\n'
            "type: concept\n"
            f"date: {now.strftime('%Y-%m-%d')}\n"
            "status: active\n"
            f"updated: {now.strftime('%Y-%m-%d')}\n"
            "sources:\n"
            + "\n".join(f'  - "{s}"' for s in sources_items)
            + "\nrelated:\n"
            f'  - "[[{source_note_wikilink}]]"\n'
            "tags:\n"
            "  - concept\n"
            f"created: {now.strftime('%Y-%m-%d')}\n"
            "---\n\n"
            f"# {concept_title}\n\n"
            "## 定义\n\n"
            f"{def_section}\n\n"
            f"{cat_section}\n\n"
            "## 研究进展\n\n"
            "<!-- 后续文献发现将通过 LLM 合并追加到此处 -->\n\n"
            "## 待验证（矛盾）\n\n"
            "<!-- 矛盾信息将在此汇总 -->\n\n"
            "## 跨领域关联\n\n"
            f"{related_section}\n\n"
            "## 见于\n\n"
            f"- [[{source_note_wikilink}]]\n"
        )
        try:
            concept_path.write_text(content, encoding="utf-8")
            print(f"    ✅ 概念节点创建: {concept_path.name}")
        except Exception as e:
            print(f"    ❌ 概念节点创建失败 ({concept_title}): {e}")
            return None
    else:
        print(f"    ♻️  概念已存在，更新 related: {concept_path.name}")
        _upsert_list_item_in_frontmatter(concept_path, "related", f"[[{source_note_wikilink}]]")
        if source_url:
            _upsert_list_item_in_frontmatter(concept_path, "sources", f"[{source_url}]({source_url})")
        # 如果有 LLM 生成的定义且现有笔记是 TODO，则更新
        if definition:
            existing = concept_path.read_text(encoding="utf-8")
            if "待完善的概念节点" in existing:
                existing = existing.replace(
                    f"{concept_title} 是一个待完善的概念节点。",
                    definition
                )
                concept_path.write_text(existing, encoding="utf-8")
        # 追加 related concepts
        if related_concepts:
            for rc in related_concepts:
                if not is_valid_concept_name(rc):
                    continue
                rc_slug = sanitize_filename(rc)
                _upsert_list_item_in_frontmatter(concept_path, "related", f"[[{rc_slug}]]")

        # 概念合并：将新文献的摘要和发现合并到已有概念页面
        if definition or summary or key_findings:
            merge_src_title = source_title or source_note_wikilink
            merge_summary = summary or ""
            merge_findings = key_findings or ""
            if isinstance(merge_findings, list):
                merge_findings = "\n".join(f"- {f}" for f in merge_findings)
            merge_concept_with_new_source(
                concept_path,
                new_source_title=merge_src_title,
                new_source_summary=merge_summary,
                new_source_key_findings=merge_findings,
            )

    return concept_path

def extract_atomic_points(text: str, max_items: int = 8) -> list[str]:
    """Extract key findings sentences by prefix rules."""
    if not text:
        return []

    candidates: list[str] = []
    for seg in ATOM_SENT_SPLIT.split(text):
        s = re.sub(r"\s+", " ", seg.strip())
        if len(s) < 12 or len(s) > 220:
            continue
        lower = s.lower()
        if any(lower.startswith(p.lower()) for p in ATOM_PREFIX):
            candidates.append(s)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for s in candidates:
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)
        if len(unique) >= max_items:
            break
    return unique


def find_existing_atomic_note(source_note_wikilink: str, title: str = "", sentence: str = ""):
    """Find an existing atomic note for the same source and same title/content."""
    permanent_dir = Path(CONFIG["permanent_dir"]).expanduser()
    normalized_title = normalize_text_key(title)
    normalized_sentence = normalize_text_key(sentence)

    for path in sorted(permanent_dir.glob("*.md"), reverse=True):
        text = path.read_text(encoding="utf-8", errors="ignore")
        fm, body = parse_frontmatter(text)
        up = normalize_text_key(str(fm.get("up", "")))
        if source_note_wikilink.lower() not in up:
            continue

        existing_title = normalize_text_key(str(fm.get("title", "")))
        existing_body = normalize_text_key(body)
        if normalized_title and existing_title == normalized_title:
            return path
        if normalized_sentence and existing_body == normalized_sentence:
            return path

    return None


def create_atomic_note(sentence, source_note_wikilink, title=None):
    """Create one permanent atomic note with source backlink.
    
    Args:
        sentence: 原子笔记内容（自包含）
        source_note_wikilink: 来源文献笔记的 wikilink
        title: 可选的标题（LLM 生成）
    """
    try:
        out_dir = Path(CONFIG["permanent_dir"]).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)

        existing = find_existing_atomic_note(
            source_note_wikilink=source_note_wikilink,
            title=title or "",
            sentence=sentence,
        )
        if existing is not None:
            return existing

        now = datetime.now(TZ)
        display_title = title if title else (sentence[:48] + ("..." if len(sentence) > 48 else ""))
        stem_seed = sanitize_filename(display_title[:42])
        filename = f"{now.strftime('%Y%m%d%H%M%S')}-{stem_seed}.md"
        path = out_dir / filename
        if path.exists():
            path = out_dir / f"{path.stem}-dup.md"

        content = (
            "---\n"
            f'title: "{display_title}"\n'
            "type: zettel\n"
            f"date: {now.strftime('%Y-%m-%d')}\n"
            "tags: [atomic, literature]\n"
            f'up: "[[{source_note_wikilink}]]"\n'
            f"created: {now.strftime('%Y-%m-%d')}\n"
            "status: active\n"
            "---\n\n"
            f"# {display_title}\n\n"
            f"{sentence}\n"
        )
        path.write_text(content, encoding="utf-8")
        return path
    except Exception as e:
        print(f"    ❌ 原子笔记创建失败: {e}")
        return None



def _append_atom_links_to_note(note_path):
    """将最新创建的原子笔记链接写回文献笔记，避免重复追加区块。"""
    try:
        note_path = Path(note_path)
        permanent_dir = Path(CONFIG["permanent_dir"]).expanduser()
        atoms = []
        for f in sorted(permanent_dir.glob("*.md"), reverse=True):
            text = f.read_text(encoding="utf-8", errors="ignore")
            # 检查 up 字段是否指向该文献
            note_stem = note_path.stem
            if note_stem in text:
                fm, _ = parse_frontmatter(text)
                up = fm.get("up", "")
                if note_stem in str(up):
                    title = fm.get("title", f.stem)
                    wikilink = f"3-Permanent/{f.stem}"
                    atoms.append(f"- [[{wikilink}|{title}]]")
            if len(atoms) >= 10:
                break

        if atoms:
            section = "\n---\n\n## 原子笔记（自动提炼）\n\n"
            section += "\n".join(atoms) + "\n"
            note_text = note_path.read_text(encoding="utf-8", errors="ignore")
            note_text = re.sub(
                r"\n---\n\n## 原子笔记（自动提炼）\n\n.*\Z",
                "",
                note_text,
                flags=re.S,
            ).rstrip()
            note_path.write_text(note_text + section, encoding="utf-8")
    except Exception as e:
        print(f"    ⚠️ 原子笔记链接追加失败: {e}")

def _upsert_concept_related(concept_slug: str, wikilink: str):
    """在概念笔记的 related 列表中追加链接"""
    concepts_dir = Path(CONFIG["concepts_dir"]).expanduser()
    note_path = concepts_dir / f"{concept_slug}.md"
    if not note_path.exists():
        return
    _upsert_list_item_in_frontmatter(note_path, "related", wikilink)


def _append_concept_links_to_note(note_path, concepts):
    """将概念链接追加到文献笔记的 ## Related 区"""
    try:
        text = open(note_path, "r", encoding="utf-8").read()
        concept_links = []
        for c in filter_concept_payloads(concepts):
            name = c.get("name", "")
            slug = sanitize_filename(name)
            definition = c.get("definition", "")
            link = f"- [[2-Concepts/{slug}|{name}]]"
            if definition:
                link += f" — {definition}"
            concept_links.append(link)

        # 替换 <!-- TODO --> 为实际链接
        if "<!-- TODO: 添加关联笔记 -->" in text:
            replacement = "\n".join(concept_links)
            text = text.replace("<!-- TODO: 添加关联笔记 -->", replacement)
            with open(note_path, "w", encoding="utf-8") as f:
                f.write(text)
    except Exception as e:
        print(f"    ⚠️ 概念链接写入失败: {e}")


def post_process_literature_note(note_path: str, extraction_text: str, source_url: str = "") -> tuple[int, int]:
    """Run concept extraction + atomic extraction for a newly created literature note.
    
    Uses LLM if available, falls back to regex extraction.
    """
    concept_count = 0
    atom_count = 0

    try:
        note_rel = os.path.relpath(note_path, CONFIG["atlas_vault"])
        source_note_wikilink = note_rel[:-3] if note_rel.endswith(".md") else note_rel
        note_name = Path(note_path).stem
        llm_result = pop_cached_llm_result(note_name)

        if LLM_AVAILABLE and llm_result:
            # LLM 驱动模式：使用已缓存的 LLM 结果
            # 概念提取（两轮：先全部创建，再建立互联）
            created_concepts = {}  # name -> wikilink
            filtered_concepts = filter_concept_payloads(llm_result.get("concepts", []))
            for concept_data in filtered_concepts:
                concept_name = concept_data.get("name", "")
                if not concept_name:
                    continue
                definition = concept_data.get("definition", "")
                related = concept_data.get("related_concepts", [])
                category = concept_data.get("category", "")

                cp = create_or_update_concept_node(
                    concept_name, source_note_wikilink,
                    definition=definition,
                    category=category,
                    source_url=source_url,
                    summary=llm_result.get("summary", ""),
                    key_findings=llm_result.get("key_findings", []),
                    source_title=Path(note_path).stem,
                )
                if cp is not None:
                    concept_count += 1
                    # 记录 slug 用于互联
                    concept_slug = cp.stem
                    created_concepts[concept_name] = concept_slug

            # 第二轮：建立概念间互联
            for concept_data in filtered_concepts:
                concept_name = concept_data.get("name", "")
                related = concept_data.get("related_concepts", [])
                if not related or concept_name not in created_concepts:
                    continue
                my_slug = created_concepts[concept_name]
                # 检查 related 中的概念是否在本次创建的
                for rel_name in related:
                    if not is_valid_concept_name(rel_name):
                        continue
                    # 精确匹配或模糊匹配
                    rel_slug = None
                    if rel_name in created_concepts:
                        rel_slug = created_concepts[rel_name]
                    else:
                        # 模糊匹配：检查是否包含关键词
                        for cn, cs in created_concepts.items():
                            if cn.lower() in rel_name.lower() or rel_name.lower() in cn.lower():
                                if cn != concept_name:
                                    rel_slug = cs
                                    break
                    if rel_slug:
                        _upsert_concept_related(my_slug, f"[[2-Concepts/{rel_slug}]]")

            # 原子笔记提取
            for atom_data in llm_result.get("atoms", []):
                title = atom_data.get("title", "")
                atom_content = atom_data.get("content", "")
                if not atom_content:
                    continue
                p = create_atomic_note(atom_content, source_note_wikilink, title=title)
                if p is not None:
                    atom_count += 1

        else:
            # 回退：正则匹配模式
            concept_candidates = extract_concept_candidates(extraction_text)
            for term in concept_candidates:
                cp = create_or_update_concept_node(term, source_note_wikilink, source_url=source_url)
                if cp is not None:
                    concept_count += 1

            atom_sentences = extract_atomic_points(extraction_text)
            for s in atom_sentences:
                p = create_atomic_note(s, source_note_wikilink)
                if p is not None:
                    atom_count += 1

        # 触发 synthesis 更新（如果有 area）
        if concept_count > 0 or atom_count > 0:
            try:
                note_fm, _ = load_note_frontmatter(Path(note_path))
                area = note_fm.get("area", "")
                if area and area != "未分类":
                    note_title = note_fm.get("title", Path(note_path).stem)
                    note_body = Path(note_path).read_text(encoding="utf-8", errors="ignore")
                    src_summary = ""
                    src_findings = ""
                    sm = re.search(r"## 摘要\n\n(.{20,500}?)(?=\n## |\n---|$)", note_body, re.DOTALL)
                    if sm:
                        src_summary = re.sub(r"\s+", " ", sm.group(1).strip())[:400]
                    fm_s = re.search(r"## 关键发现\n\n(.{20,1000}?)(?=\n## |\n---|$)", note_body, re.DOTALL)
                    if fm_s:
                        src_findings = re.sub(r"\s+", " ", fm_s.group(1).strip())[:600]
                    update_area_synthesis(area, note_title, src_summary, src_findings)
            except Exception as syn_e:
                print(f"    ⚠️  Synthesis 更新失败: {syn_e}")

    except Exception as e:
        print(f"  ⚠️  文献后处理失败 ({note_path}): {e}")

    return concept_count, atom_count


# ── Literature Note Template ──────────────────────────────────────────────

def generate_lit_note_frontmatter(filename, file_type, source_path, metadata=None, existing_fm=None):
    """Generate frontmatter for a literature note."""
    now = datetime.now(TZ)
    note_id = now.strftime("%Y%m%d%H%M")
    safe_name = existing_fm.get("title") if existing_fm else ""
    safe_name = safe_name or sanitize_filename(Path(filename).stem)
    existing_date = existing_fm.get("date") if existing_fm and existing_fm.get("date") else now.strftime("%Y-%m-%d")
    existing_created = existing_fm.get("created") if existing_fm and existing_fm.get("created") else now.isoformat()

    tags = []
    if file_type == "paper":
        tags = ["paper", "research"]
    elif file_type == "book":
        tags = ["book"]
    else:
        tags = ["article"]

    if metadata and metadata.get("area"):
        tags.append(metadata["area"])

    fm = {
        "title": safe_name,
        "type": "literature",
        "date": existing_date,
        "created": existing_created,
        "tags": tags,
        "file_type": file_type,
        "source": source_path,
        "status": "active",
    }

    # For new notes, default to 'reviewing' so local model can review
    if not existing_fm:
        fm["status"] = "reviewing"

    if existing_fm:
        fm["updated"] = now.isoformat()
        for key in ("authors", "source_url", "doi", "year", "area"):
            if existing_fm.get(key):
                fm[key] = existing_fm[key]

    if metadata:
        if metadata.get("authors"):
            fm["authors"] = metadata["authors"]
        if metadata.get("url"):
            fm["source_url"] = metadata["url"]
        if metadata.get("doi"):
            fm["doi"] = metadata["doi"]
        if metadata.get("year"):
            fm["year"] = metadata["year"]
        if metadata.get("area"):
            fm["area"] = metadata["area"]

    return render_frontmatter(fm), note_id, safe_name


def generate_lit_note_body(file_type, safe_name, metadata=None, extraction_text=None, cache_key=None) -> tuple:
    """Generate the body of a literature note.
    
    If extraction_text is provided and LLM is available, use LLM to generate.
    Otherwise fall back to template with TODO placeholders.
    
    Returns:
        tuple[str, bool]: (body_text, llm_success)
    """
    # LLM 驱动模式
    if extraction_text and LLM_AVAILABLE:
        try:
            llm_result = process_with_llm(extraction_text, safe_name)
            
            parts = [f"# {safe_name}", ""]
            
            if llm_result.get("summary"):
                parts.append("## 摘要")
                parts.append("")
                parts.append(llm_result["summary"])
                parts.append("")
            
            if llm_result.get("key_findings"):
                parts.append("## 关键发现")
                parts.append("")
                for f in llm_result["key_findings"]:
                    cleaned = re.sub(r"^\s*[-*•]+\s*", "", str(f or "")).strip()
                    if cleaned:
                        parts.append(f"- {cleaned}")
                parts.append("")
            
            if llm_result.get("area"):
                parts.append(f"**知识领域**: {llm_result['area']}")
                parts.append("")
            
            parts.append("---")
            parts.append("")
            parts.append("## Related")
            parts.append("")
            parts.append("<!-- TODO: 添加关联笔记 -->")
            parts.append("")
            
            # 缓存 LLM 结果供 post_process 使用
            cache_llm_result(cache_key or safe_name, llm_result)
            
            return "\n".join(parts), True  # (body, llm_success=True)
        except Exception as e:
            print(f"  ⚠️ LLM body generation failed, fallback to template: {e}")
    
    # 回退：模板
    lines = []
    
    if file_type == "paper":
        lines += [f"# {safe_name}", "", "## Abstract", ""]
        if metadata and metadata.get("abstract"):
            lines.append(metadata["abstract"])
        else:
            lines.append("<!-- TODO: 填写摘要 -->")
        lines += ["", "## Key Points", ""]
        for i in range(1, 4):
            lines.append(f"- <!-- TODO: 关键发现 {i} -->")
        lines += ["", "## Method", "", "<!-- TODO: 方法描述 -->", ""]
        lines += ["## Results", "", "<!-- TODO: 结果描述 -->", ""]
    elif file_type == "book":
        lines += [f"# {safe_name}", "", "## Summary", "", "<!-- TODO: 全书摘要 -->", ""]
        lines += ["## Key Ideas", ""]
        for i in range(1, 3):
            lines.append(f"- <!-- TODO: 核心观点 {i} -->")
        lines += ["", "## Chapter Notes", "", "<!-- TODO: 章节笔记 -->", ""]
    else:
        lines += [f"# {safe_name}", "", "## Summary", "", "<!-- TODO: 文章摘要 -->", ""]
        lines += ["## Key Points", ""]
        for i in range(1, 3):
            lines.append(f"- <!-- TODO: 关键要点 {i} -->")
        lines.append("")
    
    lines += ["---", "", "## Related", "", "<!-- TODO: 添加关联笔记 -->", ""]
    return "\n".join(lines), False  # (body, llm_success=False)


def generate_chapter_note_body(book_title: str, chapter_title: str, chapter_text: str, cache_key: str):
    """Generate a chapter companion note body."""
    if chapter_text and LLM_AVAILABLE:
        try:
            llm_result = process_with_llm(chapter_text, f"{book_title} - {chapter_title}")
            cache_llm_result(cache_key, llm_result)
            parts = [f"# {chapter_title}", "", f"**所属书籍**: [[{book_title}]]", ""]
            if llm_result.get("summary"):
                parts += ["## 摘要", "", llm_result["summary"], ""]
            if llm_result.get("key_findings"):
                parts += ["## 关键发现", ""]
                for finding in llm_result["key_findings"]:
                    cleaned = re.sub(r"^\s*[-*•]+\s*", "", str(finding or "")).strip()
                    if cleaned:
                        parts.append(f"- {cleaned}")
                parts.append("")
            if llm_result.get("area"):
                parts += [f"**知识领域**: {llm_result['area']}", ""]
            parts += ["---", "", "## Related", "", "<!-- TODO: 添加关联笔记 -->", ""]
            return "\n".join(parts)
        except Exception as e:
            print(f"  ⚠️ Chapter LLM generation failed, fallback to template: {e}")

    return "\n".join([
        f"# {chapter_title}",
        "",
        f"**所属书籍**: [[{book_title}]]",
        "",
        "## 摘要",
        "",
        "<!-- TODO: 章节摘要 -->",
        "",
        "## Key Points",
        "",
        "- <!-- TODO: 关键发现 -->",
        "",
        "---",
        "",
        "## Related",
        "",
        "<!-- TODO: 添加关联笔记 -->",
        "",
    ])


def sync_book_chapter_section(book_note_path: str, chapter_entries: list[dict]) -> None:
    """Replace or append the chapter navigation section in a book note."""
    try:
        text = Path(book_note_path).read_text(encoding="utf-8", errors="ignore")
        section_lines = ["## 章节导读", ""]
        for entry in chapter_entries:
            section_lines.append(f"- [[{entry['rel_wikilink']}|{entry['title']}]]")
        section_lines.append("")
        section = "\n".join(section_lines)

        pattern = re.compile(
            r"\n## 章节导读\n.*?(?=\n## |\Z)",
            re.DOTALL,
        )
        if pattern.search(text):
            text = pattern.sub("\n" + section, text)
        elif "## 原子笔记（自动提炼）" in text:
            text = text.replace("## 原子笔记（自动提炼）", section + "\n## 原子笔记（自动提炼）", 1)
        else:
            text = text.rstrip() + "\n\n" + section

        Path(book_note_path).write_text(text.rstrip() + "\n", encoding="utf-8")
    except Exception as e:
        print(f"  ⚠️ 书籍章节导读写入失败 ({book_note_path}): {e}")


def compile_book_chapters(book_note_path: str, work_path: str, source_path: str, metadata=None, extraction_text: str = "") -> tuple:
    """Create/update chapter-level companion notes for EPUB/MOBI/PDF books."""
    ext = Path(work_path).suffix.lower()
    if ext in {".epub", ".mobi"}:
        chapters = extract_epub_chapters(work_path)
    elif ext == ".pdf":
        full_markdown = _extract_pdf_text_via_pymupdf4llm(work_path, keep_markdown=True)
        if full_markdown:
            extraction_text = full_markdown
        chapters = extract_pdf_book_chapters(extraction_text)
        _debug_pdf_book_chapters(source_path, chapters)
    else:
        return 0, 0

    if not chapters:
        return 0, 0

    metadata = metadata or {}
    book_path = Path(book_note_path)
    book_title = book_path.stem
    chapter_dir = Path(CONFIG["literature_dir"]) / "Books" / sanitize_filename(book_path.stem)
    chapter_dir.mkdir(parents=True, exist_ok=True)

    chapter_entries = []
    concept_total = 0
    atom_total = 0
    expected_files = {f"{chapter['slug']}.md" for chapter in chapters}

    for old_path in chapter_dir.glob("*.md"):
        if old_path.name not in expected_files:
            try:
                old_path.unlink()
            except OSError:
                pass

    for chapter in chapters:
        chapter_filename = f"{chapter['slug']}.md"
        chapter_path = chapter_dir / chapter_filename
        chapter_title = chapter["title"]
        chapter_cache_key = chapter_path.stem

        fm_data = {
            "title": chapter_title,
            "type": "literature",
            "date": datetime.now(TZ).strftime("%Y-%m-%d"),
            "created": datetime.now(TZ).isoformat(),
            "tags": ["book", "chapter"],
            "file_type": "book-chapter",
            "source": source_path,
            "status": "active",
            "book_note": os.path.relpath(book_note_path, CONFIG["atlas_vault"]),
            "chapter_index": chapter["index"],
        }
        if metadata.get("area"):
            fm_data["area"] = metadata["area"]
        if metadata.get("authors"):
            fm_data["authors"] = metadata["authors"]
        if metadata.get("url"):
            fm_data["source_url"] = metadata["url"]

        body = generate_chapter_note_body(
            book_title=book_path.stem,
            chapter_title=chapter_title,
            chapter_text=chapter["text"],
            cache_key=chapter_cache_key,
        )
        chapter_path.write_text(render_frontmatter(fm_data) + body, encoding="utf-8")

        llm_data = peek_cached_llm_result(chapter_cache_key)
        if LLM_AVAILABLE and llm_data:
            _append_concept_links_to_note(str(chapter_path), llm_data.get("concepts", []))

        concept_count, atom_count = post_process_literature_note(
            note_path=str(chapter_path),
            extraction_text=chapter["text"],
            source_url=metadata.get("url", ""),
        )
        if atom_count > 0:
            _append_atom_links_to_note(str(chapter_path))

        concept_total += concept_count
        atom_total += atom_count
        chapter_entries.append({
            "title": chapter_title,
            "rel_wikilink": os.path.relpath(chapter_path, CONFIG["atlas_vault"])[:-3],
        })
        sync_book_chapter_section(book_note_path, chapter_entries)

    return len(chapter_entries), atom_total


def extract_metadata_from_pdf_text(text, filename):
    """Extract basic metadata from PDF text content."""
    metadata = {}
    pdf_info = extract_pdf_info(filename)

    if pdf_info.get("title"):
        metadata["title"] = pdf_info["title"]
    if pdf_info.get("author"):
        metadata["authors"] = pdf_info["author"].rstrip(";")

    # Try to find title from first lines
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines and not metadata.get("title"):
        # First non-empty line is often the title
        metadata["title"] = lines[0][:100]

    # Try to find authors (common patterns)
    author_patterns = [
        r'(?:by|authors?[:\s]+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5})',
    ]
    for pattern in author_patterns:
        m = re.search(pattern, text[:2000])
        if m:
            metadata["authors"] = m.group(1).strip()
            break

    # Extract abstract section
    abstract_match = re.search(
        r'abstract[:\s]+(.*?)(?=\n\s*(?:introduction|1\s+\.|keywords|key words|I\.\s))',
        text, re.IGNORECASE | re.DOTALL
    )
    if abstract_match:
        abstract = abstract_match.group(1).strip()
        abstract = re.sub(r'\s+', ' ', abstract)
        if len(abstract) > 20:
            metadata["abstract"] = abstract[:500]

    # ── Area detection: weighted scoring + cross-domain disambiguation ──
    area_scores = {}
    text_lower = text.lower()

    # 定义 area 关键词及权重（权重越高越具区分度）
    area_keywords = {
        "AI-ML": {
            "strong": ["neural network", "deep learning", "transformer", "large language model",
                       "GPT", "BERT", "attention mechanism", "embedding", "diffusion model",
                       "reinforcement learning", "generative model", "language model"],
            "weak": ["LLM", "agent", "AI", "machine learning", "training", "inference",
                     "prompt", "fine-tun", "token", "parameter"],
        },
        "Education": {
            "strong": ["pedagogy", "curriculum", "classroom", "student learning",
                       "learning outcome", "teaching", "course design", "assessment",
                       "educational", "learner", "competency", "instructional"],
            "weak": ["student", "education", "learning", "school", "university",
                     "teacher", "lecture", "syllabus", "grade", "assignment"],
        },
        "Engineering": {
            "strong": ["software engineering", "system architecture", "API design",
                       "database", "infrastructure", "microservice", "devops",
                       "code review", "refactoring", "deployment"],
            "weak": ["software", "engineering", "framework", "system", "tool",
                     "library", "module", "component", "platform"],
        },
        "Policy": {
            "strong": ["policy", "regulation", "governance", "compliance", "legislation"],
            "weak": ["government", "standard", "regulation", "public", "administration"],
        },
        "Research-Method": {
            "strong": ["research method", "systematic review", "meta-analysis",
                       "grounded theory", "case study", "qualitative analysis"],
            "weak": ["methodology", "empirical", "survey", "interview", "data collection"],
        },
    }

    for area, keywords in area_keywords.items():
        strong_score = sum(3 for kw in keywords["strong"] if kw in text_lower)
        weak_score = sum(1 for kw in keywords["weak"] if kw in text_lower)
        area_scores[area] = strong_score + weak_score

    # 消歧规则：当 Education 和 AI-ML 分数接近时，检查教育强信号
    edu_score = area_scores.get("Education", 0)
    ai_score = area_scores.get("AI-ML", 0)

    if edu_score >= 4 and ai_score >= 3:
        # 交叉领域：看谁有更多 strong 信号
        edu_strong = sum(1 for kw in area_keywords["Education"]["strong"] if kw in text_lower)
        ai_strong = sum(1 for kw in area_keywords["AI-ML"]["strong"] if kw in text_lower)
        if edu_strong > ai_strong:
            metadata["area"] = "Education"
        elif ai_strong > edu_strong:
            metadata["area"] = "AI-ML"
        else:
            # 都没有 strong 信号或持平 → 看标题和摘要中的关键词密度
            title_lower = (metadata.get("title", "") or "").lower()
            abstract_lower = (metadata.get("abstract", "") or "").lower()
            title_abstract = title_lower + " " + abstract_lower
            if any(kw in title_abstract for kw in area_keywords["Education"]["strong"]):
                metadata["area"] = "Education"
            else:
                metadata["area"] = "AI-ML"
    elif edu_score > ai_score and edu_score >= 3:
        metadata["area"] = "Education"
    elif ai_score >= 3:
        metadata["area"] = "AI-ML"
    else:
        # 选最高分
        best = max(area_scores, key=area_scores.get)
        if area_scores[best] >= 3:
            metadata["area"] = best

    return metadata


# ── Index Management ──────────────────────────────────────────────────────

def append_to_index(note_title, file_type, note_rel_path, area=None):
    """Append entry to sources-index.md."""
    index_path = os.path.join(CONFIG["index_dir"], "sources-index.md")
    target_abs = os.path.join(CONFIG["atlas_vault"], note_rel_path)
    index_link = os.path.relpath(target_abs, CONFIG["index_dir"])

    # Build index entry
    entry = f"- [{note_title}]({index_link})"
    if area:
        entry += f" — *{area}*"
    entry += "\n"

    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        existing_link = f"]({index_link})"
        if existing_link in content:
            content = re.sub(
                rf"^- \[.*?\]\({re.escape(index_link)}\)(?: — \*.*?\*)?$",
                entry.rstrip(),
                content,
                flags=re.M,
            )
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(content)
            return

        # Find the appropriate section or append at end
        if area and f"## {area}" in content:
            # Insert under the area section
            section_header = f"## {area}"
            idx = content.index(section_header)
            # Find next ## or end of file
            next_section = content.find("\n## ", idx + len(section_header))
            if next_section == -1:
                next_section = len(content)
            content = content[:next_section] + entry + content[next_section:]
        else:
            # Add new section header if area specified
            if area:
                entry = f"\n## {area}\n" + entry
            content = content.rstrip() + "\n" + entry + "\n"
    else:
        # Create new index file
        header = f"# Sources Index（LLM 维护，最后更新：{now_iso()}）\n\n"
        if area:
            header += f"## {area}\n"
        content = header + entry + "\n"

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)


# ── Dropbox Ingest ────────────────────────────────────────────────────────

def backup_source_file(src_path: Path) -> None:
    """Move a processed raw source file into the backup directory."""
    backup_dir = Path(CONFIG["backup_dir"]).expanduser()
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_dest = backup_dir / src_path.name
    if backup_dest.exists():
        stem = backup_dest.stem
        suffix = backup_dest.suffix
        ts = datetime.now(TZ).strftime("%Y%m%d%H%M%S")
        backup_dest = backup_dir / f"{stem}_{ts}{suffix}"
    shutil.move(str(src_path), str(backup_dest))
    print(f"  📦 已备份: {src_path.name} → Dropbox raw/")


def ingest_dropbox(dry_run=False, single_file=None, force=False):
    """Scan Dropbox raw/ directory and process new/modified files."""
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}📁 Scanning Dropbox raw/...")

    raw_dir = CONFIG["dropbox_raw"]
    if not os.path.isdir(raw_dir):
        print(f"  ⚠️  Dropbox raw/ not found: {raw_dir}")
        return

    conn = get_db()
    init_db(conn)
    hash_state = load_ingest_hash_state()

    if single_file:
        files_to_check = [Path(single_file)]
    else:
        files_to_check = sorted(Path(raw_dir).iterdir())

    stats = {"found": 0, "new": 0, "updated": 0, "skipped": 0, "errors": [], "items": []}

    for filepath in files_to_check:
        if not filepath.is_file():
            continue

        filename = filepath.name
        full_path = str(filepath)
        mtime = int(filepath.stat().st_mtime)
        stats["found"] += 1

        # Check if already processed (by path and mtime)
        row = conn.execute(
            "SELECT mtime, sha256, status, target_note FROM processed WHERE path = ?",
            (full_path,)
        ).fetchone()

        if not force and row and row["status"] in ("incomplete", "draft"):
            print(f"  🔄 Previously incomplete (status={row['status']}), retrying...")
        elif not force and row and row["mtime"] == mtime and row["status"] in ("success", "dedup_content"):
            stats["skipped"] += 1
            detail = "mtime_unchanged" if row["status"] == "success" else "content_hash_duplicate"
            stats["items"].append({"filename": filename, "status": "skipped", "detail": detail})
            continue

        print(f"\n  📄 {filename}")

        # Copy file to temp to avoid Dropbox lock issues
        if not dry_run:
            temp_path, copied = copy_with_retry(full_path)
            if not copied:
                stats["errors"].append(f"{filename}: copy failed (locked)")
                stats["items"].append({"filename": filename, "status": "error", "detail": "copy_failed_locked"})
                continue
            work_path = temp_path
        else:
            work_path = full_path
            print(f"  [DRY-RUN] Would process this file")

        pdf_content_hash = None
        is_pdf = Path(work_path).suffix.lower() == ".pdf"
        if not dry_run and is_pdf:
            pdf_content_hash = compute_sha256(work_path)
            existing_hash_note_path = hash_state.get(pdf_content_hash)
            if existing_hash_note_path:
                print(
                    f"  [DEDUP] 跳过：内容与已有笔记 {existing_hash_note_path} 相同（hash: {pdf_content_hash[:8]}）"
                )
                conn.execute("""
                    INSERT OR REPLACE INTO processed
                    (path, filename, mtime, sha256, file_type, processed_at, target_note, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    full_path, filename, mtime, pdf_content_hash, "pdf",
                    now_iso(), existing_hash_note_path, "dedup_content"
                ))
                conn.commit()
                stats["skipped"] += 1
                stats["items"].append({
                    "filename": filename,
                    "status": "skipped",
                    "detail": f"content_hash_duplicate:{pdf_content_hash[:8]}",
                    "note_path": existing_hash_note_path,
                })
                try:
                    if work_path != full_path and os.path.exists(full_path):
                        backup_source_file(filepath)
                except Exception as move_err:
                    print(f"  ⚠️  备份失败（不影响处理结果）: {move_err}")
                if work_path != full_path and os.path.exists(work_path):
                    os.remove(work_path)
                continue

        # Classify file
        file_type = classify_file(work_path)
        print(f"  🏷️  Classified as: {file_type}")

        if dry_run:
            stats["new"] += 1
            stats["items"].append({"filename": filename, "status": "dry-run", "detail": file_type})
            continue

        # Extract metadata + source text for post-processing
        metadata = {}
        extraction_text = ""
        if work_path.endswith(".pdf"):
            extraction_text = extract_text_from_pdf(work_path)
            metadata = extract_metadata_from_pdf_text(extraction_text, filename)
        else:
            extraction_text = _load_note_text(work_path)

        existing_note_path = None
        existing_fm = {}
        if row and row["target_note"] and os.path.exists(row["target_note"]):
            existing_note_path = row["target_note"]
            existing_fm, _ = load_note_frontmatter(Path(existing_note_path))
        else:
            existing_note_path, existing_fm = find_existing_literature_note(
                source_path=full_path,
                source_url=metadata.get("url", ""),
                title=Path(filename).stem,
            )

        frontmatter, note_id, safe_name = generate_lit_note_frontmatter(
            filename,
            file_type,
            full_path,
            metadata,
            existing_fm=existing_fm,
        )
        cache_key = Path(existing_note_path).stem if existing_note_path else f"{note_id}-{safe_name}"
        body, llm_success = generate_lit_note_body(
            file_type,
            safe_name,
            metadata,
            extraction_text=extraction_text,
            cache_key=cache_key,
        )
        if not llm_success:
            print(f"  ⚠️ 笔记使用模板填充（LLM 未参与），status: incomplete")

        # Determine output directory
        subdir_map = {
            "paper": "Papers",
            "book": "Books",
            "article": "Articles",
            "repo": "Repos",
            "podcast": "Podcasts",
            "tweet": "Tweets",
        }
        subdir = subdir_map.get(file_type, "Articles")
        out_dir = os.path.join(CONFIG["literature_dir"], subdir)
        os.makedirs(out_dir, exist_ok=True)

        if existing_note_path:
            note_path = existing_note_path
            note_filename = os.path.basename(note_path)
        else:
            note_filename = f"{note_id}-{safe_name}.md"
            note_path = os.path.join(out_dir, note_filename)

        note_path = relocate_literature_note(note_path, file_type)
        note_filename = os.path.basename(note_path)

        # Write note
        try:
            with open(note_path, "w", encoding="utf-8") as f:
                f.write(frontmatter + body)
            action = "updated" if existing_note_path else "created"
            print(f"  ✅ Note {action}: {note_path}")

            # 将概念链接写入文献笔记的 Related 区
            cached_for_note = peek_cached_llm_result(Path(note_filename).stem)
            if LLM_AVAILABLE and cached_for_note:
                _append_concept_links_to_note(note_path, cached_for_note.get("concepts", []))

            # Compute SHA256 of source
            sha256 = pdf_content_hash or compute_sha256(work_path)

            # Update SQLite
            is_update = row is not None or existing_note_path is not None
            note_status = "success" if llm_success else "incomplete"
            conn.execute("""
                INSERT OR REPLACE INTO processed
                (path, filename, mtime, sha256, file_type, processed_at, target_note, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                full_path, filename, mtime, sha256, file_type,
                now_iso(), note_path, note_status
            ))
            conn.commit()

            if is_update:
                stats["updated"] += 1
                item_status = "updated"
            else:
                stats["new"] += 1
                item_status = "created"

            if pdf_content_hash and hash_state.get(pdf_content_hash) != note_path:
                hash_state[pdf_content_hash] = note_path
                save_ingest_hash_state(hash_state)

            # Update index
            note_rel_path = os.path.relpath(note_path, CONFIG["atlas_vault"])
            append_to_index(safe_name, file_type, note_rel_path, metadata.get("area"))
            print(f"  📝 Index updated")

            # Post-process: concept + atomic extraction (rule-based, no LLM)
            concept_count, atom_count = post_process_literature_note(
                note_path=note_path,
                extraction_text=extraction_text or body,
                source_url=metadata.get("url", "")
            )
            print(f"  🧠 Concepts: {concept_count}, ⚛️ Atoms: {atom_count}")

            # 追加原子笔记链接到文献笔记
            if atom_count > 0:
                _append_atom_links_to_note(note_path)

            # Log to log.md
            try:
                note_rel_for_log = os.path.relpath(note_path, CONFIG["atlas_vault"])
                if note_rel_for_log.endswith(".md"):
                    note_rel_for_log = note_rel_for_log[:-3]
                summary_text = ""
                try:
                    note_content = Path(note_path).read_text(encoding="utf-8", errors="ignore")
                    sm = re.search(r"## 摘要\n\n(.{20,300}?)(?=\n\n|$)", note_content, re.DOTALL)
                    if sm:
                        summary_text = re.sub(r"\s+", " ", sm.group(1).strip())[:150]
                except Exception:
                    pass
                append_to_log("ingest", safe_name, {
                    "type": file_type,
                    "source": "dropbox",
                    "summary": summary_text,
                    "concepts": f"{concept_count}个" if concept_count else "",
                    "atoms": f"{atom_count}条" if atom_count else "",
                    "file": note_rel_for_log,
                })
            except Exception as log_e:
                print(f"    ⚠️  Log write failed: {log_e}")

            auto_git_commit("ingest", safe_name)

            if file_type == "book" and Path(work_path).suffix.lower() in {".epub", ".mobi", ".pdf"}:
                chapter_count, chapter_atom_count = compile_book_chapters(
                    book_note_path=note_path,
                    work_path=work_path,
                    source_path=full_path,
                    metadata=metadata,
                    extraction_text=extraction_text,
                )
                if chapter_count:
                    print(f"  📚 Chapter notes: {chapter_count}, ⚛️ Chapter atoms: {chapter_atom_count}")

            stats["items"].append({
                "filename": filename,
                "status": item_status,
                "detail": file_type,
                "note_path": note_path,
            })

            # Backup: move source file to backup dir on success
            if work_path != full_path and os.path.exists(full_path):
                try:
                    backup_source_file(filepath)
                except Exception as move_err:
                    print(f"  ⚠️  备份失败（不影响处理结果）: {move_err}")

            # Clean up temp file
            if work_path != full_path and os.path.exists(work_path):
                os.remove(work_path)

        except Exception as e:
            stats["errors"].append(f"{filename}: {e}")
            stats["items"].append({"filename": filename, "status": "error", "detail": str(e)})
            print(f"  ❌ Error: {e}")

    # Log scan
    if not dry_run:
        conn.execute("""
            INSERT INTO scan_log (scanned_at, files_found, files_new, files_updated, files_skipped, errors)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            now_iso(),
            stats["found"],
            stats["new"],
            stats["updated"],
            stats["skipped"],
            "; ".join(stats["errors"]) if stats["errors"] else None
        ))
        conn.commit()
    conn.close()
    report_json, report_md = write_ingest_run_report("dropbox", stats, dry_run=dry_run)

    # 生成研究建议（所有文件处理完后）
    if not dry_run and (stats["new"] > 0 or stats["updated"] > 0):
        suggestions = generate_research_suggestions()
        if suggestions:
            append_suggestions_to_log(suggestions)

    # Summary
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}📊 Scan complete:")
    print(f"  Found: {stats['found']}, New: {stats['new']}, "
          f"Updated: {stats['updated']}, Skipped: {stats['skipped']}")
    print(f"  📝 Run report: {report_md}")
    if stats["errors"]:
        print(f"  ⚠️  Errors: {len(stats['errors'])}")
        for err in stats["errors"][:5]:
            print(f"    - {err}")
    _write_oq_pending_queue(stats, source="dropbox", dry_run=dry_run)


# ── Clippings Ingest ──────────────────────────────────────────────────────

def parse_frontmatter(content):
    """Parse YAML frontmatter from markdown content. Returns (frontmatter_dict, body)."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    fm_text = parts[1].strip()
    body = parts[2].strip()

    # Simple YAML parsing (no PyYAML dependency)
    fm = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            # Remove quotes
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            elif value.startswith("[") and value.endswith("]"):
                value = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",")]
            fm[key] = value

    return fm, body


def update_frontmatter_status(filepath, status):
    """Update the status field in a markdown file's frontmatter."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    fm, body = parse_frontmatter(content)

    if content.startswith("---"):
        # Rebuild frontmatter
        fm["status"] = status
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(render_frontmatter(fm) + body)
    else:
        # No frontmatter, add one
        new_content = f"---\nstatus: {status}\n---\n\n{content}"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)


def review_pending_notes():
    """Scan for notes with status=reviewing and run local Gemma 4 review.

    For each reviewing note:
    1. Re-read the source extraction text
    2. Run review_with_local() to get missed concepts / corrections / findings
    3. Append review section to the note
    4. Create concept nodes for missed concepts
    5. Update status to active
    """
    if not LOCAL_REVIEW_AVAILABLE:
        print("  ⚠️ Local review module not available, skipping")
        return

    if not is_omlx_online():
        print("  ⚠️ oMLX offline, skipping review")
        return

    print("  🔍 Scanning for notes with status=reviewing...")
    reviewed = 0

    for note_path in iter_literature_notes():
        try:
            fm, body = load_note_frontmatter(note_path)
            status = fm.get("status", "").strip().lower()
            if status != "reviewing":
                continue

            title = fm.get("title", note_path.stem)
            source_path = fm.get("source", "")
            print(f"  📝 Reviewing: {title}")

            # Load extraction text from source
            extraction_text = ""
            if source_path and os.path.exists(source_path):
                extraction_text = _load_note_text(source_path)
            if not extraction_text:
                extraction_text = body  # fallback to note body

            if not extraction_text or len(extraction_text) < 200:
                print(f"    ⏭️  Too little text to review, skipping")
                update_frontmatter_status(str(note_path), "active")
                continue

            # Run local review
            review = review_with_local(extraction_text, body)
            if not review:
                print(f"    ⏭️  Review returned nothing, marking active")
                update_frontmatter_status(str(note_path), "active")
                continue

            # Build review section
            section_parts = ["", "---", "", "## 本地模型审核补充", ""]

            missed = review.get("missed_concepts", [])
            if missed:
                section_parts.append("### 遗漏概念")
                section_parts.append("")
                for mc in missed:
                    name = mc.get("name", "")
                    definition = mc.get("definition", "")
                    section_parts.append(f"- **{name}**: {definition}")
                section_parts.append("")

            corrections = review.get("corrections", [])
            if corrections:
                section_parts.append("### 修正建议")
                section_parts.append("")
                for c in corrections:
                    section_parts.append(f"- {c}")
                section_parts.append("")

            supplementary = review.get("supplementary_findings", [])
            if supplementary:
                section_parts.append("### 补充发现")
                section_parts.append("")
                for s in supplementary:
                    section_parts.append(f"- {s}")
                section_parts.append("")

            if len(section_parts) <= 5:
                # No review content
                section_parts.append("(无补充)\n")

            review_section = "\n".join(section_parts) + "\n"

            # Append to note (replace existing review section if present)
            current_content = note_path.read_text(encoding="utf-8", errors="ignore")
            current_content = re.sub(
                r"\n---\n\n## 本地模型审核补充\n.*\Z",
                "",
                current_content,
                flags=re.S,
            ).rstrip()
            note_path.write_text(current_content + review_section, encoding="utf-8")

            # Create concept nodes for missed concepts
            note_rel = os.path.relpath(str(note_path), CONFIG["atlas_vault"])
            source_wikilink = note_rel[:-3] if note_rel.endswith(".md") else note_rel
            source_url = fm.get("source_url", "")

            for mc in (missed or []):
                cp = create_or_update_concept_node(
                    mc.get("name", ""),
                    source_wikilink,
                    definition=mc.get("definition", ""),
                    category=mc.get("category", ""),
                    related_concepts=mc.get("related_concepts", []),
                    source_url=source_url,
                )
                if cp is not None:
                    # Append link to note's Related section
                    slug = cp.stem
                    name = mc.get("name", "")
                    link_text = f"- [[2-Concepts/{slug}|{name}]]"
                    updated = note_path.read_text(encoding="utf-8", errors="ignore")
                    if link_text not in updated:
                        updated = updated.rstrip() + "\n" + link_text + "\n"
                        note_path.write_text(updated, encoding="utf-8")

            # Mark as active
            update_frontmatter_status(str(note_path), "active")
            print(f"    ✅ Review complete, status → active")
            reviewed += 1

            # Log to log.md
            try:
                note_rel_for_log = os.path.relpath(str(note_path), CONFIG["atlas_vault"])
                if note_rel_for_log.endswith(".md"):
                    note_rel_for_log = note_rel_for_log[:-3]
                append_to_log("review | Gemma 4 补充", title, {
                    "type": "paper",
                    "file": note_rel_for_log,
                })
            except Exception as log_e:
                print(f"    ⚠️  Log write failed: {log_e}")

            auto_git_commit("review", title)

        except Exception as e:
            print(f"    ❌ Review failed ({note_path.name}): {e}")
            # Still mark as active to avoid infinite retry
            try:
                update_frontmatter_status(str(note_path), "active")
            except Exception:
                pass

    print(f"  🔍 Review complete: {reviewed} notes reviewed")


def _write_oq_pending_queue(stats: dict, source: str, dry_run: bool = False) -> None:
    """
    将本次 ingest 新增的文献追加写入 OQ pending 队列。
    队列文件：~/pkm/atlas/.state/oq-pending.json

    规则：
    - 只写 status="created" 的条目（跳过 updated/skipped/error）
    - dry_run 模式不写入
    - 读取笔记 frontmatter 获取 title 和 area（失败则置 None）
    - 追加语义，不覆盖已有 pending 条目
    - 队列文件损坏时自动备份并重建
    - 任何异常静默处理，不影响主流程
    """
    if dry_run:
        return

    created_items = [
        item for item in stats.get("items", [])
        if item.get("status") == "created" and item.get("note_path")
    ]
    if not created_items:
        return

    queue_path = Path(os.path.expanduser("~/pkm/atlas/.state/oq-pending.json"))
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing queue
    existing: list = []
    if queue_path.exists():
        try:
            with open(queue_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                raise ValueError("Queue is not a list")
        except Exception as e:
            # Backup corrupted file and start fresh
            bak = queue_path.with_suffix(f".bak.{int(time.time())}")
            try:
                queue_path.rename(bak)
                print(f"  ⚠️  OQ queue corrupted, backed up to {bak.name}: {e}")
            except Exception:
                pass
            existing = []

    vault_root = Path(CONFIG["atlas_vault"])
    ingested_at = datetime.now(timezone(timedelta(hours=8))).isoformat()

    new_entries = []
    for item in created_items:
        note_path_abs = item["note_path"]
        try:
            note_rel = os.path.relpath(str(note_path_abs), str(vault_root))
        except Exception:
            note_rel = str(note_path_abs)

        # Read frontmatter for title and area
        title = None
        area = None
        try:
            with open(note_path_abs, "r", encoding="utf-8") as f:
                raw = f.read()
            fm, _ = parse_frontmatter(raw)
            title = fm.get("title") or None
            area = fm.get("area") or None
        except Exception:
            pass

        new_entries.append({
            "ingested_at": ingested_at,
            "source": source,
            "note_path": note_rel,
            "title": title,
            "area": area,
            "status": "pending",
        })

    combined = existing + new_entries
    try:
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)
        print(f"  📋 OQ queue: {len(new_entries)} item(s) added → {queue_path}")
    except Exception as e:
        print(f"  ⚠️  OQ queue write failed: {e}")


def _launch_async_review():
    """Launch review_pending_notes() in a background process if oMLX is online."""
    if not LOCAL_REVIEW_AVAILABLE:
        return
    try:
        if not is_omlx_online():
            return
    except Exception:
        return

    script_path = os.path.abspath(__file__)
    try:
        subprocess.Popen(
            [sys.executable, script_path, "--source", "review-only"],
            stdout=open(os.devnull, "w"),
            stderr=open(os.devnull, "w"),
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        print("  🚀 Gemma 4 review launched in background")
    except Exception as e:
        print(f"  ⚠️ Failed to launch background review: {e}")


def ingest_clippings(dry_run=False, force=False):
    """Scan clippings directory and process pending items."""
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}📎 Scanning Clippings...")

    clippings_dir = CONFIG["clippings_dir"]
    if not os.path.isdir(clippings_dir):
        print(f"  ⚠️  Clippings directory not found: {clippings_dir}")
        return

    conn = get_db()
    init_db(conn)

    stats = {"found": 0, "new": 0, "updated": 0, "skipped": 0, "errors": [], "items": []}

    for filepath in sorted(Path(clippings_dir).glob("*.md")):
        filename = filepath.name
        stats["found"] += 1

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        fm, body = parse_frontmatter(content)
        status = fm.get("status", "").strip().lower()

        # Skip already processed
        if not force and status in ("compiled", "processed", "done"):
            stats["skipped"] += 1
            stats["items"].append({"filename": filename, "status": "skipped", "detail": f"status={status}"})
            continue

        # Only process pending or unstatused
        if not force and status not in ("pending", ""):
            stats["skipped"] += 1
            stats["items"].append({"filename": filename, "status": "skipped", "detail": f"status={status}"})
            continue

        print(f"\n  📎 {filename}")
        print(f"     Status: {status or '(none)'}")

        if dry_run:
            print(f"  [DRY-RUN] Would process this clipping")
            stats["new"] += 1
            stats["items"].append({"filename": filename, "status": "dry-run", "detail": "clipping"})
            continue

        try:
            # Extract title from frontmatter or first heading
            title = fm.get("title", fm.get("name", ""))
            if not title:
                # Try first heading
                m = re.match(r'^#\s+(.+)', body, re.MULTILINE)
                title = m.group(1).strip() if m else sanitize_filename(filepath.stem)
            display_title = title.strip() if title else filepath.stem
            safe_name = sanitize_filename(display_title)

            # Determine area from tags if available
            tags = fm.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.strip("[]").split(",")]

            area = None
            area_map = {"ai": "AI-ML", "ml": "AI-ML", "education": "Education",
                        "engineering": "Engineering", "research": "Research-Method"}
            for tag in tags:
                tag_lower = tag.lower()
                if tag_lower in area_map:
                    area = area_map[tag_lower]
                    break

            # Get source URL
            source_url = fm.get("source_url", fm.get("url", fm.get("source", "")))
            if isinstance(source_url, list):
                source_url = source_url[0] if source_url else ""

            # Get author
            author = fm.get("author", fm.get("authors", ""))
            if isinstance(author, list):
                author = ", ".join(str(a) for a in author)

            existing_note_path, existing_fm = find_existing_literature_note(
                source_url=source_url,
                title=display_title or filepath.stem,
            )

            note_id = datetime.now(TZ).strftime("%Y%m%d%H%M")
            out_dir = os.path.join(CONFIG["literature_dir"], "Articles")
            os.makedirs(out_dir, exist_ok=True)

            if existing_note_path:
                note_path = existing_note_path
                note_filename = os.path.basename(note_path)
            else:
                note_filename = f"{note_id}-{safe_name}.md"
                note_path = os.path.join(out_dir, note_filename)
            note_stem = Path(note_filename).stem

            # Build frontmatter
            now = datetime.now(TZ)
            clipping_title = existing_fm.get("title") if existing_fm else ""
            clipping_title = clipping_title or display_title
            fm_data = {
                "title": clipping_title,
                "type": "literature",
                "date": existing_fm.get("date") if existing_fm and existing_fm.get("date") else now.strftime('%Y-%m-%d'),
                "created": existing_fm.get("created") if existing_fm and existing_fm.get("created") else now.isoformat(),
                "tags": ["article", "clipping"],
            }
            for key in ("area", "authors", "source_url", "doi", "year"):
                if existing_fm.get(key):
                    fm_data[key] = existing_fm[key]
            if area:
                fm_data["area"] = area
            if author:
                fm_data["authors"] = author
            if source_url:
                fm_data["source_url"] = source_url
            fm_data["source"] = str(filepath)
            fm_data["file_type"] = "article"
            fm_data["status"] = "active"
            # For new clippings, default to 'reviewing' so local model can review
            if not existing_note_path:
                fm_data["status"] = "reviewing"
            if existing_note_path:
                fm_data["updated"] = now.isoformat()

            # Build body - use LLM if available
            extraction_text = body  # clipping 正文用于 LLM 分析
            if LLM_AVAILABLE and body:
                try:
                    llm_result = process_with_llm(body, clipping_title)
                    body_lines = [f"# {clipping_title}", ""]
                    if llm_result.get("summary"):
                        body_lines += ["## 摘要", "", llm_result["summary"], ""]
                    if llm_result.get("key_findings"):
                        body_lines += ["## 关键发现", ""]
                        for kf in llm_result["key_findings"]:
                            body_lines.append(f"- {kf}")
                        body_lines.append("")
                    if llm_result.get("area"):
                        body_lines += [f"**知识领域**: {llm_result['area']}", ""]
                        area = area or llm_result.get("area")
                    body_lines += ["---", "", "## Related", "", "<!-- TODO: 添加关联笔记 -->", ""]
                    cache_llm_result(note_stem, llm_result)
                except Exception as e:
                    print(f"  ⚠️ LLM clipping analysis failed: {e}")
                    body_lines = [f"# {clipping_title}", "", "## Summary", "", "<!-- TODO: 总结摘要 -->", "", "## Key Points", "", "- <!-- TODO: 关键要点 -->", ""]
            else:
                body_lines = [f"# {clipping_title}", ""]
                body_lines.append("## Summary")
                body_lines.append("")
                description = fm.get("description", "")
                if description:
                    body_lines.append(f"> {description}")
                    body_lines.append("")
                else:
                    body_lines.append("<!-- TODO: 总结摘要 -->")
                    body_lines.append("")
                body_lines += ["## Key Points", "", "- <!-- TODO: 关键要点 -->", ""]

            # Include clipping reference
            body_lines.append("## Source Clipping")
            body_lines.append("")
            body_lines.append(f"Original: [[{filepath.name}]]")
            body_lines.append("")

            if area:
                fm_data["area"] = area

            with open(note_path, "w", encoding="utf-8") as f:
                f.write(render_frontmatter(fm_data) + "\n".join(body_lines))

            action = "updated" if existing_note_path else "created"
            print(f"  ✅ Note {action}: {note_path}")

            # 将概念链接写入文献笔记的 Related 区
            llm_data = peek_cached_llm_result(note_stem)
            if LLM_AVAILABLE and llm_data:
                concepts = llm_data.get("concepts", [])
                if concepts:
                    _append_concept_links_to_note(note_path, concepts)

            # Update index
            note_rel_path = os.path.relpath(note_path, CONFIG["atlas_vault"])
            append_to_index(clipping_title, "article", note_rel_path, area)
            print(f"  📝 Index updated")

            # Post-process: concept + atomic extraction
            concept_count, atom_count = post_process_literature_note(
                note_path=note_path,
                extraction_text=body,
                source_url=source_url,
            )
            print(f"  🧠 Concepts: {concept_count}, ⚛️ Atoms: {atom_count}")

            # 追加原子笔记链接
            if atom_count > 0:
                _append_atom_links_to_note(note_path)

            # Log to log.md
            try:
                note_rel_for_log = os.path.relpath(note_path, CONFIG["atlas_vault"])
                if note_rel_for_log.endswith(".md"):
                    note_rel_for_log = note_rel_for_log[:-3]
                summary_text = ""
                try:
                    note_content = Path(note_path).read_text(encoding="utf-8", errors="ignore")
                    sm = re.search(r"## 摘要\n\n(.{20,300}?)(?=\n\n|$)", note_content, re.DOTALL)
                    if sm:
                        summary_text = re.sub(r"\s+", " ", sm.group(1).strip())[:150]
                except Exception:
                    pass
                append_to_log("ingest", clipping_title, {
                    "type": "article",
                    "source": "clippings",
                    "summary": summary_text,
                    "concepts": f"{concept_count}个" if concept_count else "",
                    "atoms": f"{atom_count}条" if atom_count else "",
                    "file": note_rel_for_log,
                })
            except Exception as log_e:
                print(f"    ⚠️  Log write failed: {log_e}")

            auto_git_commit("clip", clipping_title)

            # Mark clipping as compiled
            update_frontmatter_status(str(filepath), "compiled")
            print(f"  ✅ Clipping marked as compiled")

            if existing_note_path:
                stats["updated"] += 1
                item_status = "updated"
            else:
                stats["new"] += 1
                item_status = "created"

            stats["items"].append({
                "filename": filename,
                "status": item_status,
                "detail": "article",
                "note_path": note_path,
            })

        except Exception as e:
            stats["errors"].append(f"{filename}: {e}")
            stats["items"].append({"filename": filename, "status": "error", "detail": str(e)})
            print(f"  ❌ Error: {e}")

    # Log scan
    if not dry_run:
        errors_str = "; ".join(stats["errors"]) if stats["errors"] else None
        conn.execute("""
            INSERT INTO scan_log (scanned_at, files_found, files_new, files_updated, files_skipped, errors)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            now_iso(),
            stats["found"], stats["new"], stats["updated"], stats["skipped"],
            errors_str
        ))
        conn.commit()
    conn.close()
    report_json, report_md = write_ingest_run_report("clippings", stats, dry_run=dry_run)

    # 生成研究建议（所有文件处理完后）
    if not dry_run and (stats["new"] > 0 or stats["updated"] > 0):
        suggestions = generate_research_suggestions()
        if suggestions:
            append_suggestions_to_log(suggestions)

    # Summary
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}📊 Clippings scan complete:")
    print(f"  Found: {stats['found']}, New: {stats['new']}, Updated: {stats['updated']}, Skipped: {stats['skipped']}")
    print(f"  📝 Run report: {report_md}")
    if stats["errors"]:
        print(f"  ⚠️  Errors: {len(stats['errors'])}")
        for err in stats["errors"][:5]:
            print(f"    - {err}")
    _write_oq_pending_queue(stats, source="clippings", dry_run=dry_run)


# ── Atlas Overview Generation ──────────────────────────────────────────────

def generate_atlas_overview():
    """Generate a Slides Extended overview slide deck from vault statistics.
    
    Reads template from 7-Templates/atlas-overview.md, fills in stats,
    and writes to 6-Outputs/Slides/atlas-overview-YYYYMMDD.slides.md.
    """
    vault = Path(CONFIG["atlas_vault"])
    template_path = vault / "7-Templates" / "atlas-overview.md"
    outputs_dir = vault / "6-Outputs" / "Slides"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(TZ)
    date_str = now.strftime("%Y-%m-%d %H:%M")
    file_stamp = now.strftime("%Y%m%d")

    # Count literature notes
    lit_dir = vault / "1-Literature"
    literature_count = 0
    area_counts = {}
    recent_literature = []
    reviewing_notes = []
    if lit_dir.exists():
        for md_file in lit_dir.rglob("*.md"):
            fm, _ = load_note_frontmatter(md_file)
            if fm.get("type") == "literature":
                literature_count += 1
                area = fm.get("area", "未分类")
                area_counts[area] = area_counts.get(area, 0) + 1
                date_val = fm.get("date", "")
                title = fm.get("title", md_file.stem)
                rel = os.path.relpath(str(md_file), str(vault))
                if rel.endswith(".md"):
                    rel = rel[:-3]
                recent_literature.append((date_val, title, rel, area))
                # Collect reviewing notes
                if fm.get("status", "").strip().lower() == "reviewing":
                    reviewing_notes.append((title, rel))
    recent_literature.sort(key=lambda x: x[0], reverse=True)

    # Count concepts & collect recent concepts with definitions
    concepts_dir = vault / "2-Concepts"
    concept_count = 0
    concept_highlights = []
    if concepts_dir.exists():
        for md_file in concepts_dir.glob("*.md"):
            fm, body = load_note_frontmatter(md_file)
            if fm.get("type") == "concept":
                concept_count += 1
                title = fm.get("title", md_file.stem)
                slug = md_file.stem
                concept_highlights.append((fm.get("date", ""), title, slug, body))
    concept_highlights.sort(key=lambda x: x[0], reverse=True)

    # Count atomic notes
    permanent_dir = vault / "3-Permanent"
    atom_count = 0
    if permanent_dir.exists():
        for md_file in permanent_dir.glob("*.md"):
            fm, _ = load_note_frontmatter(md_file)
            if fm.get("type") == "zettel":
                atom_count += 1

    # Build area breakdown table
    area_lines = []
    for area, count in sorted(area_counts.items(), key=lambda x: x[1], reverse=True):
        area_lines.append(f"- {area}: {count} 篇")
    area_breakdown = "\n".join(area_lines) if area_lines else "(暂无数据)"

    # Build recent literature list (with area)
    lit_lines = []
    for date_val, title, rel, area in recent_literature[:8]:
        lit_lines.append(f"- [[{rel}|{title}]] ({date_val}, {area})")
    recent_literature_md = "\n".join(lit_lines) if lit_lines else "(暂无数据)"

    # Build recent concepts with definition excerpt
    concept_lines = []
    for date_val, title, slug, body in concept_highlights[:8]:
        # Extract first ~30 chars after ## 定义
        def_match = re.search(r"## 定义\n+(.{0,60})", body or "", re.DOTALL)
        def_excerpt = ""
        if def_match:
            def_excerpt = re.sub(r"\s+", " ", def_match.group(1).strip())[:30]
        if def_excerpt:
            concept_lines.append(f"- [[2-Concepts/{slug}|{title}]] — {def_excerpt}")
        else:
            concept_lines.append(f"- [[2-Concepts/{slug}|{title}]]")
    recent_concepts_md = "\n".join(concept_lines) if concept_lines else "(暂无数据)"

    # Find orphan concepts (no incoming links from other vault files)
    orphan_concepts = []
    if concepts_dir.exists():
        for concept_md in concepts_dir.glob("*.md"):
            stem = concept_md.stem
            # Skip non-concept files
            fm_c, _ = load_note_frontmatter(concept_md)
            if fm_c.get("type") != "concept":
                continue
            # Search for wikilinks to this concept in all .md files except itself
            try:
                grep_result = subprocess.run(
                    ["grep", "-rl", "-E", f"\\[\\[{stem}[\\]|\\]]", str(vault)],
                    capture_output=True, text=True, timeout=30,
                    env={**os.environ, "LANG": "C"},
                )
                linked_files = grep_result.stdout.strip().split("\n") if grep_result.stdout.strip() else []
                # Remove the concept file itself from matches
                linked_files = [f for f in linked_files if os.path.normpath(f) != os.path.normpath(str(concept_md))]
                if not linked_files:
                    title_c = fm_c.get("title", stem)
                    orphan_concepts.append(f"- [[2-Concepts/{stem}|{title_c}]]")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            if len(orphan_concepts) >= 20:
                break
    orphan_concepts_md = "\n".join(orphan_concepts) if orphan_concepts else "(暂无孤立概念)"

    # Count contradictions across all concept pages
    contradiction_count = count_contradictions()
    contradiction_md = f"{contradiction_count} 条" if contradiction_count > 0 else "(无矛盾)"

    # Build reviewing notes list
    reviewing_lines = []
    for title, rel in reviewing_notes:
        reviewing_lines.append(f"- [[{rel}|{title}]]")
    reviewing_notes_md = "\n".join(reviewing_lines) if reviewing_lines else "(无待审核笔记)"

    # Read recent log entries (last 10)
    log_path = vault / "log.md"
    recent_log_md = "(暂无日志)"
    if log_path.exists():
        try:
            log_content = log_path.read_text(encoding="utf-8", errors="ignore")
            # Extract entries matching ## [timestamp]...
            log_entries = re.findall(r"^## .+$", log_content, re.MULTILINE)
            recent_log_md = "\n".join(log_entries[-10:]) if log_entries else "(暂无日志)"
        except Exception:
            pass

    # Read today's research suggestions
    suggestions_md = "(暂无建议)"
    today_suggestions = read_today_suggestions()
    if today_suggestions:
        suggestions_md = today_suggestions

    # Read template or use built-in default
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = """---
slideType: slide
theme: default
---

# Atlas 知识库概览

> 更新时间: {{date}}

---

# 统计摘要

| 指标 | 数量 |
|------|------|
| 📄 文献笔记 | {{literature_count}} |
| 💡 概念节点 | {{concept_count}} |
| ⚛️ 原子笔记 | {{atom_count}} |
| 🏷️ 知识领域 | {{area_count}} |

---

# 知识领域分布

{{area_breakdown}}

---

# 最近添加的文献

{{recent_literature}}

---

# 最近添加的概念

{{recent_concepts}}

---

# 孤立概念（无入链）

{{orphan_concepts}}

---

# 矛盾检测

{{contradictions}}

---

# 待审核笔记

{{reviewing_notes}}

---

# 操作日志（最近 10 条）

{{recent_log}}

---

# 💡 研究建议

{{suggestions}}
"""

    # Replace placeholders
    output = template
    output = output.replace("{{date}}", date_str)
    output = output.replace("{{literature_count}}", str(literature_count))
    output = output.replace("{{concept_count}}", str(concept_count))
    output = output.replace("{{atom_count}}", str(atom_count))
    output = output.replace("{{area_count}}", str(len(area_counts)))
    output = output.replace("{{recent_literature}}", recent_literature_md)
    output = output.replace("{{area_breakdown}}", area_breakdown)
    output = output.replace("{{recent_concepts}}", recent_concepts_md)
    output = output.replace("{{orphan_concepts}}", orphan_concepts_md)
    output = output.replace("{{contradictions}}", contradiction_md)
    output = output.replace("{{reviewing_notes}}", reviewing_notes_md)
    output = output.replace("{{recent_log}}", recent_log_md)
    output = output.replace("{{suggestions}}", suggestions_md)

    out_path = outputs_dir / f"atlas-overview-{file_stamp}.slides.md"
    out_path.write_text(output, encoding="utf-8")
    print(f"  📊 Overview generated: {out_path}")
    print(f"     文献: {literature_count}, 概念: {concept_count}, 原子: {atom_count}, 领域: {len(area_counts)}, 矛盾: {contradiction_count}")

    auto_git_commit("overview", date_str)

    return str(out_path)


# ── Lint Check ──────────────────────────────────────────────────────────────

def _grep_in_vault(pattern: str, vault_dir: str, exclude_path: str = "") -> List[str]:
    """Grep for pattern across all .md files in vault, return matching file paths.

    Args:
        pattern: regex pattern to search
        vault_dir: root vault directory
        exclude_path: absolute path to exclude from results
    """
    try:
        cmd = ["grep", "-rl", "-E", pattern, vault_dir, "--include=*.md"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                                env={**os.environ, "LANG": "C"})
        if result.returncode != 0:
            return []
        files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        if exclude_path:
            norm_exclude = os.path.normpath(exclude_path)
            files = [f for f in files if os.path.normpath(f) != norm_exclude]
        return files
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _find_orphans(directory: str, vault_dir: str) -> List[Tuple[str, str]]:
    """Find notes in directory with no incoming wikilinks from other vault files.

    Returns list of (stem, display_title) tuples.
    """
    orphans = []
    dir_path = Path(directory)
    if not dir_path.exists():
        return orphans

    for md_file in sorted(dir_path.glob("*.md")):
        stem = md_file.stem
        # Check for [[stem| or [[stem]] in any other .md file
        pattern = r"\[\[" + re.escape(stem) + r"[\]|\]]"
        linked = _grep_in_vault(pattern, vault_dir, exclude_path=str(md_file))
        if not linked:
            fm, _ = load_note_frontmatter(md_file)
            title = fm.get("title", stem)
            orphans.append((stem, title))
    return orphans


def _find_incomplete_concepts(concepts_dir: str) -> List[Tuple[str, str]]:
    """Find concept notes containing '待完善的概念节点'."""
    results = []
    dir_path = Path(concepts_dir)
    if not dir_path.exists():
        return results
    for md_file in sorted(dir_path.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            if "待完善的概念节点" in content:
                fm, _ = load_note_frontmatter(md_file)
                title = fm.get("title", md_file.stem)
                results.append((md_file.stem, title))
        except Exception:
            pass
    return results


def _find_literature_missing_concepts(lit_dir: str) -> List[Tuple[str, str]]:
    """Find literature notes that have '## 相关概念' section but it's empty or missing."""
    results = []
    dir_path = Path(lit_dir)
    if not dir_path.exists():
        return results
    for md_file in sorted(dir_path.rglob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            fm, _ = parse_frontmatter(content)
            if fm.get("type") != "literature":
                continue
            # Check if ## 相关概念 exists
            if "## 相关概念" in content:
                section = content.split("## 相关概念")[-1]
                # Get text before next ## heading
                next_heading = re.search(r"\n## ", section)
                section_text = section[:next_heading.start()] if next_heading else section
                # Check if the section has actual content (links, not just empty/TODO)
                lines = [l.strip() for l in section_text.split("\n") if l.strip() and not l.strip().startswith("<!--")]
                has_links = any("[[" in l for l in lines)
                if not has_links:
                    fm2, _ = load_note_frontmatter(md_file)
                    title = fm2.get("title", md_file.stem)
                    results.append((md_file.stem, title))
            else:
                # No ## 相关概念 at all — also flag
                fm2, _ = load_note_frontmatter(md_file)
                title = fm2.get("title", md_file.stem)
                results.append((md_file.stem, title))
        except Exception:
            pass
    return results


def _find_shallow_definitions(concepts_dir: str) -> List[Tuple[str, str, int]]:
    """Find concepts with ## 定义 section shorter than ~20 Chinese chars.

    Returns list of (stem, title, char_count) tuples.
    """
    MIN_DEF_CHARS = 20
    results = []
    dir_path = Path(concepts_dir)
    if not dir_path.exists():
        return results
    for md_file in sorted(dir_path.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            fm, _ = load_note_frontmatter(md_file)
            if fm.get("type") != "concept":
                continue
            # Extract ## 定义 section
            if "## 定义" not in content:
                results.append((md_file.stem, fm.get("title", md_file.stem), 0))
                continue
            section = content.split("## 定义")[-1]
            next_heading = re.search(r"\n## ", section)
            section_text = section[:next_heading.start()] if next_heading else section
            # Strip frontmatter-like lines, HTML comments, and whitespace
            clean_lines = []
            for l in section_text.split("\n"):
                l = l.strip()
                if not l or l.startswith("<!--") or l.startswith("---"):
                    continue
                clean_lines.append(l)
            def_text = "\n".join(clean_lines)
            # Count non-whitespace characters (rough char count)
            char_count = len(re.sub(r"\s+", "", def_text))
            if char_count < MIN_DEF_CHARS:
                results.append((md_file.stem, fm.get("title", md_file.stem), char_count))
        except Exception:
            pass
    return results


def run_lint_check():
    """Run a series of health checks on the Atlas vault and generate a report."""
    print("\n🔍 Running Atlas Lint Check...")
    vault_dir = CONFIG["atlas_vault"]
    concepts_dir = CONFIG["concepts_dir"]
    permanent_dir = CONFIG["permanent_dir"]
    lit_dir = CONFIG["literature_dir"]

    print("  📋 Checking MinerU preflight...")
    mineru_preflight = _collect_mineru_preflight()

    # 1. Orphan concepts (no incoming links)
    print("  📋 Checking orphan concepts...")
    orphan_concepts = _find_orphans(concepts_dir, vault_dir)

    # 2. Orphan atomic notes (no incoming links)
    print("  📋 Checking orphan atomic notes...")
    orphan_atoms = _find_orphans(permanent_dir, vault_dir)

    # 3. Incomplete concepts (待完善的概念节点)
    print("  📋 Checking incomplete concepts...")
    incomplete = _find_incomplete_concepts(concepts_dir)

    # 4. Contradiction count
    print("  📋 Counting contradictions...")
    contradiction_count = count_contradictions()

    # 5. Literature notes missing concept links
    print("  📋 Checking literature notes for concept links...")
    missing_concepts_lit = _find_literature_missing_concepts(lit_dir)

    # 6. Shallow definitions
    print("  📋 Checking concept definition quality...")
    shallow_defs = _find_shallow_definitions(concepts_dir)

    # 7. 检测 status=incomplete 的文献笔记
    print("  📋 Checking incomplete literature notes...")
    incomplete_notes = []
    for note_path in Path(CONFIG["literature_dir"]).rglob("*.md"):
        fm, _ = load_note_frontmatter(note_path)
        if fm.get("status") in ("incomplete", "draft"):
            incomplete_notes.append(str(note_path))
    if incomplete_notes:
        for n in incomplete_notes[:5]:
            print(f"    ⚠️  {n}")
    else:
        print(f"    ✅ 无 incomplete 文献笔记")

    # Build report
    now = datetime.now(TZ)
    date_str = now.strftime("%Y-%m-%d")
    stamp = now.strftime("%Y%m%d")

    report_lines = [
        "# Atlas Lint Report",
        "",
        f"> 日期: {date_str}",
        "",
        "## MinerU 预检",
        "",
        f"- enabled: {'yes' if mineru_preflight['enabled'] else 'no'}",
        f"- reason: {mineru_preflight['reason']}",
        f"- config: {mineru_preflight['config_path']} ({'exists' if mineru_preflight['config_exists'] else 'missing'})",
        f"- conclusion: {mineru_preflight['conclusion']}",
        "",
        "### 关键模型",
        "",
        *[
            f"- {item['name']}: {'exists' if item['exists'] else 'missing'} ({item['path']})"
            for item in mineru_preflight['models']
        ],
        "",
        *([
            "### 一键补齐命令",
            "",
            "```bash",
            *mineru_preflight['repair_commands'],
            "```",
            "",
        ] if mineru_preflight['repair_commands'] else []),
        "## 统计",
        "",
        f"- 孤立概念: {len(orphan_concepts)}",
        f"- 孤立原子笔记: {len(orphan_atoms)}",
        f"- 待完善概念: {len(incomplete)}",
        f"- 矛盾标记: {contradiction_count}",
        f"- 文献无概念链接: {len(missing_concepts_lit)}",
        f"- 低质量定义: {len(shallow_defs)}",
        f"- LLM 未完成笔记: {len(incomplete_notes)}",
        "",
    ]

    if orphan_concepts:
        report_lines.append("## 孤立概念")
        report_lines.append("")
        for stem, title in orphan_concepts:
            report_lines.append(f"- [[2-Concepts/{stem}|{title}]]")
        report_lines.append("")

    if orphan_atoms:
        report_lines.append("## 孤立原子笔记")
        report_lines.append("")
        for stem, title in orphan_atoms:
            report_lines.append(f"- [[3-Permanent/{stem}|{title}]]")
        report_lines.append("")

    if incomplete:
        report_lines.append("## 待完善概念")
        report_lines.append("")
        for stem, title in incomplete:
            report_lines.append(f"- [[2-Concepts/{stem}|{title}]]")
        report_lines.append("")

    if missing_concepts_lit:
        report_lines.append("## 文献无概念链接")
        report_lines.append("")
        for stem, title in missing_concepts_lit:
            report_lines.append(f"- [[{stem}|{title}]]")
        report_lines.append("")

    if shallow_defs:
        report_lines.append("## 低质量定义")
        report_lines.append("")
        for stem, title, char_count in shallow_defs:
            report_lines.append(f"- [[2-Concepts/{stem}|{title}]] — 定义仅 {char_count} 字")
        report_lines.append("")

    if incomplete_notes:
        report_lines.append("## LLM 未完成笔记")
        report_lines.append("")
        report_lines.append("> 这些笔记使用模板填充，LLM 未参与。可尝试 `--force` 重跑。")
        report_lines.append("")
        for n in incomplete_notes:
            report_lines.append(f"- {n}")
        report_lines.append("")

    report_content = "\n".join(report_lines)

    # Save report
    reports_dir = Path(vault_dir) / "6-Outputs" / "Reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"lint-report-{stamp}.md"
    report_path.write_text(report_content, encoding="utf-8")

    # Print summary to stdout
    print(f"\n📊 Lint Check Complete")
    print(f"  MinerU enabled: {'yes' if mineru_preflight['enabled'] else 'no'}")
    print(f"  MinerU reason: {mineru_preflight['reason']}")
    print(
        f"  MinerU config: {mineru_preflight['config_path']} "
        f"({'exists' if mineru_preflight['config_exists'] else 'missing'})"
    )
    for item in mineru_preflight["models"]:
        print(
            f"  MinerU model {item['name']}: "
            f"{'exists' if item['exists'] else 'missing'} ({item['path']})"
        )
    print(f"  MinerU conclusion: {mineru_preflight['conclusion']}")
    if mineru_preflight["repair_commands"]:
        print("  MinerU repair commands:")
        for cmd in mineru_preflight["repair_commands"]:
            print(f"    {cmd}")
    print(f"  孤立概念: {len(orphan_concepts)}")
    print(f"  孤立原子笔记: {len(orphan_atoms)}")
    print(f"  待完善概念: {len(incomplete)}")
    print(f"  矛盾标记: {contradiction_count}")
    print(f"  文献无概念链接: {len(missing_concepts_lit)}")
    print(f"  低质量定义: {len(shallow_defs)}")
    print(f"  LLM 未完成笔记: {len(incomplete_notes)}")
    print(f"  📝 Report: {report_path}")

    auto_git_commit("lint", date_str)

    return str(report_path)


# ── Atlas Query ────────────────────────────────────────────────────────────

def _token_estimate(text: str) -> int:
    """Rough token estimate: ~1.5 tokens per Chinese char, ~0.25 per English word."""
    zh_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    en_words = len(re.findall(r"[a-zA-Z]+", text))
    return int(zh_chars * 1.5 + en_words * 0.25 * 1.3)


def run_atlas_query(question: str):
    """Search the Atlas vault for relevant content and answer a question using LLM."""
    if not LLM_AVAILABLE:
        print("❌ LLM 模块不可用，无法执行 query")
        sys.exit(1)

    print(f"\n🔎 Atlas Query: {question}")
    vault_dir = Path(CONFIG["atlas_vault"])
    search_dirs = [
        CONFIG["literature_dir"],
        CONFIG["concepts_dir"],
        CONFIG["permanent_dir"],
    ]

    # 1. Tokenize question into keywords
    # Split into Chinese chars (2+ grams) and English words
    keywords = []
    # Extract Chinese phrases (2-4 chars)
    zh_segments = re.findall(r"[\u4e00-\u9fff]{2,8}", question)
    keywords.extend(zh_segments)
    # Extract English words
    en_words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,}", question)
    keywords.extend(w for w in en_words if len(w) >= 2)
    # Deduplicate
    keywords = list(dict.fromkeys(keywords))

    if not keywords:
        print("  ⚠️ 无法提取搜索关键词")
        sys.exit(1)

    print(f"  🔑 Keywords: {', '.join(keywords[:10])}")

    # 2. Grep search across all search dirs
    file_scores: Dict[str, int] = {}
    for search_dir in search_dirs:
        dir_path = Path(search_dir)
        if not dir_path.exists():
            continue
        for kw in keywords:
            try:
                # Use grep -c to count matches per file
                cmd = ["grep", "-rl", "-E", re.escape(kw), str(dir_path), "--include=*.md"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                        env={**os.environ, "LANG": "C"})
                if result.returncode == 0 and result.stdout.strip():
                    for fpath in result.stdout.strip().split("\n"):
                        fpath = fpath.strip()
                        if fpath:
                            file_scores[fpath] = file_scores.get(fpath, 0) + 1
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

    # Sort by score and take top-10
    sorted_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
    top_files = [f for f, s in sorted_files[:10]]

    if not top_files:
        print("  ⚠️ 未找到相关页面")
        print("  💡 知识库中没有与该问题相关的内容。")
        sys.exit(0)

    # 3. Read top files, respecting token budget
    MAX_TOKENS = 8000
    collected_texts = []
    collected_names = []
    total_tokens = 0

    for fpath in top_files:
        try:
            content = Path(fpath).read_text(encoding="utf-8", errors="ignore")
            fm, body = parse_frontmatter(content)
            title = fm.get("title", Path(fpath).stem)
            rel_path = os.path.relpath(fpath, CONFIG["atlas_vault"])
            if rel_path.endswith(".md"):
                wikilink = rel_path[:-3]
            else:
                wikilink = rel_path

            text_tokens = _token_estimate(body)
            if total_tokens + text_tokens > MAX_TOKENS and collected_texts:
                break

            collected_texts.append(f"### [[{wikilink}|{title}]]\n\n{body}")
            collected_names.append(wikilink)
            total_tokens += text_tokens
        except Exception:
            pass

    if not collected_texts:
        print("  ⚠️ 无法读取相关页面内容")
        sys.exit(1)

    context = "\n\n---\n\n".join(collected_texts)
    print(f"  📄 Loaded {len(collected_names)} files (~{total_tokens} tokens)")

    # 4. Call LLM
    query_prompt = f"""你是一个知识库助手。基于以下知识库内容回答用户问题。

## 知识库内容：
{context}

## 用户问题：
{question}

## 要求：
1. 基于知识库内容回答，不编造信息
2. 引用来源（用 [[wikilink]] 格式）
3. 如果知识库中没有相关信息，明确说明
4. 回答简洁，突出重点"""

    messages = [
        {"role": "system", "content": "你是 Atlas 知识库助手，基于知识库内容提供准确回答。"},
        {"role": "user", "content": query_prompt},
    ]

    try:
        answer = llm_chat(messages, max_tokens=2048)
    except Exception as e:
        print(f"  ❌ LLM 调用失败: {e}")
        sys.exit(1)

    # 5. Output answer
    print(f"\n{'='*60}")
    print(answer.strip())
    print(f"{'='*60}")
    print(f"\n📎 引用来源: {len(collected_names)} 个页面")
    for name in collected_names:
        print(f"  - [[{name}]]")

    # Save report
    now = datetime.now(TZ)
    stamp = now.strftime("%Y%m%d-%H%M%S")
    reports_dir = Path(CONFIG["atlas_vault"]) / "6-Outputs" / "Reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"query-{stamp}.md"

    report_content = f"""# Atlas Query Report

> 日期: {now.strftime("%Y-%m-%d %H:%M")}

## 问题

{question}

## 回答

{answer.strip()}

## 引用来源

"""
    report_content += "\n".join(f"- [[{name}]]" for name in collected_names)
    report_content += "\n\n---\n\n> 💡 如果此回答有价值，可手动将此报告移动到 `5-Areas/` 成为知识页面。\n"

    report_path.write_text(report_content, encoding="utf-8")
    print(f"\n📝 Report saved: {report_path}")

    return answer.strip()


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Atlas Ingest: Dropbox raw/ + Clippings incremental scan",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --source dropbox
  %(prog)s --source clippings --dry-run
  %(prog)s --source all
  %(prog)s --source dropbox --file /path/to/file.pdf
  %(prog)s --source lint
  %(prog)s --source query --question "什么是 Token Efficiency"
        """
    )
    parser.add_argument(
        "--source", "-s",
        choices=["dropbox", "clippings", "all", "review-only", "overview", "lint", "query", "synthesize"],
        required=True,
        help="Source to scan (overview: generate overview; lint: health check; query: Q&A)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Detect changes without processing"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        default=None,
        help="Process a single file (dropbox mode only)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess even if the source is already marked processed"
    )
    parser.add_argument(
        "--question", "-q",
        type=str,
        default=None,
        help="Question for query mode"
    )

    args = parser.parse_args()

    ensure_dirs()

    if args.source in ("dropbox", "all"):
        ingest_dropbox(dry_run=args.dry_run, single_file=args.file, force=args.force)

    if args.source in ("clippings", "all"):
        ingest_clippings(dry_run=args.dry_run, force=args.force)

    if args.source == "review-only":
        review_pending_notes()

    if args.source == "overview":
        generate_atlas_overview()

    if args.source == "lint":
        run_lint_check()

    if args.source == "query":
        if not args.question:
            print("❌ --source query 需要 --question 参数")
            sys.exit(1)
        run_atlas_query(args.question)

    if args.source == "synthesize":
        synthesize_all_areas()

    # After ingest, launch async local review for newly created notes
    if args.source in ("dropbox", "clippings", "all") and not args.dry_run:
        _launch_async_review()



if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
atlas-ingest post-processor: 概念提取 + 原子笔记提取
在 ingest.py 创建文献笔记后调用，对文献笔记进行二次处理。
"""

import os
from typing import Optional, List, Dict, Tuple
import re
import sys
from pathlib import Path

ATLAS_PATH = Path.home() / "pkm" / "atlas"
CONCEPTS_DIR = ATLAS_PATH / "2-Concepts"
PERMANENT_DIR = ATLAS_PATH / "3-Permanent"
VAULT_CONFIG = Path.home() / ".gorin-skills" / "openclaw" / "pkm-core" / "vault-config.yaml"


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  ⚠️ 读取 {path}: {e}")
        return ""


def write_file(path: Path, content: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"  ⚠️ 写入 {path}: {e}")
        return False


def extract_frontmatter(text: str) -> Tuple[dict, str]:
    """解析 YAML frontmatter，返回 (metadata, body)"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 3:].strip()
    meta = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip().strip('"\'')
    return meta, body


def to_frontmatter(meta: dict, body: str = "") -> str:
    """将 metadata + body 序列化为 frontmatter 格式"""
    lines = ["---"]
    for key, val in meta.items():
        if isinstance(val, list):
            lines.append(f"{key}:")
            for v in val:
                lines.append(f"  - \"{v}\"")
        elif val is None or val == "":
            lines.append(f"{key}: null")
        else:
            lines.append(f"{key}: \"{val}\"")
    lines.append("---")
    if body:
        lines.append("")
        lines.append(body)
    return "\n".join(lines)


def normalize_concept_name(name: str) -> str:
    """标准化概念名：首字母大写，空格转 -，去特殊字符"""
    name = name.strip()
    # 移除引号
    name = name.strip('「」""''《》【】()（）[]')
    # 如果是英文
    if re.match(r'^[A-Za-z]', name):
        # Title Case
        name = name.title()
    # 替换空格和特殊字符为 -
    name = re.sub(r'[\s/\\]+', '-', name)
    name = re.sub(r'[^\w\u4e00-\u9fff-]', '', name)
    return name.strip('-')


def slugify(name: str) -> str:
    """文件名安全化"""
    name = normalize_concept_name(name)
    return re.sub(r'-+', '-', name).strip('-')


def extract_concepts(body: str, title: str = "") -> List[str]:
    """从正文中提取概念候选"""
    concepts = set()

    # 1. 大写英文术语（2个以上大写字母开头的词组）
    #    如 "Progressive Disclosure", "Attention Dilution"
    eng_terms = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', body)
    for term in eng_terms:
        if len(term.split()) >= 2:
            concepts.add(term)

    # 2. 中文带引号的术语
    cn_quoted = re.findall(r'[「《]([^」》]{2,20})[」》]', body)
    cn_quoted += re.findall(r'"([^"]{2,20})"', body)
    for term in cn_quoted:
        if len(term) >= 2:
            concepts.add(term)

    # 3. 频率 >= 3 的名词短语（简单启发式）
    #    匹配 2-6 个汉字的组合
    cn_phrases = re.findall(r'[\u4e00-\u9fff]{2,6}', body)
    from collections import Counter
    phrase_counts = Counter(cn_phrases)
    # 过滤停用词
    stop_words = set("的是在了不是我们他们这个那个一个没有可以就是已经而且但是或者如果因为所以虽然然而".split())
    for phrase, count in phrase_counts.items():
        if count >= 3 and phrase not in stop_words and len(phrase) >= 2:
            concepts.add(phrase)

    # 4. 从标题中提取关键术语
    if title:
        title_terms = re.findall(r'[\u4e00-\u9fff]{2,8}', title)
        for term in title_terms:
            if len(term) >= 3:
                concepts.add(term)

    # 过滤
    concepts = {c for c in concepts if len(c) >= 2}
    # 过滤纯人名（通常 2-4 个词的英文且无其他线索）
    concepts = {c for c in concepts if not re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', c.strip())}
    # 过滤机构名中的人名模式
    concepts = {c for c in concepts if c.strip() not in ("Yudong", "Zongjie Li", "Hong Kong University")}
    # 过滤无意义的高频词
    useless = {'The', 'This', 'That', 'These', 'Those', 'However', 'Therefore',
               'Moreover', 'Furthermore', 'Additionally', 'Specifically', 'Notably'}
    concepts = {c for c in concepts if c.strip() not in useless}

    return sorted(concepts)


def find_existing_concept(concept_name: str) -> Optional[Path]:
    """检查概念是否已存在"""
    slug = slugify(concept_name)
    if CONCEPTS_DIR.joinpath(f"{slug}.md").exists():
        return CONCEPTS_DIR.joinpath(f"{slug}.md")
    # 模糊匹配：遍历所有概念文件，检查标题
    for f in CONCEPTS_DIR.glob("*.md"):
        content = read_file(f)
        if concept_name.lower() in content.lower()[:200]:
            return f
    return None


def create_concept_note(name, source_note, source_title="",
                        source_path="", existing_content="",
                        related_concepts=None):
    """创建或更新概念节点"""
    slug = slugify(name)
    note_path = CONCEPTS_DIR.joinpath(f"{slug}.md")

    if existing_content:
        # 更新已有概念：追加来源
        meta, body = extract_frontmatter(existing_content)
        sources = meta.get("sources", "").strip('[]"').split(",")
        source_ref = f"[[{source_note}]]"
        if source_ref not in str(sources):
            new_sources = [s.strip().strip('"\'') for s in sources if s.strip()]
            new_sources.append(source_ref)
            meta["sources"] = new_sources
        if related_concepts:
            existing_related = meta.get("related", "").strip('[]').split(",")
            existing_names = [r.strip().strip('"\'') for r in existing_related if r.strip()]
            for rc in related_concepts:
                rc_slug = slugify(rc)
                if rc_slug not in existing_names:
                    existing_names.append(rc_slug)
            meta["related"] = existing_names
        content = to_frontmatter(meta, body)
        print(f"  📝 更新概念: {name}")
    else:
        # 创建新概念
        meta = {
            "title": f'"{name}"',
            "type": "concept",
            "date": "2026-04-04",
            "sources": [f'[[{source_note}]]'],
            "tags": ["concept"],
            "created": "2026-04-04",
        }
        if related_concepts:
            meta["related"] = [slugify(rc) for rc in related_concepts]

        body = f"""# {name}

## 定义

（待补充 — 从来源文献中提取）

## 见于

- {source_title or source_note}

---
*概念首次提取自文献处理管线，后续发现新来源时追加*
"""
        content = to_frontmatter(meta, body)
        print(f"  ✨ 新概念: {name}")

    return write_file(note_path, content)


def extract_atoms(body, source_note, source_title=""):
    """从正文中提取原子笔记（关键发现/观点）"""
    atoms = []
    seen = set()

    # 匹配规则：以关键标记开头的句子或段落
    patterns = [
        # 中文
        r'(?m)^(?:发现[：:]?\s*)(.{10,200})',
        r'(?m)^(?:结果表明[：:]?\s*)(.{10,200})',
        r'(?m)^(?:实验证明[：:]?\s*)(.{10,200})',
        r'(?m)^(?:关键(?:洞察|发现|结论)[：:]?\s*)(.{10,200})',
        r'(?m)^(?:核心(?:贡献|观点|方法|思想)[：:]?\s*)(.{10,200})',
        r'(?m)^(?:结果[：:]?\s*)(.{10,200})',
        # 英文
        r'(?m)^(?:We (?:found|discovered|show|demonstrate|propose)s?[.:]\s*)(.{10,300})',
        r'(?m)^(?:Our (?:results?|findings?|approach|method)[.:]\s*)(.{10,300})',
        r'(?m)^(?:Key (?:insight|finding|contribution)s?[.:]\s*)(.{10,300})',
        r'(?m)^(?:The (?:results?|experiments?) (?:show|demonstrate|suggest|indicate)s?[.:]\s*)(.{10,300})',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, body):
            text = match.group(0).strip()
            if text and text not in seen:
                seen.add(text)
                atoms.append({"text": text})

    return atoms


def create_atom_note(text: str, source_note: str, source_title: str = "") -> bool:
    """创建原子笔记"""
    # 生成简短标题（取前30字）
    title = text[:40].strip()
    if len(text) > 40:
        title += "..."

    # 安全文件名
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d%H%M")
    safe_title = re.sub(r'[^\w\u4e00-\u9fff-]', '', title[:30]).strip('-')
    filename = f"{ts}-{safe_title}.md" if safe_title else f"{ts}-atom.md"
    note_path = PERMANENT_DIR.joinpath(filename)

    meta = {
        "title": f'"{title}"',
        "type": "zettel",
        "date": "2026-04-04",
        "source": f'[[{source_note}]]',
        "tags": ["zettel"],
        "created": "2026-04-04",
    }

    body = f"{text}\n\n[[{source_note}|相关：{source_title or source_note}]]"
    content = to_frontmatter(meta, body)

    if write_file(note_path, content):
        print(f"  💡 原子笔记: {title}")
        return True
    return False


def post_process(note_path):
    """对单篇文献笔记执行后处理"""
    note_path = Path(note_path)
    if not note_path.exists():
        print(f"❌ 文件不存在: {note_path}")
        return {"concepts": 0, "atoms": 0, "errors": 1}

    content = read_file(note_path)
    if not content:
        return {"concepts": 0, "atoms": 0, "errors": 1}

    meta, body = extract_frontmatter(content)
    note_name = note_path.stem
    title = meta.get("title", note_name)

    stats = {"concepts": 0, "atoms": 0, "errors": 0}

    # Step 1: 提取概念
    concepts = extract_concepts(body, title)
    all_concept_names = []
    for concept_name in concepts:
        existing = find_existing_concept(concept_name)
        existing_content = read_file(existing) if existing else ""
        other_concepts = [c for c in concepts if c != concept_name]
        if create_concept_note(concept_name, note_name, title,
                                existing_content=existing_content,
                                related_concepts=other_concepts):
            stats["concepts"] += 1
        all_concept_names.append(concept_name)

    # Step 2: 提取原子笔记
    atoms = extract_atoms(body, note_name, title)
    for atom in atoms:
        if create_atom_note(atom["text"], note_name, title):
            stats["atoms"] += 1

    # Step 3: 更新索引（追加到 papers-index.md）
    index_path = ATLAS_PATH / "4-Structure" / "Index" / "papers-index.md"
    if index_path.exists():
        index_content = read_file(index_path)
        if note_name not in index_content:
            # 找到对应领域分类或追加到末尾
            # 简单处理：追加到末尾
            # （更智能的分类由 ingest.py 处理）
            pass  # ingest.py 已处理索引

    print(f"\n✅ {note_name}: {stats['concepts']} 概念, {stats['atoms']} 原子笔记")
    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="atlas-ingest post-processor: 概念+原子笔记提取")
    parser.add_argument("note", help="文献笔记路径（单个 .md 文件）")
    parser.add_argument("--all", action="store_true", help="处理 1-Literature/ 下所有未处理的文献笔记")
    parser.add_argument("--concepts-only", action="store_true", help="只提取概念")
    parser.add_argument("--atoms-only", action="store_true", help="只提取原子笔记")
    args = parser.parse_args()

    if args.all:
        lit_dir = ATLAS_PATH / "1-Literature"
        total = {"concepts": 0, "atoms": 0, "errors": 0}
        for subdir in ["Papers", "Books", "Articles", "Repos"]:
            target = lit_dir / subdir
            if not target.exists():
                continue
            for f in sorted(target.glob("*.md")):
                print(f"\n📄 处理: {f.name}")
                result = post_process(f)
                for k in total:
                    total[k] += result[k]
        print(f"\n{'='*40}")
        print(f"总计: {total['concepts']} 概念, {total['atoms']} 原子笔记, {total['errors']} 错误")
    elif args.note:
        post_process(args.note)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

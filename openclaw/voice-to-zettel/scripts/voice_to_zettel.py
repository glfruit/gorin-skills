#!/usr/bin/env python3
"""
Voice to Zettel - 语音转永久笔记
复用: Whisper (转录) + PKM Core (保存 + 链接推荐)
"""

import os
import sys
import re
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# PKM Core paths
PKM_DIR = Path.home() / ".openclaw/pkm"
VAULT_PATH = Path.home() / "Workspace/PKM/octopus"

def transcribe_audio(audio_path: str) -> str:
    """使用系统 Whisper 转录音频"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 运行 whisper
        result = subprocess.run(
            ["whisper", audio_path, "--language", "Chinese", 
             "--output_format", "txt", "--output_dir", tmpdir],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Whisper error: {result.stderr}", file=sys.stderr)
            return ""
        
        # 读取转写结果
        txt_files = list(Path(tmpdir).glob("*.txt"))
        if txt_files:
            return txt_files[0].read_text(encoding='utf-8').strip()
        return ""

def extract_core_idea(text: str) -> str:
    """提取核心观点（第一句或前50字）"""
    # 取第一句
    first_sentence = text.split('。')[0].split('，')[0].strip()
    if len(first_sentence) > 50:
        first_sentence = first_sentence[:50] + "..."
    return first_sentence

def extract_keywords(text: str) -> list:
    """提取关键词"""
    # 匹配中英文词汇
    words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', text)
    # 去重并限制数量
    seen = set()
    keywords = []
    for w in words:
        w = w.lower()
        if w not in seen and len(keywords) < 5:
            seen.add(w)
            keywords.append(w)
    return keywords

def detect_idea_content(text: str) -> bool:
    """检测转写内容是否属于「想法」类"""
    idea_signals = [
        # 中文想法信号词
        r'我觉得', r'我认为', r'我想', r'应该', r'可以试试',
        r'如果.*就', r'为什么不', r'有个想法', r'突然想到',
        r'灵感', r'闪念', r'点子', r'方案', r'思路',
        r'或许可以', r'不如', r'要是.*呢', r'能不能',
        # 英文想法信号词
        r'(?i)idea', r'(?i)what if', r'(?i)maybe we',
        r'(?i)should', r'(?i)could try', r'(?i)how about',
    ]
    matches = sum(1 for p in idea_signals if re.search(p, text))
    # 命中 2 个以上信号词即视为想法类内容
    return matches >= 2

def find_related_notes(content: str) -> list:
    """使用 PKM Core 查找相关笔记"""
    # 复用 orphan_detector 的相似度算法
    sys.path.insert(0, str(PKM_DIR / "core"))
    try:
        from orphan_detector import OrphanDetector
        detector = OrphanDetector(str(VAULT_PATH))
        
        # 如果缓存存在，直接加载
        if detector._load_cache():
            # 提取内容关键词
            content_keywords = set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', content.lower()))
            
            related = []
            for filename in detector.file_to_path.keys():
                # 计算简单相似度
                file_keywords = set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', filename.lower()))
                if content_keywords and file_keywords:
                    intersection = len(content_keywords & file_keywords)
                    union = len(content_keywords | file_keywords)
                    similarity = intersection / union if union > 0 else 0
                    if similarity > 0.1:
                        related.append((filename, similarity))
            
            # 按相似度排序，取前5个
            related.sort(key=lambda x: x[1], reverse=True)
            return related[:5]
    except Exception as e:
        print(f"Error finding related notes: {e}", file=sys.stderr)
    
    return []

def create_zettel(transcript: str, audio_filename: str) -> str:
    """创建 Zettel 笔记"""
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M")
    
    # 提取核心观点
    core_idea = extract_core_idea(transcript)
    
    # 清理标题（用于文件名）
    safe_title = re.sub(r'[^\w\u4e00-\u9fff-]', '', core_idea[:30])
    filename = f"{timestamp}-{safe_title}.md"
    
    # 提取关键词
    keywords = extract_keywords(transcript)

    # 检测是否为想法类内容
    is_idea = detect_idea_content(transcript)

    # 查找相关笔记
    related = find_related_notes(transcript)

    # 构建标签
    tags_lines = "  - fleeting\n  - voice\n  - transcribed"
    if is_idea:
        tags_lines = "  - idea\n  - " + tags_lines.lstrip("  - ")

    note_type = "idea" if is_idea else "fleeting"

    # 构建笔记内容
    related_links = "\n".join([f"- [[{name}]]" for name, _ in related]) if related else "- （待补充）"

    content = f"""---
id: {timestamp}
title: {core_idea}
type: {note_type}
tags:
{tags_lines}
source: voice-note
created: {now.isoformat()}
modified: {now.isoformat()}
up: "[[Zettel Index]]"
---

# {core_idea}

## 完整转写内容
{transcript}

## Related Notes
{related_links}

## 思考与延伸
- [ ] 核心观点是什么？
- [ ] 与已有知识的关联？
- [ ] 需要进一步探索？

---

*语音转录于 {now.strftime("%Y-%m-%d %H:%M")}*
*原始音频: {audio_filename}*
"""
    
    # 保存文件
    output_dir = VAULT_PATH / "Zettels" / "1-Fleeting"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / filename
    output_path.write_text(content, encoding='utf-8')
    
    return str(output_path.relative_to(VAULT_PATH))

def main():
    if len(sys.argv) < 2:
        print("Usage: voice_to_zettel.py <audio_file>")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    audio_filename = Path(audio_path).name
    
    print("🎙️ 正在转录语音...", file=sys.stderr)
    
    # 转录
    transcript = transcribe_audio(audio_path)
    if not transcript:
        print("❌ 转录失败", file=sys.stderr)
        sys.exit(1)
    
    # 创建笔记
    output_path = create_zettel(transcript, audio_filename)

    # 输出结果（用于 Telegram 回复）
    core_idea = extract_core_idea(transcript)
    is_idea = detect_idea_content(transcript)
    idea_tag = "\n🏷️ 已标记为「想法」，将进入 idea-pipeline 研究队列" if is_idea else ""

    transcript_preview = transcript[:200] + ('...' if len(transcript) > 200 else '')

    print(f"""🎙️ 语音转写完成

💡 核心观点: {core_idea}

📝 已保存: {output_path}{idea_tag}

📌 讨论上下文:
- 父笔记: {core_idea}
- 路径: {output_path}
- 核心内容: {transcript_preview}

💬 进入讨论模式——""")

if __name__ == '__main__':
    main()

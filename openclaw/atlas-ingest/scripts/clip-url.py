#!/Users/gorin/.gorin-skills/openclaw/atlas-ingest/.venv/bin/python
"""
clip-url.py: URL → 9-Clippings 剪藏

使用 web-reader 抓取网页，保存为 Obsidian 兼容的 .md 到 atlas/9-Clippings/
保存后下次 heartbeat 自动触发 atlas-ingest 管线处理。

Usage:
    ~/.gorin-skills/openclaw/atlas-ingest/.venv/bin/python ~/.gorin-skills/openclaw/atlas-ingest/scripts/clip-url.py <url> [--title "自定义标题"] [--tags "tag1,tag2"]
"""

import argparse
import json
import re
import subprocess
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

TZ = timezone(timedelta(hours=8))
CLIPPINGS_DIR = Path.home() / "pkm" / "atlas" / "9-Clippings"
ASSETS_DIR = Path.home() / "pkm" / "atlas" / "8-Assets"
WEB_READER = Path.home() / ".openclaw" / "skills" / "web-reader" / "scripts" / "web-reader.sh"

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "tiff", "tif", "ico", "avif"}
IMAGE_CONTENT_TYPES = {
    "image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml",
    "image/bmp", "image/tiff", "image/avif", "image/x-icon",
}


def sanitize_filename(name, max_len=80):
    """清理文件名"""
    name = re.sub(r'[\\/:*?"<>|]', '-', name)
    name = re.sub(r'-{2,}', '-', name).strip('- .')
    return name[:max_len]


def run_web_reader(url):
    """调用 web-reader 抓取网页"""
    cmd = ["bash", str(WEB_READER), url, "--json", "--max-chars", "50000"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        output = result.stdout

        if output.strip().startswith("{"):
            data = json.loads(output)
            return {
                "title": data.get("title", ""),
                "url": data.get("url", url),
                "author": data.get("author", ""),
                "published": data.get("published", ""),
                "site": data.get("site", ""),
                "content": data.get("content", data.get("text", "")),
                "description": data.get("description", ""),
            }

        return _parse_frontmatter_output(output, url)

    except subprocess.TimeoutExpired:
        raise RuntimeError("web-reader 超时（60s）")
    except json.JSONDecodeError:
        raise RuntimeError("web-reader 输出解析失败")


def _parse_frontmatter_output(text, url):
    """解析 web-reader 的 YAML front matter + markdown 输出"""
    if not text.startswith("---"):
        return {"title": "", "url": url, "content": text}

    end = text.find("---", 3)
    if end == -1:
        return {"title": "", "url": url, "content": text}

    fm_text = text[3:end].strip()
    body = text[end + 3:].strip()

    meta = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip().strip('"\'').strip()

    return {
        "title": meta.get("title", ""),
        "url": meta.get("url", url),
        "author": meta.get("author", ""),
        "published": meta.get("published", ""),
        "site": meta.get("site", ""),
        "description": meta.get("description", meta.get("summary", "")),
        "content": body,
    }


def _download_image(url):
    """Download image URL to 8-Assets/, return local filename or None on failure."""
    try:
        import requests
        resp = requests.get(url, timeout=30, stream=True)
        if resp.status_code != 200:
            return None
        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type and content_type not in IMAGE_CONTENT_TYPES:
            return None

        # Determine extension
        url_path = urlparse(url).path
        url_ext = Path(url_path).suffix.lower().lstrip(".")
        if url_ext in IMAGE_EXTENSIONS:
            ext = url_ext
        elif content_type.startswith("image/"):
            ext = content_type.split("/")[1]
            if ext == "svg+xml":
                ext = "svg"
        else:
            ext = "png"

        # Generate unique filename
        basename = Path(url_path).stem[:60] if Path(url_path).stem else str(uuid.uuid4())[:8]
        safe_base = re.sub(r'[^A-Za-z0-9._-]', '-', basename)[:60].strip('-') or str(uuid.uuid4())[:8]
        filename = f"{safe_base}.{ext}"

        # Handle collision
        if (ASSETS_DIR / filename).exists():
            filename = f"{safe_base}-{uuid.uuid4().hex[:6]}.{ext}"

        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        dest = ASSETS_DIR / filename
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        print(f"    📷 下载图片: {filename} ({len(resp.content)} bytes)")
        return filename
    except Exception as e:
        print(f"    ⚠️ 图片下载失败 ({url}): {e}")
        return None


def localize_images(content):
    """Find ![...](http/https://...) image links and download them locally.

    Returns (new_content, downloaded_count).
    """
    # Match markdown images with http/https URLs
    pattern = re.compile(r'(!\[[^\]]*\]\()(https?://[^\)]+)\)')
    matches = list(pattern.finditer(content))
    if not matches:
        return content, 0

    downloaded = 0
    # Replace in reverse order to preserve positions
    for m in reversed(matches):
        url = m.group(2)
        # Skip data: URLs
        if url.startswith("data:"):
            continue
        local_name = _download_image(url)
        if local_name:
            new_ref = m.group(1) + "../8-Assets/" + local_name + ")"
            content = content[:m.start()] + new_ref + content[m.end():]
            downloaded += 1

    return content, downloaded


def save_to_clippings(data, custom_title=None, tags=None):
    """保存到 9-Clippings 目录"""
    CLIPPINGS_DIR.mkdir(parents=True, exist_ok=True)

    title = custom_title or data.get("title", "") or "Untitled"
    safe_name = sanitize_filename(title)
    out_path = CLIPPINGS_DIR / f"{safe_name}.md"

    if out_path.exists():
        base = safe_name
        idx = 2
        while out_path.exists():
            out_path = CLIPPINGS_DIR / f"{base}-{idx}.md"
            idx += 1

    now = datetime.now(TZ)

    fm_lines = [
        "---",
        f"title: {title}",
        f'source: "{data.get("url", "")}"',
        f'author: {data.get("author", "") or ""}',
        f'published: {data.get("published", "") or ""}',
        f'created: {now.strftime("%Y-%m-%d")}',
    ]

    desc = data.get("description", "")
    if desc:
        desc = desc.replace('"', '\\"')
        fm_lines.append(f'description: "{desc}"')

    if tags:
        fm_lines.append(f"tags: [{', '.join(tags)}]")
    else:
        fm_lines.append("tags: [clipping]")

    fm_lines.append("status: pending")
    fm_lines.append("---")
    fm_lines.append("")

    content = data.get("content", "") or f"<!-- 待抓取：{data.get('url', '')} -->"

    # Localize remote images
    content, img_count = localize_images(content)
    if img_count:
        print(f"  📷 本地化 {img_count} 张图片")

    out_path.write_text("\n".join(fm_lines) + "\n" + content + "\n", encoding="utf-8")
    return str(out_path)


def main():
    parser = argparse.ArgumentParser(description="URL → atlas 9-Clippings 剪藏")
    parser.add_argument("url", help="网页 URL")
    parser.add_argument("--title", "-t", help="自定义标题")
    parser.add_argument("--tags", help="标签（逗号分隔）")
    parser.add_argument("--no-read", action="store_true", help="只创建占位，不抓取正文")
    parser.add_argument("--open", action="store_true", help="同时在浏览器中打开")
    args = parser.parse_args()

    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []

    print(f"📎 剪藏: {args.url}")

    if args.no_read:
        data = {"url": args.url, "title": args.title or "Pending"}
        out_path = save_to_clippings(data, custom_title=args.title, tags=tags)
        print(f"  ✅ 占位笔记已创建: {out_path}")
        print("  ⏳ 下次 heartbeat 将自动处理")
        return

    print("  📖 抓取正文...")
    try:
        data = run_web_reader(args.url)
    except Exception as exc:
        print(f"  ❌ 抓取失败: {exc}")
        data = {
            "url": args.url,
            "title": args.title or "Pending",
            "content": f"<!-- 抓取失败: {exc} -->",
        }
        out_path = save_to_clippings(data, custom_title=args.title, tags=tags)
        print(f"  ⚠️ 已创建占位笔记（抓取失败）: {out_path}")
        return

    print(f"  📰 标题: {data.get('title', args.title or '')}")
    print(f"  👤 作者: {data.get('author', 'N/A')}")
    print(f"  📝 内容: {len(data.get('content', ''))} 字符")

    out_path = save_to_clippings(data, custom_title=args.title, tags=tags)
    print(f"  ✅ 已保存: {out_path}")
    print("  ⏳ 下次 heartbeat 将自动编译（→ 文献笔记 + 概念 + 原子笔记）")

    if args.open:
        subprocess.Popen(["open", args.url])


if __name__ == "__main__":
    main()

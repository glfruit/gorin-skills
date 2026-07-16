#!/usr/bin/env python3
"""
通用网页正文提取脚本（基于 Scrapling + html2text）
返回干净的 Markdown 格式，效果与 Jina Reader 相当。
用于 article-writer skill 的二级内容提取方案（Jina 超限或失败时使用）

用法：
  python3 fetch.py <url> [max_chars]

示例：
  python3 fetch.py https://example.com/article 12000
  python3 fetch.py https://mp.weixin.qq.com/s/xxx 30000

输出：
  Markdown 格式正文，截断至 max_chars（默认 30000）
  图片使用原始 URL 内嵌在 Markdown 中（data-src 懒加载已自动处理）
"""

import sys
import re
from datetime import datetime, timezone, timedelta
import html2text
from scrapling.fetchers import Fetcher


class QuietFetcher(Fetcher):
    """Compat wrapper: avoid Scrapling BaseFetcher.__init__ deprecation warning."""

    def __init__(self, *args, **kwargs):
        # Upstream __init__ only emits a deprecation warning and has no effect.
        # Skip it until Scrapling exposes a clean non-warning constructor path.
        pass


def fix_lazy_images(html_raw):
    """
    微信公众号等平台用 data-src 懒加载图片，src 为占位符。
    将 data-src 的值提升为 src，确保 html2text 能正确渲染图片。
    """
    # 先把 data-src 提升为 src（如果 src 不存在或是占位）
    html_raw = re.sub(
        r'<img([^>]*?)\sdata-src="([^"]+)"([^>]*?)>',
        lambda m: f'<img{m.group(1)} src="{m.group(2)}"{m.group(3)}>',
        html_raw
    )
    return html_raw


def _first_match(patterns, text):
    for pattern in patterns:
        m = re.search(pattern, text, re.S | re.I)
        if m:
            return m.group(1).strip()
    return ""


def _normalize_text(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def _format_unix_ts(ts):
    try:
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc).astimezone(timezone(timedelta(hours=8)))
        return dt.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return ""


def _dedupe_names(names):
    deduped = []
    for name in names:
        name = _normalize_text(name)
        if name and name not in deduped:
            deduped.append(name)
    return deduped


def _extract_names_from_citation_line(line):
    if not line:
        return []
    line = re.sub(r'[*`_]', '', line)
    line = line.split('.20', 1)[0]
    line = line.split('．20', 1)[0]
    parts = re.split(r'[，,、]', line)
    names = []
    for part in parts:
        part = _normalize_text(part).replace(' ', '')
        if not part or part in {'等', '作者', '引用格式'}:
            continue
        if re.fullmatch(r'[\u4e00-\u9fff·]{2,8}', part):
            names.append(part)
    return _dedupe_names(names)


def _extract_names_from_spaced_line(line):
    tokens = [t for t in re.split(r'\s+', line.strip()) if t]
    names = []
    i = 0
    while i < len(tokens):
        cur = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ''
        if re.fullmatch(r'[\u4e00-\u9fff]', cur) and re.fullmatch(r'[\u4e00-\u9fff]{1,2}', nxt):
            names.append(cur + nxt)
            i += 2
            continue
        if re.fullmatch(r'[\u4e00-\u9fff]{2,4}(?:·[\u4e00-\u9fff]{1,4})?', cur):
            names.append(cur)
        i += 1
    return _dedupe_names(names)


def _extract_wechat_body_author(md_text, title=''):
    citation_line = _first_match([
        r'引用格式\s*\n+([^\n]+)',
    ], md_text)
    citation_names = _extract_names_from_citation_line(citation_line)
    if len(citation_names) >= 2:
        return '、'.join(citation_names)

    lines = [_normalize_text(line) for line in md_text.splitlines()]
    lines = [line for line in lines if line]

    title_norm = _normalize_text(title)
    title_idx = -1
    for idx, line in enumerate(lines[:40]):
        if title_norm and line == title_norm:
            title_idx = idx
            break

    candidate_window = lines[max(0, title_idx + 1): min(len(lines), title_idx + 8)] if title_idx >= 0 else lines[:20]

    for line in candidate_window:
        if any(token in line for token in ['摘 要', '关键词', '作者简介', '基金项目', '引用格式', '国际与比较教育']):
            continue
        if not re.fullmatch(r'[A-Za-z\u4e00-\u9fff·,，、\s]+', line):
            continue
        names = _extract_names_from_spaced_line(line)
        if len(names) >= 2:
            return '、'.join(names)

    bio_line = _first_match([
        r'作者简介[:：]\*+([^\n]+)',
        r'作者简介[:：]\s*([^\n]+)',
    ], md_text)
    if bio_line:
        bio_line = re.sub(r'[*`_]', '', bio_line)
        names = re.findall(r'([\u4e00-\u9fff]{2,4})\s*[，,]', bio_line)
        names = _dedupe_names(names)
        if names:
            return '、'.join(names)

    return ''


def extract_metadata(url, html_raw, md_text=""):
    metadata = {
        'title': '',
        'author': '',
        'published': '',
        'site': '',
    }

    if 'mp.weixin.qq.com' in url:
        title = _first_match([
            r'<meta\s+property="og:title"\s+content="([^"]+)"',
            r'var\s+msg_title\s*=\s*["\']([^"\']+)',
            r'<title>(.*?)</title>',
        ], html_raw)
        page_author = _first_match([
            r'<meta\s+name="author"\s+content="([^"]+)"',
        ], html_raw)
        body_author = _extract_wechat_body_author(md_text, title)
        site = _first_match([
            r'<a[^>]+id="js_name"[^>]*>\s*([^<]+?)\s*</a>',
        ], html_raw)
        published = _first_match([
            r'publish_time%22%3A(\d{10})',
            r'"publish_time"\s*:\s*(\d{10})',
            r'\bct\s*=\s*(\d{10})',
        ], html_raw)

        metadata['title'] = _normalize_text(title)
        metadata['author'] = _normalize_text(body_author or page_author)
        metadata['published'] = _format_unix_ts(published) if published else ''
        metadata['site'] = _normalize_text(site) or 'mp.weixin.qq.com'
        return metadata

    metadata['title'] = _normalize_text(_first_match([
        r'<meta\s+property="og:title"\s+content="([^"]+)"',
        r'<title>(.*?)</title>',
        r'^#\s+(.+)$',
    ], html_raw + '\n' + md_text))
    metadata['author'] = _normalize_text(_first_match([
        r'<meta\s+name="author"\s+content="([^"]+)"',
        r'<meta\s+property="article:author"\s+content="([^"]+)"',
        r'by\s+([^\n|]+)',
    ], html_raw + '\n' + md_text))
    metadata['published'] = _normalize_text(_first_match([
        r'<meta\s+property="article:published_time"\s+content="([^"]+)"',
        r'<time[^>]*datetime="([^"]+)"',
        r'<meta\s+name="date"\s+content="([^"]+)"',
    ], html_raw))
    return metadata


def scrapling_fetch(url, max_chars=30000):
    page = QuietFetcher().get(
        url,
        headers={"Referer": "https://www.google.com/search?q=site"}
    )

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0  # 不自动换行

    page_html = page.html_content

    # 微信公众号专用选择器
    if "mp.weixin.qq.com" in url:
        selectors = ["div#js_content", "div.rich_media_content"]
    else:
        selectors = [
            'article',
            'main',
            '.post-content',
            '.entry-content',
            '.article-body',
            '[class*="body"]',
            '[class*="content"]',
            '[class*="article"]',
        ]

    for selector in selectors:
        els = page.css(selector)
        if els:
            html_raw = fix_lazy_images(els[0].html_content)
            md = h.handle(html_raw)
            md = re.sub(r'\n{3,}', '\n\n', md).strip()
            if len(md) > 300:
                metadata = extract_metadata(url, page_html, md)
                return md[:max_chars], selector, metadata

    # fallback：全页转 Markdown
    html_raw = fix_lazy_images(page_html)
    md = h.handle(html_raw)
    md = re.sub(r'\n{3,}', '\n\n', md).strip()
    metadata = extract_metadata(url, page_html, md)
    return md[:max_chars], 'body(fallback)', metadata


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 fetch.py <url> [max_chars]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    max_chars = int(sys.argv[2]) if len(sys.argv) > 2 else 30000

    text, selector, metadata = scrapling_fetch(url, max_chars)
    print(text)

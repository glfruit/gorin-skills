#!/usr/bin/env python3
"""
build_digest.py — Build AI Builder Daily digest in a single execution.

Replaces the multi-turn agent pipeline (30+ tool calls) with one script:
  1. Load state (last-digest.json)
  2. Fetch English feeds (GitHub JSON)
  3. Fetch Chinese sources (Tavily API)
  4. Dedup + filter
  5. Generate HTML, TXT, meta.json
  6. Print structured summary to stdout

Constraints: Python 3.14, stdlib only (urllib), idempotent, 30s HTTP timeout.
"""

import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape as html_escape

# ── Paths ──────────────────────────────────────────────────────────────────

HOME = Path.home()
STATE_FILE = HOME / ".openclaw/workspace-daily-collector/ai-image-digest/state/last-digest.json"
OUTPUT_DIR = HOME / ".openclaw/workspace-daily-collector/ai-image-digest/output"
TEMPLATE_DIR = Path(__file__).parent / "templates"

FEED_X_URL = "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-x.json"
FEED_PODCASTS_URL = "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-podcasts.json"
FEED_BLOGS_URL = "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-blogs.json"

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_URL = "https://api.tavily.com/search"

HTTP_TIMEOUT = 30

# Chinese AI media domains for filtering
ZH_DOMAINS = {
    "36kr.com", "m.36kr.com", "www.36kr.com",
    "jiqizhixin.com", "www.jiqizhixin.com", "mp.weixin.qq.com",
    "qbitai.com", "www.qbitai.com",
    "newrank.cn", "www.newrank.cn",
    "myeducs.cn", "ailab.cn", "aibase.com",
    "syncedreview.com", "www.jiqizhixin.com",
    "csdn.net", "www.csdn.net",
    "thepaper.cn", "www.thepaper.cn",
    "finance.sina.com.cn", "tech.sina.com.cn",
    "microsoft.com",  # sometimes surfaces Chinese content
}

# ── Helpers ────────────────────────────────────────────────────────────────

CST = timezone(timedelta(hours=8))


def http_get_json(url: str, timeout: int = HTTP_TIMEOUT):
    """Fetch JSON via GET."""
    req = urllib.request.Request(url, headers={"User-Agent": "OpenClaw-Digest/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post_json(url: str, body: dict, timeout: int = HTTP_TIMEOUT):
    """Post JSON and return parsed response."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "OpenClaw-Digest/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_state() -> dict:
    """Load last-digest.json or return empty state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "seen_urls_tweets": [],
        "seen_urls_podcasts": [],
        "seen_urls_blogs": [],
        "seen_urls_zh": [],
        "last_run": None,
        "run_count": 0,
        "runs": [],
        "errors": [],
    }


def save_state(state: dict):
    """Persist state to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ── Data Fetching ──────────────────────────────────────────────────────────

def fetch_tweets(state: dict):
    """Fetch and dedup tweets from feed-x.json."""
    try:
        data = http_get_json(FEED_X_URL)
    except Exception as e:
        print(f"WARN: Failed to fetch feed-x.json: {e}", file=sys.stderr)
        return []

    seen = set(state.get("seen_urls_tweets", []))
    all_tweets = []

    for user in data.get("x", []):
        name = user.get("name", "?")
        handle = user.get("handle", "?")
        for t in user.get("tweets", []):
            url = t.get("url", "")
            if url in seen:
                continue
            likes = t.get("likes", 0)
            text = t.get("text", "")
            is_quote = t.get("isQuote", False)

            # Filter: low engagement
            if likes < 20:
                continue
            # Filter: short quote without commentary
            if is_quote and len(text) < 50:
                continue

            all_tweets.append({
                "type": "twitter",
                "name": name,
                "handle": handle,
                "text": text,
                "url": url,
                "likes": likes,
                "retweets": t.get("retweets", 0),
                "created_at": t.get("createdAt", ""),
                "is_quote": is_quote,
            })

    # Sort by likes desc, cap
    all_tweets.sort(key=lambda x: x["likes"], reverse=True)
    return all_tweets[:15]


def fetch_podcasts(state: dict):
    """Fetch and dedup podcasts."""
    try:
        data = http_get_json(FEED_PODCASTS_URL)
    except Exception as e:
        print(f"WARN: Failed to fetch feed-podcasts.json: {e}", file=sys.stderr)
        return []

    seen = set(state.get("seen_urls_podcasts", []))
    items = []
    for p in data.get("podcasts", []):
        url = p.get("url", "")
        if url and url not in seen:
            items.append({
                "type": "podcast",
                "name": p.get("name", p.get("title", "Unknown")),
                "title": p.get("title", ""),
                "text": p.get("description", p.get("summary", "")),
                "url": url,
            })
    return items


def fetch_blogs(state: dict):
    """Fetch and dedup blogs."""
    try:
        data = http_get_json(FEED_BLOGS_URL)
    except Exception as e:
        print(f"WARN: Failed to fetch feed-blogs.json: {e}", file=sys.stderr)
        return []

    seen = set(state.get("seen_urls_blogs", []))
    items = []
    for b in data.get("blogs", []):
        url = b.get("url", "")
        if url and url not in seen:
            items.append({
                "type": "blog",
                "name": b.get("author", b.get("name", "Unknown")),
                "title": b.get("title", ""),
                "text": b.get("summary", b.get("description", "")),
                "url": url,
            })
    return items


def fetch_chinese(state: dict):
    """Fetch Chinese AI news via Tavily API."""
    if not TAVILY_API_KEY:
        print("WARN: TAVILY_API_KEY not set, skipping Chinese sources", file=sys.stderr)
        return []

    seen = set(state.get("seen_urls_zh", []))
    items = []

    queries = [
        "AI 人工智能 最新进展 2026",
        "大模型 LLM 最新动态",
    ]

    for query in queries:
        try:
            resp = http_post_json(TAVILY_URL, {
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": 8,
                "include_answer": False,
            })
        except Exception as e:
            print(f"WARN: Tavily query '{query}' failed: {e}", file=sys.stderr)
            continue

        for r in resp.get("results", []):
            url = r.get("url", "")
            if url in seen:
                continue
            # Filter: prefer Chinese AI media domains
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower()
            # Accept if domain matches known Chinese/AI media or contains Chinese chars in title
            title = r.get("title", "")
            has_zh = bool(re.search(r'[\u4e00-\u9fff]', title))
            if not has_zh and not any(d in domain for d in ZH_DOMAINS):
                continue

            # Friendly source name from domain
            source_name_map = {
                "36kr.com": "36氪", "m.36kr.com": "36氪", "www.36kr.com": "36氪",
                "jiqizhixin.com": "机器之心", "www.jiqizhixin.com": "机器之心",
                "qbitai.com": "量子位", "www.qbitai.com": "量子位",
                "zhuanlan.zhihu.com": "知乎", "www.zhihu.com": "知乎",
                "mp.weixin.qq.com": "微信公众号",
                "stcn.com": "证券时报", "www.stcn.com": "证券时报",
                "thepaper.cn": "澎湃新闻", "www.thepaper.cn": "澎湃新闻",
                "microsoft.com": "微软研究院",
                "ibm.com": "IBM",
                "youtube.com": "YouTube", "www.youtube.com": "YouTube",
                "zoom.com": "Zoom",
            }
            source_name = source_name_map.get(domain, title[:15] if title else domain)

            items.append({
                "type": "chinese",
                "name": source_name,
                "title": title,
                "text": r.get("content", "")[:200],
                "url": url,
                "domain": domain,
            })

    # Dedup by URL
    seen_urls = set()
    unique = []
    for item in items:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            unique.append(item)

    return unique[:8]


# ── HTML Generation ────────────────────────────────────────────────────────

def make_item_html(item: dict, num: int) -> str:
    """Generate HTML for a single item."""
    t = item["type"]
    name = html_escape(item.get("name", "?"))
    handle = html_escape(item.get("handle", item.get("domain", "")))
    text = item.get("text", "")
    url = item["url"]
    likes = item.get("likes", 0)

    # Highlight first sentence
    content_html = highlight_first_sentence(html_escape(text))

    # Stats
    if t == "twitter":
        stats = f'❤️ {likes}'
    elif t == "podcast":
        stats = '🎙 播客'
    elif t == "blog":
        stats = '📝 博客'
    else:
        stats = '📰 中文'

    avatar_char = html_escape(name[0] if name else "?")

    # URL display: domain + short path
    from urllib.parse import urlparse
    parsed = urlparse(url)
    url_display = parsed.netloc + (parsed.path[:30] if len(parsed.path) > 30 else parsed.path)

    return f'''<div class="item {t}-item">
  <div class="item-meta">
    <span class="item-num">{num}</span>
    <div class="item-avatar {t}">{avatar_char}</div>
    <span class="item-name">{name}</span>
    <span class="item-handle">@{handle}</span>
    <span class="item-stats {t}-stats">{stats}</span>
  </div>
  <div class="item-content">{content_html}</div>
  <div class="item-link"><a href="{url}">🔗 {url_display}</a></div>
</div>'''


def highlight_first_sentence(text: str) -> str:
    """Put first sentence in <strong>, rest as normal text. Max highlight ~100 chars."""
    if not text:
        return ""

    # Find first sentence boundary
    boundary = len(text)
    for i, ch in enumerate(text):
        if i > 20 and ch in ('。', '！', '？', '.', '!', '?', '\n'):
            boundary = i + 1
            break
        if i >= 100:
            boundary = i
            break

    first = text[:boundary]
    rest = text[boundary:]
    if rest:
        return f"<strong>{first}</strong>{rest}"
    return f"<strong>{first}</strong>"


def make_section_html(section_type: str, title: str, icon: str, items: list, start_num: int) -> tuple[str, int]:
    """Generate a section HTML block. Returns (html, next_num)."""
    if not items:
        return "", start_num

    items_html = ""
    num = start_num
    for item in items:
        items_html += "\n" + make_item_html(item, num)
        num += 1

    count = len(items)
    html = f'''<div class="section">
  <div class="section-header">
    <div class="section-icon {section_type}">{icon}</div>
    <div class="section-title">{title}</div>
    <div class="section-count">{count} 条精选</div>
  </div>
  <div class="items">{items_html}
  </div>
</div>'''
    return html, num


def generate_html(date_str: str, tweets: list, podcasts: list, blogs: list, chinese: list) -> str:
    """Generate full HTML from template."""
    template_path = TEMPLATE_DIR / "digest.html"
    with open(template_path) as f:
        template = f.read()

    num = 1
    podcast_html, num = make_section_html("podcast", "Podcasts", "🎙", podcasts, num)
    twitter_html, num = make_section_html("twitter", "Twitter / X", "𝕏", tweets, num)
    blog_html, num = make_section_html("blog", "Blogs", "📝", blogs, num)
    chinese_html, num = make_section_html("chinese", "中文媒体", "🇨🇳", chinese, num)

    total = len(tweets) + len(podcasts) + len(blogs) + len(chinese)
    parts = []
    if tweets:
        parts.append(f"X {len(tweets)}")
    if podcasts:
        parts.append(f"播客 {len(podcasts)}")
    if blogs:
        parts.append(f"博客 {len(blogs)}")
    if chinese:
        parts.append(f"中文 {len(chinese)}")
    stats = f"共 {total} 条 · " + " · ".join(parts)

    html = template.replace("{{DATE}}", date_str)
    html = html.replace("{{PODCAST_SECTION}}", podcast_html)
    html = html.replace("{{TWITTER_SECTION}}", twitter_html)
    html = html.replace("{{BLOG_SECTION}}", blog_html)
    html = html.replace("{{CHINESE_SECTION}}", chinese_html)
    html = html.replace("{{STATS}}", stats)

    return html


# ── TXT Generation ─────────────────────────────────────────────────────────

def generate_txt(date_str: str, tweets: list, podcasts: list, blogs: list, chinese: list) -> str:
    """Generate plain text digest."""
    total = len(tweets) + len(podcasts) + len(blogs) + len(chinese)
    parts = []
    if tweets:
        parts.append(f"X {len(tweets)}")
    if podcasts:
        parts.append(f"播客 {len(podcasts)}")
    if blogs:
        parts.append(f"博客 {len(blogs)}")
    if chinese:
        parts.append(f"中文 {len(chinese)}")

    lines = [
        f"AI Builder Daily {date_str}",
        "━" * 30,
        "",
        f"共 {total} 条：" + " · ".join(parts) if parts else f"共 {total} 条",
        "",
    ]

    def add_section(header: str, items: list):
        if not items:
            return
        lines.append("")
        lines.append(f"【{header}】")
        for i, item in enumerate(items, 1):
            name = item.get("name", "?")
            t = item["type"]
            text = item.get("text", "")
            url = item["url"]

            if t == "twitter":
                likes = item.get("likes", 0)
                lines.append(f"{i}. {name}（❤️ {likes}）")
            elif t == "podcast":
                lines.append(f"{i}. 🎙 {name}")
            elif t == "blog":
                lines.append(f"{i}. 📝 {name}")
            else:
                lines.append(f"{i}. 📰 {name}")

            # Truncate text
            display = text[:200] + ("..." if len(text) > 200 else "")
            lines.append(f"   {display}")
            lines.append(f"   🔗 {url}")

    add_section("Podcasts", podcasts)
    add_section("X / Builders", tweets)
    add_section("Blogs", blogs)
    add_section("中文", chinese)

    lines.append("─" * 34)
    lines.append("Generated by AI Builder Daily · follow-builders + 中文媒体")

    return "\n".join(lines)


# ── Meta JSON Generation ───────────────────────────────────────────────────

def generate_meta(date_str: str, date_compact: str, tweets: list, podcasts: list,
                  blogs: list, chinese: list, html_path: str, txt_path: str) -> str:
    """Generate meta.json."""
    template_path = TEMPLATE_DIR / "digest-meta.json"
    with open(template_path) as f:
        template = f.read()

    total = len(tweets) + len(podcasts) + len(blogs) + len(chinese)

    def url_list(items):
        return json.dumps([i["url"] for i in items], ensure_ascii=False)

    result = template
    result = result.replace("{{DATE}}", date_str)
    result = result.replace("{{DATE_COMPACT}}", date_compact)
    result = result.replace("{{HTML_PATH}}", html_path)
    result = result.replace("{{TEXT_PATH}}", txt_path)
    result = result.replace("{{PNG_PATH}}", "")
    result = result.replace("{{ITEMS_COUNT}}", str(total))
    result = result.replace("{{X_COUNT}}", str(len(tweets)))
    result = result.replace("{{PODCAST_COUNT}}", str(len(podcasts)))
    result = result.replace("{{BLOG_COUNT}}", str(len(blogs)))
    result = result.replace("{{ZH_COUNT}}", str(len(chinese)))
    result = result.replace("{{TWEET_URLS_JSON}}", url_list(tweets))
    result = result.replace("{{PODCAST_IDS_JSON}}", url_list(podcasts))
    result = result.replace("{{BLOG_URLS_JSON}}", url_list(blogs))
    result = result.replace("{{ZH_IDS_JSON}}", url_list(chinese))
    result = result.replace("{{ERRORS_JSON}}", "[]")

    return result


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    now = datetime.now(CST)
    date_str = now.strftime("%Y-%m-%d")
    date_compact = now.strftime("%Y%m%d")

    print(f"Building digest for {date_str}...", file=sys.stderr)

    # 1. Load state
    state = load_state()
    print(f"State loaded: {state.get('run_count', 0)} prior runs", file=sys.stderr)

    # 2. Fetch all sources
    print("Fetching tweets...", file=sys.stderr)
    tweets = fetch_tweets(state)
    print(f"  → {len(tweets)} new tweets after dedup+filter", file=sys.stderr)

    print("Fetching podcasts...", file=sys.stderr)
    podcasts = fetch_podcasts(state)
    print(f"  → {len(podcasts)} new podcasts", file=sys.stderr)

    print("Fetching blogs...", file=sys.stderr)
    blogs = fetch_blogs(state)
    print(f"  → {len(blogs)} new blogs", file=sys.stderr)

    print("Fetching Chinese sources...", file=sys.stderr)
    chinese = fetch_chinese(state)
    print(f"  → {len(chinese)} new Chinese articles", file=sys.stderr)

    all_items = tweets + podcasts + blogs + chinese
    total = len(all_items)

    # Cap total at 20
    if total > 20:
        # Keep Chinese, trim tweets
        excess = total - 20
        if len(tweets) > excess:
            tweets = tweets[:len(tweets) - excess]
        all_items = tweets + podcasts + blogs + chinese
        total = len(all_items)

    print(f"Total items: {total}", file=sys.stderr)

    # 3. Generate outputs
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    html_path = str(OUTPUT_DIR / f"digest-{date_compact}.html")
    txt_path = str(OUTPUT_DIR / f"digest-{date_compact}.txt")
    meta_path = str(OUTPUT_DIR / f"digest-{date_compact}.meta.json")

    html_content = generate_html(date_str, tweets, podcasts, blogs, chinese)
    with open(html_path, "w") as f:
        f.write(html_content)
    print(f"HTML: {html_path} ({len(html_content)} bytes)", file=sys.stderr)

    txt_content = generate_txt(date_str, tweets, podcasts, blogs, chinese)
    with open(txt_path, "w") as f:
        f.write(txt_content)
    print(f"TXT:  {txt_path} ({len(txt_content)} bytes)", file=sys.stderr)

    meta_content = generate_meta(date_str, date_compact, tweets, podcasts,
                                 blogs, chinese, html_path, txt_path)
    with open(meta_path, "w") as f:
        f.write(meta_content)
    print(f"META: {meta_path} ({len(meta_content)} bytes)", file=sys.stderr)

    # 4. Update state
    new_tweet_urls = [t["url"] for t in tweets]
    new_zh_urls = [c["url"] for c in chinese]
    new_podcast_urls = [p["url"] for p in podcasts]
    new_blog_urls = [b["url"] for b in blogs]

    state["seen_urls_tweets"].extend(new_tweet_urls)
    state["seen_urls_zh"].extend(new_zh_urls)
    state["seen_urls_podcasts"].extend(new_podcast_urls)
    state["seen_urls_blogs"].extend(new_blog_urls)
    state["last_run"] = now.isoformat()
    state["run_count"] = state.get("run_count", 0) + 1
    state["runs"].append({
        "run": f"R{state['run_count']}",
        "ts": now.isoformat(),
        "items": total,
        "status": "ok",
    })

    save_state(state)
    print("State updated.", file=sys.stderr)

    # 5. Print structured summary for agent to parse
    print()
    print("=== DIGEST BUILD COMPLETE ===")
    print(f"Date: {date_str}")
    print(f"Items: {total} total (X: {len(tweets)}, Podcasts: {len(podcasts)}, Blogs: {len(blogs)}, 中文: {len(chinese)})")
    print(f"Files: {html_path}, {txt_path}, {meta_path}")
    print(f"New tweet URLs: {len(new_tweet_urls)}")
    print(f"New zh URLs: {len(new_zh_urls)}")
    print(f"Run: R{state['run_count']}")
    print("=== END ===")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations
"""
web_reader.py — 统一网页读取脚本（三层架构）
L1: defuddle/Scrapling 快速抓取
L2: 浏览器渲染提示（PinchTab 已移除，改为提示使用 OpenClaw browser 工具）
L3: defuddle 内容清洗（统一 markdown 输出）

用法:
  python3 web_reader.py <url> [--browser] [--profile <name>] [--save <path>] [--json] [--max-chars <n>] [--timeout <s>]
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
FETCH_PY = SCRIPT_DIR / "fetch.py"
DEFUDDLE_BIN = Path("/opt/homebrew/bin/defuddle")

try:
    from fetch import scrapling_fetch
except ImportError:
    scrapling_fetch = None

# ─── 域名路由表 ───────────────────────────────────────

DOMAIN_PROFILES: dict[str, str] = {
    # 域名后缀 → profile 名
    "zhihu.com": "zhihu",
    "x.com": "x-twitter",
    "twitter.com": "x-twitter",
    "mp.weixin.qq.com": "wechat",
}

BROWSER_REQUIRED_DOMAINS: set[str] = {
    "zhihu.com",
    "x.com",
    "twitter.com",
}

# ─── 辅助函数 ─────────────────────────────────────────


def get_domain(url: str) -> str:
    """从 URL 提取域名（不含路径和端口）"""
    parsed = urlparse(url)
    host = parsed.hostname or parsed.netloc.split(":")[0]
    return host


def domain_to_profile(domain: str) -> str:
    """域名 → profile 映射"""
    for suffix, profile in DOMAIN_PROFILES.items():
        if domain.endswith(suffix):
            return profile
    return "default"


def needs_browser(domain: str) -> bool:
    """判断域名是否需要浏览器渲染"""
    for suffix in BROWSER_REQUIRED_DOMAINS:
        if domain.endswith(suffix):
            return True
    return False


def now_iso() -> str:
    """获取当前 ISO 时间戳"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")


def content_is_valid(content: str) -> bool:
    """检查 markdown 内容是否有效（非空、非登录墙）"""
    if len(content) < 100:
        return False
    login_wall_patterns = re.compile(
        r"(请登录|sign.?in.?to.?continue|login.?required|403.?forbidden|access.?denied|验证码)",
        re.IGNORECASE,
    )
    if login_wall_patterns.search(content):
        return False
    return True


def yaml_safe(value: str) -> str:
    """YAML 值转义：含特殊字符时用引号包裹"""
    if not value:
        return '""'
    special_chars = set(':#{}[]&*?|->!%@`')
    if any(c in value for c in special_chars):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def build_output(
    content: str,
    title: str,
    author: str,
    published: str,
    site: str,
    word_count: int,
    captured_via: str,
    url: str,
    output_json: bool,
) -> str:
    """构建 YAML front matter + markdown 输出"""
    captured_at = now_iso()

    if output_json:
        return json.dumps(
            {
                "url": url,
                "title": title,
                "author": author,
                "published": published,
                "site": site,
                "word_count": word_count,
                "captured_via": captured_via,
                "captured_at": captured_at,
                "content": content,
            },
            ensure_ascii=False,
            indent=2,
        )

    lines = [
        "---",
        f"url: {url}",
        f"title: {yaml_safe(title)}",
        f"author: {yaml_safe(author)}",
        f"published: {yaml_safe(published)}",
        f"site: {yaml_safe(site)}",
        f"word_count: {word_count}",
        f"captured_at: {captured_at}",
        f"captured_via: {captured_via}",
        "---",
        "",
        content,
    ]
    return "\n".join(lines)


# ─── L1: defuddle 快速抓取 ───────────────────────────


def try_defuddle(url: str, max_chars: int) -> tuple[str, dict] | None:
    """尝试使用 defuddle 抓取 URL，返回 (markdown_content, metadata) 或 None"""
    if not DEFUDDLE_BIN.exists():
        return None

    try:
        result = subprocess.run(
            [str(DEFUDDLE_BIN), "parse", "--json", "--markdown", url],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    if result.returncode != 0:
        return None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    content = data.get("content", "")
    if not content:
        return None

    title = data.get("title", "")
    author = data.get("author", "")
    published = data.get("published", "")
    site = data.get("site", "") or get_domain(url)
    word_count = data.get("wordCount", 0)

    content = content[:max_chars]

    if not content_is_valid(content):
        return None

    meta = {
        "title": title,
        "author": author,
        "published": published,
        "site": site,
        "word_count": word_count,
        "captured_via": "defuddle",
    }
    return content, meta


# ─── L1 备选: Scrapling ──────────────────────────────


def try_scrapling(url: str, max_chars: int) -> tuple[str, dict] | None:
    """尝试使用 Scrapling（fetch.py）抓取 URL"""
    if scrapling_fetch is None:
        return None

    try:
        content, _selector, extracted = scrapling_fetch(url, max_chars)
    except Exception:
        return None

    content = content.strip()
    if not content_is_valid(content):
        return None

    meta = {
        "title": extracted.get("title", ""),
        "author": extracted.get("author", ""),
        "published": extracted.get("published", ""),
        "site": extracted.get("site", "") or get_domain(url),
        "word_count": len(content.split()),
        "captured_via": "scrapling",
    }
    return content, meta


# ─── L2: 浏览器渲染提示（PinchTab 已移除）────────────


def browser_mode_message(url: str, profile: str, reason: str = "") -> str:
    """生成浏览器渲染提示信息，引导 agent 使用 OpenClaw browser 工具"""
    lines = [
        f"⚠️ 该 URL 需要浏览器渲染（profile: {profile}）",
        f"URL: {url}",
        "",
        "请使用 OpenClaw 内置 browser 工具进行浏览器渲染：",
        "  1. 用 browser open 打开页面",
        "  2. 用 browser snapshot 获取内容",
        "  3. 或用 browser navigate + browser snapshot",
    ]
    if reason:
        lines.insert(1, f"原因: {reason}")
    return "\n".join(lines)


# ─── 主路由逻辑 ──────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="统一网页读取脚本（三层架构）",
        usage="%(prog)s <url> [--browser] [--profile <name>] [--save <path>] [--json] [--max-chars <n>] [--timeout <s>]",
    )
    parser.add_argument("url", nargs="?", help="要抓取的 URL")
    parser.add_argument("--browser", action="store_true", help="强制使用浏览器渲染")
    parser.add_argument("--profile", default="", help="指定 PinchTab profile 名")
    parser.add_argument("--save", default="", help="将结果保存到指定路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--max-chars", type=int, default=50000, help="最大输出字符数（默认 50000）")
    parser.add_argument("--timeout", type=int, default=30, help="超时秒数（默认 30）")

    args = parser.parse_args()

    if not args.url:
        print("错误: 未提供 URL", file=sys.stderr)
        print(
            "用法: web_reader.py <url> [--browser] [--profile <name>] [--save <path>] [--json]",
            file=sys.stderr,
        )
        sys.exit(1)

    url = args.url
    domain = get_domain(url)
    max_chars = args.max_chars

    # 确定 profile
    profile = args.profile or domain_to_profile(domain)

    # ─── 强制浏览器模式 ───────────────────────────
    if args.browser:
        print(browser_mode_message(url, profile, "用户指定 --browser"), file=sys.stderr)
        sys.exit(1)

    # ─── 域名需要浏览器 ──────────────────────────
    if needs_browser(domain):
        print(browser_mode_message(url, profile, f"域名 {domain} 需要浏览器渲染"), file=sys.stderr)

        # 先尝试 L1 看看能不能拿到有效内容
        result = try_defuddle(url, max_chars)
        if result:
            content, meta = result
            output = build_output(content, url=url, output_json=args.json, **meta)
            _save_and_print(output, args.save)
            return

        result = try_scrapling(url, max_chars)
        if result:
            content, meta = result
            output = build_output(content, url=url, output_json=args.json, **meta)
            _save_and_print(output, args.save)
            return

        # L1 全部失败，提示需要浏览器
        print("错误: L1 抓取失败，且该域名需要浏览器渲染。请使用 OpenClaw browser 工具。", file=sys.stderr)
        sys.exit(1)

    # ─── 正常 L1 路径 ─────────────────────────────

    # defuddle 优先
    print("## [web-reader] L1: defuddle 快速抓取", file=sys.stderr)
    result = try_defuddle(url, max_chars)
    if result:
        content, meta = result
        output = build_output(content, url=url, output_json=args.json, **meta)
        _save_and_print(output, args.save)
        return

    # Scrapling 备选
    print("## [web-reader] L1: Scrapling 备选", file=sys.stderr)
    result = try_scrapling(url, max_chars)
    if result:
        content, meta = result
        output = build_output(content, url=url, output_json=args.json, **meta)
        _save_and_print(output, args.save)
        return

    # 全部失败
    print(f"错误: 所有抓取策略均失败 (URL: {url})", file=sys.stderr)
    sys.exit(1)


def _save_and_print(output: str, save_path: str) -> None:
    """打印输出并可选保存到文件"""
    print(output)
    if save_path:
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
        print(f"## [web-reader] 已保存到 {save_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

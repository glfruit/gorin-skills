#!/usr/bin/env python3
"""collect_pipeline.py — 批量站点采集管线

对多个来源执行站点级操作，合并为统一 JSON/Markdown 输出。

Usage:
    # 使用预设采集方案
    python3 collect_pipeline.py --preset daily-tech
    python3 collect_pipeline.py --preset invest-cn

    # 自定义采集
    python3 collect_pipeline.py hackernews/top --limit 10 bilibili/hot --limit 5 zhihu/hot --limit 5

    # 输出为 Markdown
    python3 collect_pipeline.py --preset daily-tech --format md

    # 列出预设方案
    python3 collect_pipeline.py --list-presets
"""

import json
import subprocess
import sys
import shutil
import os
import argparse
from datetime import datetime, timezone, timedelta

# UTC+8
CST = timezone(timedelta(hours=8))

PRESETS = {
    "daily-tech": {
        "description": "每日科技热榜（HN + V2EX + DevTo + Lobsters）",
        "sources": [
            {"site": "hackernews", "cmd": "top", "limit": 10},
            {"site": "v2ex", "cmd": "hot", "limit": 10},
            {"site": "devto", "cmd": "top", "limit": 10},
            {"site": "lobsters", "cmd": "hot", "limit": 10},
        ],
    },
    "invest-cn": {
        "description": "投资社区热榜（雪球 + 微博 + 小红书 + 36kr）",
        "sources": [
            {"site": "xueqiu", "cmd": "hot", "limit": 10},
            {"site": "weibo", "cmd": "hot", "limit": 10},
            {"site": "xiaohongshu", "cmd": "feed", "limit": 10},
            {"site": "36kr", "cmd": "hot", "limit": 10},
        ],
    },
    "ai-research": {
        "description": "AI 研究动态（arXiv + HN AI + HF Models）",
        "sources": [
            {"site": "hackernews", "cmd": "top", "limit": 15},
            {"site": "arxiv", "cmd": "search", "args": ["large language model"], "limit": 10},
            {"site": "hf", "cmd": "top", "limit": 10},
        ],
    },
    "content-cn": {
        "description": "中文内容平台热榜（B站 + 知乎 + 微博 + 小红书 + 抖音）",
        "sources": [
            {"site": "bilibili", "cmd": "hot", "limit": 10},
            {"site": "zhihu", "cmd": "hot", "limit": 10},
            {"site": "weibo", "cmd": "hot", "limit": 10},
            {"site": "xiaohongshu", "cmd": "feed", "limit": 10},
            {"site": "toutiao", "cmd": "hot", "limit": 10},
        ],
    },
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROUTER = os.path.join(SCRIPT_DIR, "site_router.py")


def fetch_one(site, cmd, limit=10, extra_args=None):
    """通过 site_router 抓取单个来源"""
    args = ["python3", ROUTER, site, cmd, f"--limit", str(limit)]
    if extra_args:
        args.extend(extra_args)
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=30
        )
        if proc.returncode != 0:
            return {
                "site": site,
                "command": cmd,
                "error": True,
                "message": proc.stderr.strip() or "unknown error",
                "data": [],
            }
        result = json.loads(proc.stdout)
        return {
            "site": site,
            "command": cmd,
            "error": result.get("error", False),
            "tool": result.get("tool", "unknown"),
            "fallback": result.get("fallback_from"),
            "data": result.get("data", []),
            "count": len(result.get("data", [])) if isinstance(result.get("data"), list) else 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "site": site,
            "command": cmd,
            "error": True,
            "message": "timeout (30s)",
            "data": [],
        }
    except Exception as e:
        return {
            "site": site,
            "command": cmd,
            "error": True,
            "message": str(e),
            "data": [],
        }


def run_preset(preset_name, limit_override=None):
    """执行预设采集方案"""
    preset = PRESETS.get(preset_name)
    if not preset:
        return {"error": True, "message": f"Unknown preset: {preset_name}. Use --list-presets."}

    results = []
    total_items = 0

    for src in preset["sources"]:
        lim = limit_override or src.get("limit", 10)
        extra = src.get("args", [])
        r = fetch_one(src["site"], src["cmd"], lim, extra)
        results.append(r)
        total_items += r["count"]

    return {
        "preset": preset_name,
        "description": preset["description"],
        "timestamp": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "Asia/Shanghai",
        "sources": results,
        "total_items": total_items,
        "errors": [r["site"] for r in results if r["error"]],
    }


def to_markdown(report):
    """将采集结果转为可读 Markdown"""
    lines = [
        f"# {report.get('description', report.get('preset', 'Collection'))}",
        f"",
        f"> 采集时间：{report['timestamp']}",
        f"",
    ]

    if report.get("errors"):
        lines.append(f"⚠️ 以下来源采集失败：{', '.join(report['errors'])}")
        lines.append("")

    for src in report.get("sources", []):
        site = src["site"]
        data = src.get("data", [])
        tool = src.get("tool", "?")
        fb = f" (fallback: {src['fallback']})" if src.get("fallback") else ""

        if src.get("error"):
            lines.append(f"## ❌ {site}/{src['command']} [{tool}{fb}]")
            lines.append(f"> {src.get('message', 'error')}")
            lines.append("")
            continue

        lines.append(f"## {site}/{src['command']} [{tool}{fb}] — {src['count']} 条")
        lines.append("")

        if not data:
            lines.append("_（无数据）_")
            lines.append("")
            continue

        for i, item in enumerate(data, 1):
            # 通用字段映射
            title = (
                item.get("title") or item.get("word") or
                item.get("name") or item.get("question") or
                item.get("name_zh") or f"#{i}"
            )
            url = item.get("url") or item.get("link") or ""
            subtitle = item.get("description") or item.get("summary") or item.get("excerpt") or ""

            # 热度/分数字段
            hot_parts = []
            for key in ["score", "hot_value", "play", "views", "points", "likes", "count"]:
                if key in item and item[key]:
                    hot_parts.append(f"{key}: {item[key]}")
            hot_str = " | ".join(hot_parts)

            line = f"{i}. {title}"
            if url:
                line += f" — [{url[:60]}...]({url})" if len(url) > 60 else f" — [{url}]({url})"
            if hot_str:
                line += f" `({hot_str})`"
            if subtitle:
                # 截断过长摘要
                sub = subtitle[:100] + "..." if len(subtitle) > 100 else subtitle
                line += f"\n   > {sub}"
            lines.append(line)

        lines.append("")

    lines.append(f"---\n共 {report.get('total_items', 0)} 条")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="批量站点采集管线")
    parser.add_argument("--preset", help="预设采集方案名称")
    parser.add_argument("--list-presets", action="store_true", help="列出所有预设方案")
    parser.add_argument("--format", choices=["json", "md"], default="json", help="输出格式")
    parser.add_argument("--limit", type=int, help="覆盖所有来源的 limit")
    parser.add_argument("--output", "-o", help="输出文件路径（不指定则 stdout）")
    parser.add_argument("sources", nargs="*", help="自定义来源：site/cmd [site/cmd ...]")

    args = parser.parse_args()

    if args.list_presets:
        for name, preset in PRESETS.items():
            src_list = ", ".join(f"{s['site']}/{s['cmd']}" for s in preset["sources"])
            print(f"  {name}: {preset['description']}")
            print(f"    来源: {src_list}")
        return

    # 执行采集
    if args.preset:
        report = run_preset(args.preset, args.limit)
    elif args.sources:
        # 自定义模式：hackernews/top bilibili/hot ...
        results = []
        total = 0
        for src in args.sources:
            parts = src.split("/", 1)
            if len(parts) != 2:
                results.append({"site": src, "command": "?", "error": True, "message": "格式: site/cmd", "data": []})
                continue
            site, cmd = parts
            r = fetch_one(site, cmd, args.limit or 10)
            results.append(r)
            total += r["count"]
        report = {
            "preset": "custom",
            "timestamp": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": "Asia/Shanghai",
            "sources": results,
            "total_items": total,
        }
    else:
        parser.print_help()
        sys.exit(1)

    # 输出
    if args.format == "md":
        output = to_markdown(report)
    else:
        output = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Written to {args.output} ({len(output)} bytes)", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()

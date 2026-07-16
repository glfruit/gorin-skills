#!/usr/bin/env python3
"""site_router.py — 站点级操作统一路由入口

Usage:
    python3 site_router.py <site> <command> [args...]

Examples:
    python3 site_router.py hackernews top --limit 10
    python3 site_router.py bilibili hot --limit 5
    python3 site_router.py zhihu search "大语言模型"
    python3 site_router.py probe          # 检测工具可用性

Output: unified JSON (stdout), errors to stderr
"""

import json
import subprocess
import sys
import shutil
import os

ROUTING_TABLE = {
    # === opencli-rs Public 模式（不需要登录，首选）===
    "hackernews":    {"tool": "opencli-rs", "mode": "public"},
    "devto":         {"tool": "opencli-rs", "mode": "public"},
    "lobsters":      {"tool": "opencli-rs", "mode": "public"},
    "stackoverflow": {"tool": "opencli-rs", "mode": "public"},
    "steam":         {"tool": "opencli-rs", "mode": "public"},
    "linux-do":      {"tool": "opencli-rs", "mode": "public"},
    "arxiv":         {"tool": "opencli-rs", "mode": "public"},
    "wikipedia":     {"tool": "opencli-rs", "mode": "public"},
    "apple-podcasts":{"tool": "opencli-rs", "mode": "public"},
    "xiaoyuzhou":    {"tool": "opencli-rs", "mode": "public"},
    "bbc":           {"tool": "opencli-rs", "mode": "public"},
    "hf":            {"tool": "opencli-rs", "mode": "public"},
    "sinafinance":   {"tool": "opencli-rs", "mode": "public"},

    # === 重叠站点：opencli-rs 优先 ===
    "bilibili":      {"tool": "opencli-rs", "fallback": "bb-browser"},
    "zhihu":         {"tool": "opencli-rs", "fallback": "bb-browser"},
    "twitter":       {"tool": "opencli-rs", "fallback": "bb-browser"},
    "x":             {"tool": "opencli-rs", "fallback": "bb-browser"},
    "xiaohongshu":   {"tool": "opencli-rs", "fallback": "bb-browser"},
    "reddit":        {"tool": "opencli-rs", "fallback": "bb-browser"},
    "douban":        {"tool": "opencli-rs", "fallback": "bb-browser"},
    "xueqiu":        {"tool": "opencli-rs", "fallback": "bb-browser"},
    "boss":          {"tool": "opencli-rs", "fallback": "bb-browser"},
    "v2ex":          {"tool": "opencli-rs", "fallback": "bb-browser"},
    "linkedin":      {"tool": "opencli-rs", "fallback": "bb-browser"},
    "reuters":       {"tool": "opencli-rs", "fallback": "bb-browser"},
    "smzdm":         {"tool": "opencli-rs", "fallback": "bb-browser"},
    "ctrip":         {"tool": "opencli-rs", "fallback": "bb-browser"},

    # === 重叠站点：bb-browser 优先 ===
    "weibo":         {"tool": "bb-browser", "fallback": "opencli-rs"},
    "youtube":       {"tool": "bb-browser", "fallback": "opencli-rs"},

    # === bb-browser 独有 ===
    "baidu":         {"tool": "bb-browser"},
    "cnblogs":       {"tool": "bb-browser"},
    "csdn":          {"tool": "bb-browser"},
    "36kr":          {"tool": "opencli-rs"},  # auto-generated adapter
    "eastmoney":     {"tool": "bb-browser"},
    "genius":        {"tool": "bb-browser"},
    "hupu":          {"tool": "bb-browser"},
    "npm":           {"tool": "bb-browser"},
    "sogou":         {"tool": "bb-browser"},
    "toutiao":       {"tool": "bb-browser"},
    "youdao":        {"tool": "bb-browser"},
    "producthunt":   {"tool": "bb-browser"},
    "openlibrary":   {"tool": "bb-browser"},
    "pypi":          {"tool": "bb-browser"},
    "gsmarena":      {"tool": "bb-browser"},
    "qidian":        {"tool": "bb-browser"},

    # === opencli-rs 独有 ===
    "weread":        {"tool": "opencli-rs"},
    "bloomberg":     {"tool": "opencli-rs"},
    "medium":        {"tool": "opencli-rs"},
    "substack":      {"tool": "opencli-rs"},
    "facebook":      {"tool": "opencli-rs"},
    "instagram":     {"tool": "opencli-rs"},
    "tiktok":        {"tool": "opencli-rs"},
    "weixin":        {"tool": "opencli-rs"},
    "cursor":        {"tool": "opencli-rs"},
    "codex":         {"tool": "opencli-rs"},
    "chatgpt":       {"tool": "opencli-rs"},
    "notion":        {"tool": "opencli-rs"},
    "discord-app":   {"tool": "opencli-rs"},
    "doubao":        {"tool": "opencli-rs"},
    "chaoxing":      {"tool": "opencli-rs"},
    "jimeng":        {"tool": "opencli-rs"},
    "grok":          {"tool": "opencli-rs"},
    "jike":          {"tool": "opencli-rs"},
    "yollomi":       {"tool": "opencli-rs"},
    "sinablog":      {"tool": "opencli-rs"},
    "doubao-app":    {"tool": "opencli-rs"},
    "chatwise":      {"tool": "opencli-rs"},
    "coupang":       {"tool": "opencli-rs"},
    "barchart":      {"tool": "opencli-rs"},
    "google":        {"tool": "opencli-rs"},
    "yahoo-finance": {"tool": "opencli-rs"},
}


def probe_tools():
    """检测 opencli-rs 和 bb-browser 可用性"""
    result = {}

    # opencli-rs binary
    ocr_path = shutil.which("opencli-rs")
    result["opencli-rs"] = {
        "binary": ocr_path is not None,
        "path": ocr_path or "not found",
    }

    # opencli-rs daemon + extension
    if ocr_path:
        try:
            doctor = subprocess.run(
                ["opencli-rs", "doctor"],
                capture_output=True, text=True, timeout=10
            )
            output = doctor.stdout + doctor.stderr
            result["opencli-rs"]["daemon"] = "Daemon running" in output
            result["opencli-rs"]["extension"] = "Chrome extension connected" in output
            result["opencli-rs"]["browser_mode"] = result["opencli-rs"]["daemon"] and result["opencli-rs"]["extension"]
        except Exception as e:
            result["opencli-rs"]["error"] = str(e)
            result["opencli-rs"]["daemon"] = False
            result["opencli-rs"]["extension"] = False
            result["opencli-rs"]["browser_mode"] = False
    else:
        result["opencli-rs"]["daemon"] = False
        result["opencli-rs"]["extension"] = False
        result["opencli-rs"]["browser_mode"] = False

    # bb-browser
    bbb_path = shutil.which("bb-browser")
    result["bb-browser"] = {
        "binary": bbb_path is not None,
        "path": bbb_path or "not found",
    }

    return result


def run_opencli_rs(site, command, args):
    """执行 opencli-rs 命令"""
    cmd = ["opencli-rs", site, command] + args
    # 确保有 --format json
    if "--format" not in cmd:
        cmd.append("--format")
        cmd.append("json")
    return _run(cmd, "opencli-rs")


def run_bb_browser(site, command, args):
    """执行 bb-browser 命令"""
    cmd = ["bb-browser", "site", f"{site}/{command}"] + args
    return _run(cmd, "bb-browser")


def _run(cmd, tool_name):
    """统一执行 + 错误处理"""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            return {
                "error": True,
                "tool": tool_name,
                "command": " ".join(cmd),
                "message": err,
            }
        # 尝试解析 JSON
        try:
            data = json.loads(proc.stdout)
            return {
                "error": False,
                "tool": tool_name,
                "command": " ".join(cmd),
                "count": len(data) if isinstance(data, list) else 1,
                "data": data,
            }
        except json.JSONDecodeError:
            return {
                "error": False,
                "tool": tool_name,
                "command": " ".join(cmd),
                "data": proc.stdout.strip(),
            }
    except subprocess.TimeoutExpired:
        return {
            "error": True,
            "tool": tool_name,
            "command": " ".join(cmd),
            "message": f"timeout after 30s",
        }
    except Exception as e:
        return {
            "error": True,
            "tool": tool_name,
            "command": " ".join(cmd),
            "message": str(e),
        }


def route(site, command, args):
    """按路由表选择工具执行"""
    # 查找路由（支持别名）
    route_entry = None
    for key, val in ROUTING_TABLE.items():
        if key == site or key.startswith(site):
            route_entry = val
            break

    if route_entry is None:
        # 未在路由表中，尝试 opencli-rs（它有 55+ 站点，可能覆盖）
        return run_opencli_rs(site, command, args)

    primary = route_entry["tool"]
    fallback = route_entry.get("fallback")

    # Public 模式直接执行，不需要检查 daemon
    if route_entry.get("mode") == "public":
        return run_opencli_rs(site, command, args)

    # Browser 模式：检查工具可用性，执行 + 自动 fallback
    tools = probe_tools()

    result = _execute_tool(primary, site, command, args, tools, route_entry)
    if result.get("error") and fallback:
        print(f"[site_router] {primary} failed, falling back to {fallback}", file=sys.stderr)
        fb_entry = ROUTING_TABLE.get(site, {})
        fb_result = _execute_tool(fallback, site, command, args, tools, fb_entry)
        fb_result["fallback_from"] = primary
        return fb_result
    return result


def _execute_tool(tool, site, command, args, tools, route_entry=None):
    if tool == "opencli-rs":
        ocr = tools["opencli-rs"]
        if not ocr["binary"]:
            return {"error": True, "tool": tool, "message": "opencli-rs not installed"}
        # Public 模式不需要 daemon
        if route_entry and route_entry.get("mode") == "public":
            return run_opencli_rs(site, command, args)
        # Browser 模式需要 daemon + extension
        if not ocr["browser_mode"]:
            return {"error": True, "tool": tool, "message": "opencli-rs daemon/extension not connected"}
        return run_opencli_rs(site, command, args)
    elif tool == "bb-browser":
        bbb = tools["bb-browser"]
        if not bbb["binary"]:
            return {"error": True, "tool": tool, "message": "bb-browser not installed"}
        return run_bb_browser(site, command, args)
    return {"error": True, "tool": tool, "message": f"unknown tool: {tool}"}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": True,
            "message": "Usage: site_router.py <site> <command> [args...] | probe",
        }))
        sys.exit(1)

    if sys.argv[1] == "probe":
        result = probe_tools()
        result["supported_sites"] = sorted(ROUTING_TABLE.keys())
        print(json.dumps(result, indent=2))
        return

    if sys.argv[1] == "list":
        # 列出所有支持站点
        sites = {}
        for key, val in ROUTING_TABLE.items():
            mode = val.get("mode", "browser")
            fb = val.get("fallback", "")
            label = f"{val['tool']}"
            if fb:
                label += f" (fallback: {fb})"
            if mode == "public":
                label += " [public]"
            sites[key] = label
        print(json.dumps(sites, indent=2))
        return

    site = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else None
    args = sys.argv[3:] if len(sys.argv) > 3 else []

    if not command:
        print(json.dumps({
            "error": True,
            "message": f"Usage: site_router.py {site} <command> [args...]",
        }))
        sys.exit(1)

    result = route(site, command, args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

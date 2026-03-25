#!/usr/bin/env python3
"""
Harness Audit — 扫描 OpenClaw agent workspace 配置健康度。

用法:
    python3 harness_audit.py [--all | --soul | --agents | --cron | --skills]
    python3 harness_audit.py --report [OUTPUT_DIR]
    python3 harness_audit.py --trend

默认执行 --all，输出到 stdout。
--report 将结果保存为 markdown 文件。
--trend 与历史报告对比，输出趋势。
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

OPENCLAW_DIR = Path.home() / ".openclaw"
WORKSPACE_DIR = OPENCLAW_DIR  # workspaces are ~/.openclaw/workspace-*
SKILLS_DIR = OPENCLAW_DIR / "skills"
AUDITS_DIR = OPENCLAW_DIR / "audits"

# Severity downgrade map for third-party skills
SEVERITY_DOWNGRADE = {"P0": "P1", "P1": "P2", "P2": "P3", "P3": "INFO"}


def get_workspaces():
    """获取所有 agent workspace 路径。"""
    if not WORKSPACE_DIR.exists():
        return []
    return sorted(WORKSPACE_DIR.glob("workspace-*"))


def get_skills():
    """获取所有 skill 目录。"""
    skills = []
    for p in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        skills.append(p.parent)
    return skills


def read_skill_meta(skill_dir):
    """读取 skill 的 .skill-meta.json（支持 symlink 解析）。

    Returns: dict with 'origin' and 'author', or None if not found.
    """
    # Try direct path first, then resolve symlink
    for candidate in [skill_dir, skill_dir.resolve()]:
        meta_path = candidate / ".skill-meta.json"
        if meta_path.exists():
            try:
                import json
                with open(meta_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return None


def count_lines(path):
    """统计文件行数。"""
    if not path.exists():
        return 0
    try:
        return sum(1 for _ in open(path, encoding="utf-8", errors="ignore"))
    except Exception:
        return 0


def extract_hardcoded_rules(soul_path):
    """从 SOUL.md 的 Hard Rules section 提取硬性规则条目。

    只统计 ## Hard Rules section 内的 bold bullet，忽略
    "What You're Good At" 等其他 section 里的能力描述。
    """
    if not soul_path.exists():
        return []
    content = soul_path.read_text(encoding="utf-8", errors="ignore")

    # 定位 Hard Rules section 内容
    # 匹配各种变体: "## Hard Rules", "## Hard Rules (不可违背)" 等
    hr_match = re.search(
        r"^##\s+Hard Rules[^\n]*\n(.*?)(?=^##\s|^---\n|_This is who|$)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if not hr_match:
        return []

    hr_section = hr_match.group(1)
    rules = re.findall(r"^- \*\*(.+?)\*\*", hr_section, re.MULTILINE)
    return rules


def check_broken_refs(file_path):
    """检查文件中引用的路径是否存在。

    跳过以下情况（已知的误报源）：
    - 运行时创建的文件（consent.json、state.json 等）
    - 模板占位符（YYYY-MM、<path> 等）
    - 跨平台多路径中的备选路径（如果任一平台路径存在则跳过）
    """
    if not file_path.exists():
        return []
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    patterns = re.findall(
        r"(?:~/|/Users/\w+/)[\w/.~\-]+(?:\.py|\.sh|\.md|\.json|\.yaml|\.yml)",
        content,
    )

    # 排除模板占位符路径
    template_patterns = [
        "YYYY", "MM", "DD",  # 日期模板
        "path/to",  # 通用占位符
    ]

    # 运行时创建的文件，不存在是正常状态
    runtime_files = {"consent.json", "state.json"}

    # 按文件名分组，处理跨平台路径
    path_groups = {}
    for p in patterns:
        skip = False
        for tp in template_patterns:
            if tp in p:
                skip = True
                break
        if skip:
            continue
        basename = os.path.basename(p)
        if basename in runtime_files:
            continue
        path_groups.setdefault(basename, []).append(p)

    broken = []
    for basename, group in path_groups.items():
        # 如果组内任一路径存在，跳过整个组（跨平台 fallback）
        if any(os.path.exists(os.path.expanduser(p)) for p in group):
            continue
        broken.extend(group)

    return broken


def file_similarity(path_a, path_b):
    """简单的行级 Jaccard 相似度。"""
    if not path_a.exists() or not path_b.exists():
        return 0.0
    lines_a = set(
        line.strip()
        for line in open(path_a, encoding="utf-8", errors="ignore")
        if line.strip() and not line.strip().startswith("#")
    )
    lines_b = set(
        line.strip()
        for line in open(path_b, encoding="utf-8", errors="ignore")
        if line.strip() and not line.strip().startswith("#")
    )
    if not lines_a or not lines_b:
        return 0.0
    intersection = lines_a & lines_b
    union = lines_a | lines_b
    return len(intersection) / len(union)


def audit_soul():
    """审计所有 SOUL.md。"""
    findings = []
    for ws in get_workspaces():
        agent = ws.name.replace("workspace-", "")
        soul = ws / "SOUL.md"
        if not soul.exists():
            continue
        lines = count_lines(soul)
        rules = extract_hardcoded_rules(soul)
        broken = check_broken_refs(soul)
        # 与 AGENTS.md 重叠
        agents_md = ws / "AGENTS.md"
        overlap = file_similarity(soul, agents_md)

        if lines > 200:
            findings.append(
                {
                    "agent": agent,
                    "file": "SOUL.md",
                    "severity": "P1",
                    "issue": f"SOUL.md {lines} 行，超过 200 行阈值",
                    "suggestion": "检查是否可拆分规则到 references/ 或合并相似条目",
                }
            )
        elif lines > 150:
            findings.append(
                {
                    "agent": agent,
                    "file": "SOUL.md",
                    "severity": "P2",
                    "issue": f"SOUL.md {lines} 行，接近膨胀阈值",
                    "suggestion": "下次新增规则时考虑是否可替换而非追加",
                }
            )

        if len(rules) > 10:
            findings.append(
                {
                    "agent": agent,
                    "file": "SOUL.md",
                    "severity": "P1",
                    "issue": f"硬性规则 {len(rules)} 条，可能过度约束",
                    "suggestion": "检查是否有可合并或删除的规则",
                }
            )

        if overlap > 0.3:
            findings.append(
                {
                    "agent": agent,
                    "file": "SOUL.md + AGENTS.md",
                    "severity": "P1",
                    "issue": f"与 AGENTS.md 重叠 {overlap:.0%}",
                    "suggestion": "去重：规则在单一位置定义，另一处引用",
                }
            )

        for ref in broken:
            findings.append(
                {
                    "agent": agent,
                    "file": "SOUL.md",
                    "severity": "P0",
                    "issue": f"引用不存在的路径: {ref}",
                    "suggestion": "删除引用或恢复对应文件",
                }
            )

    return findings


def audit_agents():
    """审计所有 AGENTS.md。"""
    findings = []
    for ws in get_workspaces():
        agent = ws.name.replace("workspace-", "")
        agents_md = ws / "AGENTS.md"
        if not agents_md.exists():
            continue
        lines = count_lines(agents_md)
        broken = check_broken_refs(agents_md)

        if lines > 150:
            findings.append(
                {
                    "agent": agent,
                    "file": "AGENTS.md",
                    "severity": "P2",
                    "issue": f"AGENTS.md {lines} 行",
                    "suggestion": "检查是否有过时流程可以精简",
                }
            )

        for ref in broken:
            findings.append(
                {
                    "agent": agent,
                    "file": "AGENTS.md",
                    "severity": "P0",
                    "issue": f"引用不存在的路径: {ref}",
                    "suggestion": "删除引用或恢复对应文件",
                }
            )

    return findings


def audit_skills():
    """审计所有 skills 的 SKILL.md。"""
    findings = []
    for skill_dir in get_skills():
        skill_name = skill_dir.name
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        lines = count_lines(skill_md)
        broken = check_broken_refs(skill_md)
        meta = read_skill_meta(skill_dir)
        is_third_party = meta and meta.get("origin") == "third-party"

        if lines > 300:
            sev = "P2" if is_third_party else "P1"
            label = " (third-party)" if is_third_party else ""
            findings.append(
                {
                    "agent": f"skill:{skill_name}{label}",
                    "file": "SKILL.md",
                    "severity": sev,
                    "issue": f"SKILL.md {lines} 行，建议拆分到 references/",
                    "suggestion": "将详细说明移入 references/ 目录"
                    + (" (向上游反馈)" if is_third_party else ""),
                }
            )

        for ref in broken:
            sev = "P2" if is_third_party else "P1"
            label = " (third-party)" if is_third_party else ""
            findings.append(
                {
                    "agent": f"skill:{skill_name}{label}",
                    "file": "SKILL.md",
                    "severity": sev,
                    "issue": f"引用不存在的路径: {ref}",
                    "suggestion": "删除引用或恢复对应文件",
                }
            )

    return findings


def format_findings(findings):
    """格式化审计结果为 markdown。"""
    by_severity = {"P0": [], "P1": [], "P2": []}
    for f in findings:
        by_severity[f["severity"]].append(f)

    lines = []
    for sev in ["P0", "P1", "P2"]:
        items = by_severity[sev]
        if not items:
            continue
        label = {"P0": "必改", "P1": "建议", "P2": "可选"}[sev]
        lines.append(f"### {sev} {label} ({len(items)} 项)")
        lines.append("")
        lines.append("| # | Agent | 文件 | 问题 | 建议 |")
        lines.append("|---|-------|------|------|------|")
        for i, item in enumerate(items, 1):
            agent = item["agent"]
            file = item["file"]
            issue = item["issue"].replace("|", "\\|")
            suggestion = item["suggestion"].replace("|", "\\|")
            lines.append(f"| {i} | {agent} | {file} | {issue} | {suggestion} |")
        lines.append("")

    return "\n".join(lines)


def generate_report(findings, output_dir=None):
    """生成完整审计报告。"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m")
    report_date = now.strftime("%Y-%m-%d %H:%M")

    ws_count = len(get_workspaces())
    skill_count = len(get_skills())

    p0 = sum(1 for f in findings if f["severity"] == "P0")
    p1 = sum(1 for f in findings if f["severity"] == "P1")
    p2 = sum(1 for f in findings if f["severity"] == "P2")

    # 统计信息
    stats = []
    stats.append("### 配置概况")
    stats.append("")
    stats.append("| 维度 | 数量 |")
    stats.append("|------|------|")
    stats.append(f"| Agent workspace | {ws_count} |")
    stats.append(f"| Skills | {skill_count} |")

    # SOUL.md 行数排名（前5）
    soul_sizes = []
    for ws in get_workspaces():
        agent = ws.name.replace("workspace-", "")
        lines = count_lines(ws / "SOUL.md")
        if lines > 0:
            soul_sizes.append((agent, lines))
    soul_sizes.sort(key=lambda x: -x[1])

    if soul_sizes:
        stats.append("")
        stats.append("### SOUL.md 行数排名 (Top 5)")
        stats.append("")
        stats.append("| Agent | 行数 |")
        stats.append("|-------|------|")
        for agent, lines in soul_sizes[:5]:
            marker = " ⚠️" if lines > 150 else ""
            stats.append(f"| {agent} | {lines}{marker} |")

    # Skill origin 统计
    origin_stats = {"self": 0, "third-party": 0, "unknown": 0}
    for skill_dir in get_skills():
        meta = read_skill_meta(skill_dir)
        if meta:
            origin = meta.get("origin", "unknown")
        else:
            origin = "unknown"
        origin_stats[origin] = origin_stats.get(origin, 0) + 1

    origin_lines = []
    origin_lines.append("### Skill 来源")
    origin_lines.append("")
    origin_lines.append("| 来源 | 数量 |")
    origin_lines.append("|------|------|")
    for k, v in sorted(origin_stats.items(), key=lambda x: -x[1]):
        origin_lines.append(f"| {k} | {v} |")

    report = f"""# Harness 审计报告 — {date_str}

## 摘要
- 审计时间：{report_date}
- Agent 数量：{ws_count}
- Skill 数量：{skill_count}
- 发现问题：P0={p0} / P1={p1} / P2={p2}

{chr(10).join(stats)}

{chr(10).join(origin_lines)}

## 发现

{format_findings(findings)}
"""

    report += "---\n*由 harness-audit skill 生成*\n"

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / f"harness-{date_str}.md"
        report_path.write_text(report, encoding="utf-8")
        print(f"报告已保存: {report_path}", file=sys.stderr)
    else:
        print(report)

    return report


def main():
    parser = argparse.ArgumentParser(description="Harness Audit")
    parser.add_argument(
        "--all", action="store_true", help="执行所有审计（默认）"
    )
    parser.add_argument("--soul", action="store_true", help="仅审计 SOUL.md")
    parser.add_argument("--agents", action="store_true", help="仅审计 AGENTS.md")
    parser.add_argument(
        "--skills", action="store_true", help="仅审计 Skills"
    )
    parser.add_argument(
        "--report",
        nargs="?",
        const=str(AUDITS_DIR),
        help="保存报告为 markdown（可指定目录）",
    )
    parser.add_argument(
        "--json", action="store_true", help="输出 JSON 格式"
    )

    args = parser.parse_args()

    # 默认执行所有
    run_all = not (args.soul or args.agents or args.skills)

    findings = []
    if run_all or args.soul:
        findings.extend(audit_soul())
    if run_all or args.agents:
        findings.extend(audit_agents())
    if run_all or args.skills:
        findings.extend(audit_skills())

    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        generate_report(findings, output_dir=args.report)


if __name__ == "__main__":
    main()

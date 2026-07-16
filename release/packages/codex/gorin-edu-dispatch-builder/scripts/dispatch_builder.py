from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

COLUMN_ALIASES = {
    "project": ["项目名称", "项目", "项目名"],
    "task": ["任务名称", "任务", "任务名"],
    "module": ["模块/板块", "模块", "板块"],
    "unit": ["单元名称", "单元", "板块名称"],
    "knowledge": ["知识点/技能点", "知识点", "技能点"],
    "summary": ["主要内容概要", "具体内容概要", "内容概要"],
    "ideology": ["思政元素", "思政融入", "课程思政"],
    "needed_resource": ["需补充资源", "资源需求", "补充资源"],
    "existing_resource": ["已有资源名称", "已有资源"],
    "resource_type": ["资源类型"],
    "remark": ["备注"],
}

FIXED_PROHIBITIONS = [
    '不使用"了解/掌握/熟悉/培养/提高"等虚词',
    "不添加 TBD/待定/TODO",
    "不在拓展知识板块写 AI 前沿技术（只写专业拓展知识）",
    "不修改已完成的板块内容",
    "不越界扩写到后续板块",
]

TEMPLATE_HINTS = {
    "textbook": ["以教材正文口径组织内容，保证可直接进入教材手稿。", "兼顾章节可读性、教学逻辑与案例落地。"],
    "course": ["以课程教学材料口径组织内容，可适当强化课堂活动提示。", "突出教学过程中的讲练结合与课堂可执行性。"],
    "training": ["以实训材料口径组织内容，突出步骤、操作、检查点。", "强调任务驱动、操作规范与结果验收。"],
}


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip() == ""



def _clean(value: object) -> str:
    if _is_empty(value):
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
    return re.sub(r"\n{3,}", "\n\n", text)



def _first_present(row: pd.Series, names: Iterable[str]) -> str:
    for name in names:
        if name in row.index:
            value = _clean(row[name])
            if value:
                return value
    return ""



def _find_column(columns: Iterable[str], aliases: Iterable[str]) -> str | None:
    for alias in aliases:
        if alias in columns:
            return alias
    return None



def load_outline(excel_path: str | Path) -> pd.DataFrame:
    path = Path(excel_path)
    sheets = pd.read_excel(path, sheet_name=None)
    if not sheets:
        raise ValueError(f"未读取到任何工作表: {path}")
    frame = next(iter(sheets.values())).copy()
    frame.columns = [str(col).strip() for col in frame.columns]

    for logical_name in ("project", "task", "module"):
        column = _find_column(frame.columns, COLUMN_ALIASES[logical_name])
        if column:
            frame[column] = frame[column].ffill()

    frame = frame.reset_index(drop=True)
    frame.insert(0, "__row_number__", range(1, len(frame) + 1))
    return frame



def _title_for_row(row: pd.Series) -> str:
    unit = _first_present(row, COLUMN_ALIASES["unit"])
    module = _first_present(row, COLUMN_ALIASES["module"])
    knowledge = _first_present(row, COLUMN_ALIASES["knowledge"])
    if unit and module and unit != module:
        return f"{module}｜{unit}"
    return unit or module or knowledge or f"第{int(row['__row_number__'])}行板块"



def _derive_course_name(teaching_design_path: str | Path | None, project_root: str | Path | None, row: pd.Series) -> str:
    patterns = [r"\*\*书名\*\*[:：]\s*(.+)", r"\*\*课程\*\*[:：]\s*(.+)"]
    candidates: list[Path] = []
    if teaching_design_path:
        candidates.append(Path(teaching_design_path))
    if project_root:
        design_dir = Path(project_root) / "design"
        for name in ["requirements.md", "teaching-design.md"]:
            candidate = design_dir / name
            if candidate.exists():
                candidates.append(candidate)
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
    return _first_present(row, ["课程", "课程名称"]) or "未显式提供课程名"



def _split_markdown_sections(text: str) -> list[dict]:
    sections: list[dict] = []
    current: dict | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            current = {"level": len(heading.group(1)), "title": heading.group(2).strip(), "lines": []}
            sections.append(current)
            continue
        if current is not None:
            current["lines"].append(raw_line)
    return sections



def _compact_excerpt(text: str, limit: int = 200) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned[:limit] + ("…" if len(cleaned) > limit else "")



def _extract_teaching_constraints(teaching_design_path: str | Path | None) -> list[str]:
    if not teaching_design_path:
        return ["未提供 teaching-design.md，请派发前人工补充教学框架与边界。"]
    path = Path(teaching_design_path)
    if not path.exists():
        return [f"teaching-design.md 不存在: {path}"]

    text = path.read_text(encoding="utf-8")
    constraints: list[str] = []
    patterns = [
        (r"\*\*教学框架\*\*[:：]\s*(.+)", "教学框架"),
        (r"\*\*辅助方法\*\*[:：]\s*(.+)", "辅助方法"),
    ]
    for pattern, label in patterns:
        match = re.search(pattern, text)
        if match:
            constraints.append(f"{label}: {match.group(1).strip()}")

    for heading in ["教学设计决策", "技术边界", "已确认的歧义澄清"]:
        block = re.search(rf"##+\s+.*{re.escape(heading)}[\s\S]*?(?=\n##+\s+|\Z)", text)
        if not block:
            continue
        for line in block.group(0).splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(("- ", "* ")):
                constraints.append(stripped[2:].strip())
            elif re.match(r"^\d+\.\s+", stripped):
                constraints.append(re.sub(r"^\d+\.\s+", "", stripped))
            elif "|" in stripped and not stripped.startswith("|"):
                constraints.append(stripped)
    deduped: list[str] = []
    seen = set()
    for item in constraints:
        norm = re.sub(r"\s+", " ", item)
        if norm not in seen:
            seen.add(norm)
            deduped.append(item)
    return deduped or ["teaching-design.md 已提供，但未提取到结构化约束，请人工检查。"]



def _find_project_root(project_root: str | Path | None, teaching_design_path: str | Path | None) -> Path | None:
    if project_root:
        return Path(project_root)
    if teaching_design_path:
        td = Path(teaching_design_path).resolve()
        if td.parent.name == "design":
            return td.parent.parent
    return None



def _extract_format_requirements(project_root: str | Path | None, teaching_design_path: str | Path | None, template_type: str) -> list[str]:
    root = _find_project_root(project_root, teaching_design_path)
    docs: list[Path] = []
    if root:
        design_dir = root / "design"
        docs.extend([
            design_dir / "delivery-spec.md",
            design_dir / "content-architecture.md",
            design_dir / "framework-decision.md",
            design_dir / "requirements.md",
        ])
    requirements: list[str] = []
    for doc in docs:
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8")
        for heading in ["正文交付", "编写规范", "体例结构", "体例要求", "交付物", "质量标准", "审阅流程", "当前编写范围"]:
            block = re.search(rf"##+\s+.*{re.escape(heading)}[\s\S]*?(?=\n##+\s+|\Z)", text)
            if not block:
                continue
            for line in block.group(0).splitlines():
                stripped = line.strip()
                if stripped.startswith(("- ", "* ")):
                    requirements.append(stripped[2:].strip())
                elif re.match(r"^\d+\.\s+", stripped):
                    requirements.append(re.sub(r"^\d+\.\s+", "", stripped))
    requirements.extend(TEMPLATE_HINTS.get(template_type, []))
    deduped: list[str] = []
    seen = set()
    for item in requirements:
        norm = re.sub(r"\s+", " ", item)
        if norm not in seen:
            seen.add(norm)
            deduped.append(item)
    return deduped or ["Markdown 输出", "术语统一，遵循项目既有治理方案", "与前后板块标题层级保持一致"]



def _read_markdown_files(manuscript_dir: str | Path | None) -> list[tuple[Path, str]]:
    if not manuscript_dir:
        return []
    root = Path(manuscript_dir)
    if not root.exists():
        return []
    files = sorted(root.rglob("*.md"))
    return [(path, path.read_text(encoding="utf-8")) for path in files]



def _match_excerpt_in_manuscript(title_candidates: list[str], manuscripts: list[tuple[Path, str]]) -> str:
    for candidate in title_candidates:
        if not candidate:
            continue
        pattern = re.escape(candidate.strip())
        for _path, text in manuscripts:
            match = re.search(pattern, text)
            if match:
                snippet = text[match.end() : match.end() + 400]
                return _compact_excerpt(snippet)
    for _path, text in manuscripts:
        sections = _split_markdown_sections(text)
        for section in sections:
            if any(candidate and candidate in section["title"] for candidate in title_candidates):
                return _compact_excerpt("\n".join(section["lines"]))
    return "暂无对应手稿摘要，可按大纲规格直接编写。"



def _build_context(frame: pd.DataFrame, current_row_number: int, manuscript_dir: str | Path | None) -> tuple[list[str], list[str]]:
    manuscripts = _read_markdown_files(manuscript_dir)
    current_row = frame.loc[frame["__row_number__"] == current_row_number].iloc[0]
    task_name = _first_present(current_row, COLUMN_ALIASES["task"])
    same_task = frame.loc[frame[_find_column(frame.columns, COLUMN_ALIASES["task"])].fillna("") == task_name].copy()
    previous = same_task.loc[same_task["__row_number__"] < current_row_number].tail(4)
    upcoming = same_task.loc[same_task["__row_number__"] > current_row_number].head(6)

    previous_lines: list[str] = []
    for _, row in previous.iterrows():
        title = _title_for_row(row)
        excerpt = _match_excerpt_in_manuscript([
            _first_present(row, COLUMN_ALIASES["unit"]),
            _first_present(row, COLUMN_ALIASES["module"]),
            _first_present(row, COLUMN_ALIASES["knowledge"]),
            title,
        ], manuscripts)
        previous_lines.append(f"- {title}：{excerpt}")
    if not previous_lines:
        previous_lines.append("- 当前板块前暂无已完成板块，写作时直接从本板块起笔，但需与任务总目标对齐。")

    upcoming_lines: list[str] = []
    for _, row in upcoming.iterrows():
        title = _title_for_row(row)
        summary = _first_present(row, COLUMN_ALIASES["summary"]) or _first_present(row, COLUMN_ALIASES["knowledge"])
        upcoming_lines.append(f"- {title}：后续将覆盖 {summary or '相关内容'}")
    if not upcoming_lines:
        upcoming_lines.append("- 当前板块已接近任务末尾，注意补足收束与过渡。")

    return previous_lines, upcoming_lines



def _infer_output_path(current_row: pd.Series, manuscript_dir: str | Path | None, project_root: str | Path | None) -> str:
    task = _first_present(current_row, COLUMN_ALIASES["task"]) or "未命名任务"
    project = _first_present(current_row, COLUMN_ALIASES["project"]) or "未命名项目"
    filename = f"part_{project.replace('/', '_')}_{task.replace('/', '_')}.md"
    if manuscript_dir:
        return str((Path(manuscript_dir) / filename).resolve())
    root = _find_project_root(project_root, None)
    if root:
        return str((root / "manuscript" / filename).resolve())
    return filename



def build_dispatch(
    excel_path,
    row_number,
    template_type,
    manuscript_dir=None,
    teaching_design_path=None,
    project_root=None,
) -> str:
    frame = load_outline(excel_path)
    if row_number < 1 or row_number > len(frame):
        raise IndexError(f"row_number 超出范围: {row_number}, 有效范围 1-{len(frame)}")

    row = frame.iloc[row_number - 1]
    project_name = _first_present(row, COLUMN_ALIASES["project"]) or "未命名项目"
    task_name = _first_present(row, COLUMN_ALIASES["task"]) or "未命名任务"
    module_name = _first_present(row, COLUMN_ALIASES["module"]) or "未命名板块"
    unit_name = _first_present(row, COLUMN_ALIASES["unit"]) or module_name
    section_title = _title_for_row(row)
    course_name = _derive_course_name(teaching_design_path, project_root, row)

    knowledge = _first_present(row, COLUMN_ALIASES["knowledge"]) or "未填写"
    summary = _first_present(row, COLUMN_ALIASES["summary"]) or "未填写"
    ideology = _first_present(row, COLUMN_ALIASES["ideology"]) or "未填写"
    needed_resource = _first_present(row, COLUMN_ALIASES["needed_resource"]) or "未填写"
    existing_resource = _first_present(row, COLUMN_ALIASES["existing_resource"]) or "未填写"
    resource_type = _first_present(row, COLUMN_ALIASES["resource_type"]) or "未填写"
    remark = _first_present(row, COLUMN_ALIASES["remark"]) or "无"

    teaching_constraints = _extract_teaching_constraints(teaching_design_path)
    format_requirements = _extract_format_requirements(project_root, teaching_design_path, template_type)
    previous_context, upcoming_context = _build_context(frame, row_number, manuscript_dir)
    output_path = _infer_output_path(row, manuscript_dir, project_root)

    project_specific_prohibitions = [
        "如需引用系统或代码示例，默认以 HNC 为主，不擅自切换为其他系统。",
        "思政元素应自然融入，不写成口号式空话。",
    ]
    if "拓展" in module_name or "AI助学" in unit_name or "AI助学" in summary:
        project_specific_prohibitions.append("不要把拓展知识写成 AI 技术综述，必须回到数控专业场景。")

    dispatch = f"""## 派发指令: {section_title}

### 基本信息
- 课程: {course_name}
- 项目: {project_name}
- 任务: {task_name}
- 板块: {module_name}
- 大纲行号: {row_number}
- 单元名称: {unit_name}
- 模板类型: {template_type}

### 板块规格
- 知识点/技能点: {knowledge}
- 主要内容概要: {summary}
- 思政融入: {ideology}
- 需补充资源: {needed_resource}
- 已有资源名称: {existing_resource}
- 资源类型: {resource_type}
- 备注: {remark}

请根据以上大纲规格写作当前板块，只覆盖当前板块应承担的内容，不提前代写后续板块。若大纲当前行存在空白字段，仍需结合任务结构补齐叙述骨架，但不能捏造超出项目边界的新知识线。

### 教学设计约束
""" + "\n".join(f"- {item}" for item in teaching_constraints) + f"""

### 上下文
#### 前置板块（已完成的）
""" + "\n".join(previous_context) + f"""

#### 后续板块（待完成的）
""" + "\n".join(upcoming_context) + f"""

### 格式要求
""" + "\n".join(f"- {item}" for item in format_requirements) + f"""

### 禁止项
""" + "\n".join(f"- {item}" for item in [*FIXED_PROHIBITIONS, *project_specific_prohibitions]) + f"""

### 自检清单
写完后自查：
1. 知识点是否全部覆盖？
2. 教学目标动词是否合规？
3. 是否有占位符？
4. 板块间过渡是否自然？
5. 是否保持在 {task_name} 的任务边界内，没有越界写到后续板块？
6. 是否体现“理、虚、实相结合”和项目既定教学框架？

### 交付
- 输出文件: {output_path}
- 输出格式: Markdown
- 交付说明: 直接输出可并入手稿的中文 Markdown 正文，不要额外输出聊天解释。
"""
    return dispatch



def build_all_dispatches(
    excel_path,
    template_type,
    task_filter=None,
    manuscript_dir=None,
    teaching_design_path=None,
    project_root=None,
) -> list[str]:
    frame = load_outline(excel_path)
    task_column = _find_column(frame.columns, COLUMN_ALIASES["task"])
    if task_filter:
        if not task_column:
            raise ValueError("Excel 中未找到任务名称列，无法按任务过滤")
        mask = frame[task_column].fillna("").astype(str).str.contains(str(task_filter), regex=False)
        target_rows = frame.loc[mask, "__row_number__"].tolist()
    else:
        target_rows = frame["__row_number__"].tolist()

    if not target_rows:
        raise ValueError(f"未找到匹配任务: {task_filter}")

    return [
        build_dispatch(
            excel_path=excel_path,
            row_number=int(row_number),
            template_type=template_type,
            manuscript_dir=manuscript_dir,
            teaching_design_path=teaching_design_path,
            project_root=project_root,
        )
        for row_number in target_rows
    ]



def main() -> None:
    parser = argparse.ArgumentParser(description="Build self-contained dispatch prompts from Excel outlines.")
    parser.add_argument("excel_path", help="Excel 大纲文件路径")
    parser.add_argument("--row", type=int, help="单板块行号（1-indexed，对应数据行）")
    parser.add_argument("--task", help="按任务名批量构造派发指令")
    parser.add_argument("--template-type", required=True, choices=sorted(TEMPLATE_HINTS.keys()))
    parser.add_argument("--manuscript", dest="manuscript_dir", help="手稿目录")
    parser.add_argument("--teaching-design", dest="teaching_design_path", help="teaching-design.md 路径")
    parser.add_argument("--project", dest="project_root", help="项目根目录")
    parser.add_argument("--output", help="输出到文件")
    args = parser.parse_args()

    if not args.row and not args.task:
        parser.error("必须提供 --row 或 --task 之一")

    if args.row:
        result = build_dispatch(
            excel_path=args.excel_path,
            row_number=args.row,
            template_type=args.template_type,
            manuscript_dir=args.manuscript_dir,
            teaching_design_path=args.teaching_design_path,
            project_root=args.project_root,
        )
    else:
        results = build_all_dispatches(
            excel_path=args.excel_path,
            template_type=args.template_type,
            task_filter=args.task,
            manuscript_dir=args.manuscript_dir,
            teaching_design_path=args.teaching_design_path,
            project_root=args.project_root,
        )
        result = "\n\n" + ("\n\n---\n\n").join(results)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(result, encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()

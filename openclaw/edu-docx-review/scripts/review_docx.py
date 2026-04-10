from __future__ import annotations

import argparse
import re
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"

NS = {"w": W_NS, "a": A_NS, "pic": PIC_NS, "r": R_NS, "rel": REL_NS, "wp": WP_NS}
PAGE_WIDTH_CM = 21.0
EMU_PER_CM = 360000
PAGE_WIDTH_EMU = PAGE_WIDTH_CM * EMU_PER_CM
PLACEHOLDER_PATTERNS = ["TBD", "TODO", "待定", "适当", "酌情"]
CAPTION_WINDOW = 3
FIGURE_PATTERN = re.compile(r"图\s*(\d+)-(\d+)")
TABLE_PATTERN = re.compile(r"表\s*(\d+)-(\d+)")


@dataclass
class Issue:
    severity: str
    message: str


@dataclass
class SectionResult:
    name: str
    issues: list[Issue] = field(default_factory=list)
    details: list[str] = field(default_factory=list)

    def status(self) -> str:
        return "✅ 通过" if not self.issues else "❌ 不通过"


@dataclass
class ParagraphInfo:
    index: int
    text: str
    heading_level: int | None
    has_drawing: bool
    drawing_rel_ids: list[str]
    drawing_extents: list[int]


@dataclass
class TableInfo:
    index: int
    caption: str | None


@dataclass
class ImageInfo:
    index: int
    rel_id: str | None
    target: str | None
    paragraph_index: int
    caption: str | None
    width_px: int | None
    height_px: int | None
    estimated_dpi: float | None


@dataclass
class ReviewData:
    file_name: str
    publisher_name: str
    paragraphs: list[ParagraphInfo]
    headings: list[ParagraphInfo]
    images: list[ImageInfo]
    tables: list[TableInfo]
    placeholders: list[str]


def normalize_publisher(publisher: str) -> str:
    if publisher.lower() == "sjtu":
        return "上海交通大学出版社"
    return publisher


def get_paragraph_text(paragraph: etree._Element) -> str:
    texts = paragraph.xpath(".//w:t/text()", namespaces=NS)
    return "".join(texts).strip()


def get_heading_level(paragraph: etree._Element) -> int | None:
    style = paragraph.find("w:pPr/w:pStyle", namespaces=NS)
    if style is None:
        return None
    val = style.get(f"{{{W_NS}}}val") or style.get("val") or ""
    match = re.search(r"heading\s*([1-9])", val, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def read_relationships(rels_path: Path) -> dict[str, str]:
    if not rels_path.exists():
        return {}
    root = etree.parse(str(rels_path)).getroot()
    relationships: dict[str, str] = {}
    for rel in root.findall(f"{{{REL_NS}}}Relationship"):
        rid = rel.get("Id")
        target = rel.get("Target")
        if rid and target:
            relationships[rid] = target
    return relationships


def parse_paragraphs(document_root: etree._Element) -> list[ParagraphInfo]:
    paragraphs: list[ParagraphInfo] = []
    for index, paragraph in enumerate(document_root.xpath("//w:body/w:p", namespaces=NS), start=1):
        text = get_paragraph_text(paragraph)
        rel_ids = [
            blip.get(f"{{{R_NS}}}embed") or blip.get("embed")
            for blip in paragraph.xpath(".//a:blip", namespaces=NS)
            if blip.get(f"{{{R_NS}}}embed") or blip.get("embed")
        ]
        extents = []
        for extent in paragraph.xpath(".//wp:extent", namespaces=NS):
            cx = extent.get("cx")
            if cx and cx.isdigit():
                extents.append(int(cx))
        paragraphs.append(
            ParagraphInfo(
                index=index,
                text=text,
                heading_level=get_heading_level(paragraph),
                has_drawing=bool(paragraph.xpath(".//w:drawing", namespaces=NS)),
                drawing_rel_ids=rel_ids,
                drawing_extents=extents,
            )
        )
    return paragraphs


def parse_tables(document_root: etree._Element, paragraphs: list[ParagraphInfo]) -> list[TableInfo]:
    tables: list[TableInfo] = []
    body_children = document_root.xpath("//w:body/*", namespaces=NS)
    for child_index, node in enumerate(body_children):
        if etree.QName(node).localname != "tbl":
            continue
        caption = None
        for prev_index in range(child_index - 1, max(-1, child_index - CAPTION_WINDOW - 1), -1):
            prev_node = body_children[prev_index]
            if etree.QName(prev_node).localname != "p":
                continue
            text = get_paragraph_text(prev_node)
            if TABLE_PATTERN.search(text):
                caption = text
                break
        tables.append(TableInfo(index=len(tables) + 1, caption=caption))
    return tables


def parse_dimensions(media_path: Path) -> tuple[int | None, int | None]:
    suffix = media_path.suffix.lower()
    data = media_path.read_bytes()
    if suffix == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if suffix in {".jpg", ".jpeg"}:
        return parse_jpeg_dimensions(data)
    if suffix == ".gif" and data[:6] in {b"GIF87a", b"GIF89a"} and len(data) >= 10:
        return int.from_bytes(data[6:8], "little"), int.from_bytes(data[8:10], "little")
    if suffix == ".webp" and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return parse_webp_dimensions(data)
    return None, None


def parse_jpeg_dimensions(data: bytes) -> tuple[int | None, int | None]:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None, None
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            break
        seg_len = int.from_bytes(data[index:index + 2], "big")
        if seg_len < 2 or index + seg_len > len(data):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if index + 7 <= len(data):
                height = int.from_bytes(data[index + 3:index + 5], "big")
                width = int.from_bytes(data[index + 5:index + 7], "big")
                return width, height
        index += seg_len
    return None, None


def parse_webp_dimensions(data: bytes) -> tuple[int | None, int | None]:
    chunk = data[12:16]
    if chunk == b"VP8 ":
        if len(data) >= 30:
            return int.from_bytes(data[26:28], "little") & 0x3FFF, int.from_bytes(data[28:30], "little") & 0x3FFF
    if chunk == b"VP8L" and len(data) >= 25:
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if chunk == b"VP8X" and len(data) >= 30:
        width = 1 + int.from_bytes(data[24:27] + b"\x00", "little")
        height = 1 + int.from_bytes(data[27:30] + b"\x00", "little")
        return width, height
    return None, None


def estimate_dpi(width_px: int | None, extent_cx: int | None) -> float | None:
    if not width_px:
        return None
    ratio = (extent_cx / PAGE_WIDTH_EMU) if extent_cx else 1.0
    ratio = min(max(ratio, 0.05), 1.0)
    rendered_width_in = (PAGE_WIDTH_CM / 2.54) * ratio
    if rendered_width_in <= 0:
        return None
    return width_px / rendered_width_in


def resolve_media_path(extract_dir: Path, target: str | None) -> Path | None:
    if not target:
        return None
    normalized = target.replace('\\', '/').lstrip('/')
    candidates = [
        (extract_dir / "word" / normalized).resolve(),
        (extract_dir / normalized).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def parse_images(extract_dir: Path, paragraphs: list[ParagraphInfo]) -> list[ImageInfo]:
    relationships = read_relationships(extract_dir / "word" / "_rels" / "document.xml.rels")
    images: list[ImageInfo] = []
    for paragraph in paragraphs:
        if not paragraph.has_drawing:
            continue
        rel_ids = paragraph.drawing_rel_ids or [None]
        extents = paragraph.drawing_extents or [None]
        caption = find_caption_after(paragraphs, paragraph.index, FIGURE_PATTERN)
        for idx, rel_id in enumerate(rel_ids, start=1):
            target = relationships.get(rel_id) if rel_id else None
            media_path = resolve_media_path(extract_dir, target)
            width_px, height_px = parse_dimensions(media_path) if media_path else (None, None)
            extent_cx = extents[min(idx - 1, len(extents) - 1)] if extents and extents[0] is not None else None
            images.append(
                ImageInfo(
                    index=len(images) + 1,
                    rel_id=rel_id,
                    target=target,
                    paragraph_index=paragraph.index,
                    caption=caption,
                    width_px=width_px,
                    height_px=height_px,
                    estimated_dpi=estimate_dpi(width_px, extent_cx),
                )
            )
    return images


def find_caption_after(paragraphs: list[ParagraphInfo], start_index: int, pattern: re.Pattern[str]) -> str | None:
    for paragraph in paragraphs[start_index:start_index + CAPTION_WINDOW]:
        if pattern.search(paragraph.text):
            return paragraph.text
    return None


def scan_placeholders(paragraphs: Iterable[ParagraphInfo]) -> list[str]:
    findings: list[str] = []
    for paragraph in paragraphs:
        hits = [token for token in PLACEHOLDER_PATTERNS if token.lower() in paragraph.text.lower()]
        if hits:
            findings.append(f"第{paragraph.index}段：{paragraph.text[:80]}（命中: {', '.join(sorted(set(hits)))}）")
    return findings


def check_structure(data: ReviewData) -> SectionResult:
    result = SectionResult(name="结构检查")
    heading_levels = [p.heading_level for p in data.headings if p.heading_level is not None]
    highest = max(heading_levels) if heading_levels else None
    result.details.append(
        f"- 标题层级：共 {len(data.headings)} 个标题，最高 H{highest}" if highest else "- 标题层级：未发现标题"
    )
    for heading in data.headings:
        if heading.heading_level and heading.heading_level > 4:
            result.issues.append(Issue("important", f"第{heading.index}段标题层级超过 H4：{heading.text}"))
    previous_level = None
    for heading in data.headings:
        level = heading.heading_level
        if level is None:
            continue
        if previous_level is not None and level - previous_level > 1:
            result.issues.append(Issue("minor", f"第{heading.index}段标题存在跳级：H{previous_level} 后直接到 H{level}"))
        previous_level = level
    if not data.headings:
        result.issues.append(Issue("important", "文档未检测到标题，需人工确认是否缺少结构化章节。"))
    return result


def check_images(data: ReviewData) -> SectionResult:
    result = SectionResult(name="图片检查")
    result.details.append(f"- 图片总数：{len(data.images)}")
    low_res: list[str] = []
    missing_caption: list[str] = []
    figure_numbers: list[tuple[int, int]] = []
    for image in data.images:
        if image.estimated_dpi is not None and image.estimated_dpi < 300:
            low_res.append(
                f"图片{image.index}（{image.target or '未定位源文件'}，约 {image.estimated_dpi:.1f} DPI，{image.width_px}x{image.height_px}）"
            )
        elif image.width_px is None:
            low_res.append(f"图片{image.index}（{image.target or '未定位源文件'}，无法解析像素尺寸）")
        if not image.caption:
            missing_caption.append(f"图片{image.index}（位于第{image.paragraph_index}段附近）缺少图题")
        else:
            match = FIGURE_PATTERN.search(image.caption)
            if match:
                figure_numbers.append((int(match.group(1)), int(match.group(2))))
    result.details.append(f"- 低分辨率图片：{format_list(low_res)}")
    continuity = evaluate_number_sequence(figure_numbers, "图") if figure_numbers else "未形成可校验的图序"
    result.details.append(f"- 图序图题连续性：{continuity}")
    if not data.images:
        result.issues.append(Issue("minor", "未发现图片。"))
    for item in low_res:
        severity = "important" if "无法解析" not in item else "minor"
        result.issues.append(Issue(severity, item))
    for item in missing_caption:
        result.issues.append(Issue("important", item))
    return result


def check_tables(data: ReviewData) -> SectionResult:
    result = SectionResult(name="表格检查")
    result.details.append(f"- 表格总数：{len(data.tables)}")
    table_numbers: list[tuple[int, int]] = []
    if not data.tables:
        result.issues.append(Issue("minor", "未发现表格。"))
    for table in data.tables:
        if not table.caption:
            result.issues.append(Issue("important", f"表格{table.index}缺少位于前方的“表X-Y”表题。"))
            continue
        match = TABLE_PATTERN.search(table.caption)
        if match:
            table_numbers.append((int(match.group(1)), int(match.group(2))))
    continuity = evaluate_number_sequence(table_numbers, "表") if table_numbers else "未形成可校验的表序"
    result.details.append(f"- 表序表题连续性：{continuity}")
    return result


def check_content(data: ReviewData) -> SectionResult:
    result = SectionResult(name="内容检查")
    result.details.append(f"- 占位符：{format_list(data.placeholders)}")
    for placeholder in data.placeholders:
        result.issues.append(Issue("important", placeholder))
    if not data.placeholders:
        result.details.append("- 其他问题：未发现明显占位符")
    else:
        result.details.append("- 其他问题：请逐条清理占位内容并复审")
    return result


def evaluate_number_sequence(numbers: list[tuple[int, int]], label: str) -> str:
    if not numbers:
        return f"未发现可识别{label}序号"
    ordered = sorted(numbers)
    gaps: list[str] = []
    chapter_map: dict[int, list[int]] = {}
    for chapter, serial in ordered:
        chapter_map.setdefault(chapter, []).append(serial)
    for chapter, serials in chapter_map.items():
        serials = sorted(serials)
        for expected, current in enumerate(serials, start=1):
            if current != expected:
                gaps.append(f"{label}{chapter}-{current} 前缺少 {label}{chapter}-{expected}")
                break
    return "连续" if not gaps else "；".join(gaps)


def format_list(items: list[str]) -> str:
    return "无" if not items else "；".join(items)


def classify_overall(sections: list[SectionResult]) -> tuple[str, dict[str, int]]:
    counts = {"critical": 0, "important": 0, "minor": 0}
    for section in sections:
        for issue in section.issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
    if counts["critical"]:
        return "❌ 退回重做", counts
    if counts["important"]:
        return "⚠️ 需修复后复审", counts
    return "✅ 通过可交付", counts


def extract_docx(docx_path: Path) -> Path:
    if not docx_path.exists():
        raise FileNotFoundError(f"文件不存在: {docx_path}")
    if docx_path.suffix.lower() != ".docx":
        raise ValueError(f"不是 .docx 文件: {docx_path}")
    temp_dir = Path(tempfile.mkdtemp(prefix="edu_docx_review_"))
    with zipfile.ZipFile(docx_path) as archive:
        archive.extractall(temp_dir)
    return temp_dir


def collect_review_data(docx_path: Path, publisher: str) -> ReviewData:
    extract_dir = extract_docx(docx_path)
    document_xml = extract_dir / "word" / "document.xml"
    if not document_xml.exists():
        raise FileNotFoundError("缺少 word/document.xml，文档可能已损坏。")
    document_root = etree.parse(str(document_xml)).getroot()
    paragraphs = parse_paragraphs(document_root)
    headings = [paragraph for paragraph in paragraphs if paragraph.heading_level is not None]
    tables = parse_tables(document_root, paragraphs)
    images = parse_images(extract_dir, paragraphs)
    placeholders = scan_placeholders(paragraphs)
    return ReviewData(
        file_name=docx_path.name,
        publisher_name=normalize_publisher(publisher),
        paragraphs=paragraphs,
        headings=headings,
        images=images,
        tables=tables,
        placeholders=placeholders,
    )


def render_report(data: ReviewData, sections: list[SectionResult]) -> str:
    overall, counts = classify_overall(sections)
    total_issues = sum(counts.values())
    lines = [
        "# 教材出版规范审核报告",
        "",
        "## 基本信息",
        f"- **文件**: {data.file_name}",
        f"- **审核时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- **出版社要求**: {data.publisher_name}",
        "",
        "## 检查结果",
        "",
    ]
    for idx, section in enumerate(sections, start=1):
        lines.append(f"### {idx}. {section.name} — {section.status()}")
        lines.extend(section.details)
        if section.issues:
            for issue in section.issues:
                lines.append(f"- [{issue.severity.capitalize()}] {issue.message}")
        else:
            lines.append("- 未发现问题")
        lines.append("")
    lines.extend(
        [
            "## 总评",
            f"- **结果**: {overall}",
            f"- **问题总数**: {total_issues}（Critical: {counts['critical']}, Important: {counts['important']}, Minor: {counts['minor']}）",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def review_document(docx_path: str | Path, publisher: str = "sjtu") -> str:
    path = Path(docx_path).expanduser().resolve()
    data = collect_review_data(path, publisher)
    sections = [
        check_structure(data),
        check_images(data),
        check_tables(data),
        check_content(data),
    ]
    return render_report(data, sections)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="教材 DOCX 出版规范审核")
    parser.add_argument("docx", nargs="?", help="待审核的 .docx 文件路径")
    parser.add_argument("--publisher", default="sjtu", help="出版社要求代号或名称，默认 sjtu")
    parser.add_argument("--output", help="输出 Markdown 报告路径")
    parser.add_argument("--docx", dest="docx_flag", help="待审核的 .docx 文件路径（可选旗标写法）")
    args = parser.parse_args(argv)

    docx_arg = args.docx_flag or args.docx
    if not docx_arg:
        parser.error("请提供待审核的 .docx 文件路径")
    try:
        report = review_document(docx_arg, publisher=args.publisher)
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

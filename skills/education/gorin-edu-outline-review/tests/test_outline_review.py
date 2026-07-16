from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "outline_review.py"
HEADERS = [
    "项目名称",
    "任务名称",
    "模块/板块",
    "知识点/技能点",
    "主要内容概要",
]


class OutlineReviewCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_outline(self, rows: list[list[str]], headers: list[str] | None = None) -> Path:
        path = self.root / "outline.xlsx"
        workbook = Workbook()
        worksheet = workbook.active
        for row in [["课程大纲"], [], [], [], headers or HEADERS, *rows]:
            worksheet.append(row)
        workbook.save(path)
        return path

    def write_manuscript(self, source: str) -> Path:
        path = self.root / "manuscript.md"
        path.write_text(source, encoding="utf-8")
        return path

    def run_review(self, manuscript: Path, outline: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(manuscript),
                str(outline),
                "--template-type",
                "textbook",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_complete_manuscript_reports_full_coverage(self) -> None:
        outline = self.write_outline(
            [
                ["项目一", "任务一", "安全准备", "识别安全风险", "说明风险来源"],
                ["", "", "设备配置", "配置交换机 VLAN", "完成 VLAN 配置"],
            ]
        )
        manuscript = self.write_manuscript(
            """# 项目一

## 安全准备

学习者能够识别安全风险并说明风险来源。

## 设备配置

学习者完成配置交换机 VLAN 的操作。
"""
        )

        result = self.run_review(manuscript, outline)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**已覆盖**: 2 (100.0%)", result.stdout)
        self.assertIn("**模块覆盖**: 2/2 (100.0%)", result.stdout)
        self.assertIn("**结果**: ✅ 通过", result.stdout)

    def test_module_heading_alone_does_not_cover_knowledge_points(self) -> None:
        outline = self.write_outline(
            [
                ["项目一", "任务一", "安全准备", "识别钓鱼邮件", "列举钓鱼邮件特征"],
                ["", "", "安全准备", "处置恶意附件", "演示隔离附件步骤"],
            ]
        )
        manuscript = self.write_manuscript(
            """# 项目一

## 安全准备

本节内容尚未编写。
"""
        )

        result = self.run_review(manuscript, outline)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**已覆盖**: 0 (0.0%)", result.stdout)
        self.assertIn("**未覆盖**: 2 (100.0%)", result.stdout)
        self.assertIn("**结果**: ❌ 退回", result.stdout)

    def test_invalid_outline_headers_fail_closed(self) -> None:
        outline = self.write_outline(
            [["项目一", "任务一"]],
            headers=["项目", "任务"],
        )
        manuscript = self.write_manuscript("# 项目一\n\n## 安全准备\n")

        result = self.run_review(manuscript, outline)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required outline headers", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()

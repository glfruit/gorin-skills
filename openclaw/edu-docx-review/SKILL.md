---
name: edu-docx-review
description: "教材出版规范审核，对照出版社要求检查 Word 文档结构、图片、表格、代码、公式、中英文格式与内容合规，输出 Markdown 审核报告。不要用于 docx 生成或排版生产。"
triggers:
  - "审核教材"
  - "出版规范"
  - "docx审核"
  - "排版检查"
user-invocable: true
agent-usable: true
---

# edu-docx-review — 教材出版规范审核

## Core Principles

1. **只审不改**: 本技能只做 `.docx` 解包、检查、报告，不负责生成或修文档，生成交给 `kimi-docx`
2. **先按出版社要求，再看通用规范**: 默认使用上海交大社要求，可切换到其他要求文件
3. **报告必须可执行**: 每个维度输出 pass/fail、问题列表、严重度、总评，不写空话
4. **机器先扫，人工补判**: 结构、占位符、图片、标题/图表序号优先自动检查；术语统一、思政自然度等保留人工复核提示

## When to Use / When NOT to Use

✅ 教材交稿前出版规范审核；Word 原稿排版检查；出版社要求对照检查；生成复审问题清单

❌ 生成 docx / 美化排版 / 加封面 / 目录生产 → `kimi-docx` | 通用 Excel 审核 → `edu-xlsx` | PPT 检查 → `edu-pptx`

## Workflow

### 1. 选择要求 → 2. 解包 Word → 3. 逐项检查 → 4. 生成 Markdown 报告

默认要求文件：`/Users/gorin/.openclaw/workspace-edu-tl/knowledge-base/publisher-requirements/default.md`

核心流程：
- `docx` 当作 zip 包解压到临时目录
- 解析 `word/document.xml`、关系文件、媒体目录
- 检查六大维度：**结构、图片、表格、代码、公式、中英文格式、内容合规**
- 输出 Markdown 审核报告，每项含状态、严重度、问题清单、总评

## Recommended Invocation

```bash
cd /Users/gorin/.gorin-skills/openclaw/edu-docx-review
uv run python scripts/review_docx.py \
  --docx /path/to/manuscript.docx \
  --requirements ./references/publisher-requirements.md \
  --output /path/to/review-report.md
```

若不传 `--requirements`，默认走上海交大社要求。

## What the Script Checks

- **结构**: 标题层级、标题跳级、图序图题连续性、表序表题连续性
- **图片**: 图片数量、格式、像素尺寸，是否低于印刷建议阈值
- **表格**: 原生 Word 表格数量、表题检测、序号连续性
- **代码**: 代码块/等宽样式/常见关键字的启发式检测，提示是否疑似截图替代
- **公式**: OMML / MathML 节点检测，是否出现“公式图片”风险
- **中英文格式**: 中英文之间空格、常见缩写首次出现模式的启发式提示
- **内容合规**: `TBD` / `TODO` / `待定` / `占位` 等占位符；参考文献、前言、目录等辅文存在性线索

## Gotchas

1. **docx 本质是 zip 包**: 不解包就看不到真实结构，不能只靠页面肉眼看
2. **图片分辨率要分开看**: Word 里看到“大”不代表源图够清晰，至少先检查像素尺寸，必要时再人工复核 DPI
3. **公式不止一种格式**: 可能是 OMML，也可能是 MathML；若只搜一种会漏检
4. **图题/表题是启发式匹配**: 规范写法更容易被正确识别，乱写会导致误报
5. **中英文格式很难 100% 自动判定**: 自动报告负责抓高概率问题，不替代终审

## Error Handling

| 场景 | 处理 |
|------|------|
| 文件不存在 | 直接报错并退出 |
| 不是 docx | 报告文件类型错误 |
| document.xml 缺失 | 视为损坏文档 |
| 未检测到标题/图片/表格 | 在报告中明确写“未发现”而不是默认通过 |
| 要求文件不存在 | 回退到默认要求文件并给出提示 |

## Internal Acceptance

- **Happy-path**: 对一份教材 `.docx` 运行脚本，成功输出 Markdown 报告，至少包含结构、图片、表格、代码、公式、中英文格式、内容合规七个维度以及总评

## Delivery Contract

- 该技能当前为 **scaffold**
- 已提供可运行 Python 审核脚本与 uv 依赖声明
- Do **not** report this skill as fully production-ready until real docx 样本跑通并补完人工复核规则

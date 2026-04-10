---
name: edu-xlsx
description: "Edu outline Excel operations: identify, read, edit, validate, and extract from textbook/course/training .xlsx outline files. Do not use for general spreadsheet tasks — use xlsx skill instead. Not for Word docs or PowerPoint."
triggers:
  - "大纲 excel"
  - "大纲 xlsx"
  - "教材大纲"
  - "课程大纲"
  - "培训大纲"
  - "验证大纲"
  - "提取大纲"
user-invocable: true
agent-usable: true
---

# edu-xlsx — 教育大纲 Excel 操作

## Core Principles

1. **三套模板，自动识别**: 教材/课程/培训各一套列结构，表头匹配自动判断类型
2. **格式保留**: openpyxl 读写，不破坏合并单元格、列宽、字体
3. **公式用 Excel 公式**: 课程模板 E 列 = `=C{row}+D{row}`，不硬编码
4. **验证即文档**: 输出结构化报告，列出具体行号和问题

## When to Use / When NOT to Use

✅ 教师提供 Excel 大纲需读取/编辑；按模板填写新大纲；从大纲提取 section-requirements 派发 Phase 1；大纲完整性验证

❌ 通用 Excel 操作 → `xlsx` 技能 | 非 Excel 大纲 → 直接 Markdown | PPT 课件 → `edu-pptx`

## 模板列结构

完整列定义见 `references/column-structure.md`。简要：

- **教材** (13列): 项目名称→任务名称→模块/板块→单元名称→知识点/技能点(+8选填)
- **课程** (10列): 项目/模块名称→任务/单元名称→学时(理论/实践/总计)→教学目标(+4选填)
- **培训** (10列): 培训模块名称→培训活动名称→时长→培训对象→培训方式(+5选填)

必填列：教材 A-E | 课程 A-F | 培训 A-F

## Workflow

### 1. 识别 → 2. 读取 → 3. 填写/编辑 → 4. 验证 → 5. 提取

代码实现见 `references/code-examples.md`（含 identify / read / fill / edit / validate / extract 完整函数）。

**关键调用要点：**

- **识别**: `identify(path)` 返回 `textbook` / `course` / `training` / `None`。教材大纲常在第5行才出现表头，函数会自动检查第1行和第5行
- **读取**: 教材大纲 `pd.read_excel(path, header=4)`；标准模板 `pd.read_excel(path, header=0)`
- **验证**: 检查必填列、空行、层级完整性、不完整标记、公式、术语一致性
- **提取**: 输出 Markdown section-requirements，可直接用于 Phase 1 派发

## Gotchas

1. **行首偏移**: 教材大纲前1-4行常是课程元信息，第5行才是表头。先 `iter_rows(min_row=1, max_row=6)` 确认结构
2. **合并单元格**: openpyxl 只有左上角有值，填充时别拆合并区域
3. **公式不计算**: openpyxl 保存后公式是字符串，需用 `xlsx` 技能的 `recalc.py`
4. **pandas 合并格填充**: pandas 会把合并值填到所有行导致重复，精确控制用 openpyxl
5. **中文空格**: 列名匹配前 `.strip()` + normalize 全角/半角空格

## Error Handling

| 场景 | 处理 |
|------|------|
| 无法识别类型 | 报告前6行表头，让用户指定 |
| 文件不存在 | 查 `import/`、`knowledge-base/templates/`、`courses/{slug}/design/` |
| 列不匹配 | 列出实际 vs 期望，建议手动调整 |
| 不完整标记过多 | 列出所有位置，不自动填充 |

## Internal Acceptance

- **Happy-path**: 读取三套模板 → 识别正确 → 验证通过 → 提取 sections 输出有效 Markdown

## Delivery Contract

- 三套模板均能正确识别和读取
- 本技能标记为 scaffold，待代码脚本派发完成后升级至 integrated
- Do **not** report this skill as "complete" or "done" to the user unless it reaches integrated status

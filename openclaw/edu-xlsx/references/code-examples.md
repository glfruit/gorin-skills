# edu-xlsx Code Reference

## Template Identification

```python
import openpyxl

TEMPLATE_SIGS = {
    "textbook": {"项目名称", "任务名称", "模块/板块", "单元名称", "知识点/技能点"},
    "course": {"项目/模块名称", "任务/单元名称", "学时（理论）", "学时（实践）", "学时（总计）"},
    "training": {"培训模块名称", "培训活动名称", "时长（分钟）", "培训对象/人数"},
}

def identify(path, header_row=None):
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active
    rows_to_check = sorted(set([1] + ([header_row + 1] if header_row else [])))
    best, best_score = None, 0
    for hr in rows_to_check:
        headers = set()
        for cell in ws[hr]:
            h = str(cell.value).strip() if cell.value else ""
            if h: headers.add(h)
        for tname, sig in TEMPLATE_SIGS.items():
            overlap = len(sig & headers)
            if overlap > best_score:
                best_score, best = overlap, tname
    wb.close()
    return best if best_score >= 3 else None
```

## Outline Validation

```python
import openpyxl

REQUIRED_COLS = {
    'textbook': {'A','B','C','D','E'},
    'course':   {'A','B','C','D','E','F'},
    'training': {'A','B','C','D','E','F'},
}

def validate_outline(path, type_key, header_row=0):
    _PH = ('TBD', chr(24453)+chr(23450), 'TBC', 'T-O-D-O')
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    issues = []
    hr = header_row + 1
    for row_idx in range(hr + 1, ws.max_row + 1):
        row_vals = {col: ws[f'{col}{row_idx}'].value for col in 'ABCDEFGHIJKLM'}
        for col in REQUIRED_COLS.get(type_key, set()):
            if not row_vals.get(col) or not str(row_vals[col]).strip():
                issues.append(f'Row {row_idx}: required col {col} is empty')
        for col, val in row_vals.items():
            if val and any(k in str(val) for k in _PH):
                issues.append(f'Row {row_idx}, col {col}: incomplete marker: "{val}"')
    wb.close()
    return {'type': type_key, 'rows_checked': ws.max_row - hr, 'issues': issues, 'pass': len(issues) == 0}
```

## Section Extraction (Markdown)

```python
import openpyxl

COL_MAP = {
    'textbook': {'A': '所属项目', 'B': '所属任务', 'C': '模块', 'D': '单元', 'E': '知识点', 'F': '主要内容概要', 'G': '思政元素', 'H': '需补充资源'},
    'course':   {'A': '项目/模块名称', 'B': '任务/单元名称', 'C': '学时(理论)', 'D': '学时(实践)', 'F': '教学目标', 'G': '重点难点'},
    'training': {'A': '培训模块名称', 'B': '培训活动名称', 'C': '时长(分钟)', 'F': '活动内容描述', 'G': '产出物'},
}

def extract_sections(path, type_key, header_row=0):
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    hr = header_row + 1
    cmap = COL_MAP.get(type_key, {})
    sections = []
    current_project, current_task = '', ''
    for row_idx in range(hr + 1, ws.max_row + 1):
        row_vals = {}
        for col_letter, label in cmap.items():
            v = ws[f'{col_letter}{row_idx}'].value
            if v: row_vals[label] = str(v).strip()
        if not row_vals: continue
        if '所属项目' in row_vals: current_project = row_vals['所属项目']
        if '所属任务' in row_vals: current_task = row_vals['所属任务']
        title = ' — '.join(p for p in [current_task, row_vals.get('单元',''), row_vals.get('知识点','')] if p)
        md = f"## Section: {title}\n\n"
        for label, val in row_vals.items():
            md += f"- **{label}**: {val}\n"
        sections.append(md)
    wb.close()
    return '\n---\n\n'.join(sections)
```

## Outline Editing (Preserve Formatting)

```python
from openpyxl import load_workbook

def edit_cell(path, row, col_letter, new_value, output_path=None):
    wb = load_workbook(path)
    ws = wb.active
    ws[f'{col_letter}{row}'].value = new_value
    wb.save(output_path or path)
```

## Template Copy

```python
from pathlib import Path
from shutil import copy2

TEMPLATE_DIR = Path(__file__).parent.parent.parent / 'workspace-edu-tl' / 'knowledge-base' / 'templates'
TEMPLATE_MAP = {
    'textbook': 'template-textbook-outline.xlsx',
    'course': 'template-course-outline.xlsx',
    'training': 'template-training-outline.xlsx',
}

def create_from_template(type_key, output_path):
    copy2(TEMPLATE_DIR / TEMPLATE_MAP[type_key], output_path)
```

---
name: md2pdf
description: "Convert Markdown to professionally typeset PDF using reportlab. CJK/Latin mixed text, code blocks, tables, cover page, clickable TOC, PDF bookmarks, watermarks, 10 color themes. Do not use for LaTeX math, HTML conversion, OCR, image merge, or interactive forms."
triggers:
  - "markdown to pdf"
  - "md to pdf"
  - "md转pdf"
  - "生成 pdf 报告"
  - "md2pdf"
  - "any2pdf"
  - "排版 PDF"
  - "markdown typeset"

negative_triggers:
  - "读取 PDF"
  - "提取 PDF 文字"
  - "合并 PDF"
  - "拆分 PDF"
  - "markdown to html"
  - "md转html"
user-invocable: true
agent-usable: true
readiness: production-ready
type: tool-wrapper
---

# md2pdf — Markdown to Professional PDF

纯 Python + reportlab，零重依赖（~5MB），从 Markdown 生成出版级 PDF。
基于 [lovstudio/any2pdf](https://github.com/lovstudio/any2pdf)，适配 OpenClaw。

## When to Use

- `.md` → `.pdf`，尤其是含 CJK 字符的文档
- 需要封面、目录、书签、水印、代码块保真
- 用户提到"md转pdf"、"生成报告PDF"等

## When NOT to Use

- 纯英文无 CJK 且需要 LaTeX 级数学公式排版 → 用 pandoc + LaTeX
- 从 HTML/Word/PPT 转 PDF → 用对应专用工具
- 需要 OCR 或扫描件转 PDF → 不适用
- 批量图片合并为 PDF → 用 pypdf/img2pdf
- 用户要求交互式填表/表单 PDF → 非本技能职责

## Quick Start

```bash
python3 <skill-dir>/scripts/md2pdf_v3.py \
  --input input.md \
  --output output.pdf \
  --title "标题" \
  --author "作者" \
  --theme warm-academic
```

仅 `--input` 必填，其余有合理默认值。

## Usage Flow

### 1. Gather Options (ask once)

当用户没有明确指定参数时，一次性确认：

```
开始转 PDF！确认几个选项 👇

📐 设计风格：
 a) 暖学术  b) 经典论文  c) Tufte  d) 期刊蓝
 e) 精装书  f) 中国红   g) 水墨  h) GitHub
 i) Nord冰霜  j) 海洋
 k) 教材绿  l) 教材赛博

🖼 扉页图片：1)跳过  2)本地图片  3)AI生成
💧 水印：1)不加  2)自定义文字
📇 封底物料：1)跳过  2)图片  3)纯文字

示例："a, 扉页跳过, 水印:仅供学习参考"
```

**用户已明确指定参数时直接执行，不重复询问。**

### 2. Execute

```bash
# 检查依赖
python3 -c "import reportlab" 2>/dev/null || pip3 install reportlab

# 生成 PDF
python3 <skill-dir>/scripts/md2pdf_v3.py \
  --input "$INPUT_FILE" \
  --output "$OUTPUT_FILE" \
  --title "$TITLE" \
  --author "$AUTHOR" \
  --theme "$THEME" \
  ${WATERMARK:+--watermark "$WATERMARK"} \
  ${FRONTISPIECE:+--frontispiece "$FRONTISPIECE"} \
  ${BANNER:+--banner "$BANNER"}
```

### 3. Deliver

生成成功后用 message tool 发送 PDF 文件给用户。

## Theme Mapping

| 用户选择 | --theme | 灵感来源 |
|----------|---------|----------|
| a) 暖学术 | `warm-academic` | Lovstudio design system |
| b) 经典论文 | `classic-thesis` | LaTeX classicthesis |
| c) Tufte | `tufte` | Edward Tufte |
| d) 期刊蓝 | `ieee-journal` | IEEE journal |
| e) 精装书 | `elegant-book` | LaTeX ElegantBook |
| f) 中国红 | `chinese-red` | 中文正式文档 |
| g) 水墨 | `ink-wash` | 水墨画 |
| h) GitHub | `github-light` | GitHub Markdown |
| i) Nord冰霜 | `nord-frost` | Nord color scheme |
| j) 海洋 | `ocean-breeze` | — |
| k) 教材绿 | `textbook-green` | 机械/工程类教材 |
| l) 教材赛博 | `textbook-cyber` | 计算机类专业教材 |

详见 `references/themes.md`。

## CLI Reference

| Argument | Default | Description |
|----------|---------|-------------|
| `--input` | (必填) | Markdown 文件 |
| `--output` | `output.pdf` | 输出路径 |
| `--title` | 首个 H1 | 封面标题 |
| `--subtitle` | `""` | 副标题 |
| `--author` | `""` | 作者 |
| `--date` | 今天 | 日期 |
| `--version` | `""` | 版本号 |
| `--watermark` | `""` | 水印文字 |
| `--theme` | `warm-academic` | 主题 |
| `--theme-file` | `""` | 自定义主题 JSON |
| `--cover` | `true` | 封面 |
| `--toc` | `true` | 目录 |
| `--page-size` | `A4` | 纸张 |
| `--frontispiece` | `""` | 扉页图片 |
| `--banner` | `""` | 封底图片 |
| `--header-title` | `""` | 页眉标题 |
| `--footer-left` | author | 页脚左侧 |
| `--stats-line` | `""` | 封面统计1 |
| `--stats-line2` | `""` | 封面统计2 |
| `--edition-line` | `""` | 封面版次 |
| `--disclaimer` | `""` | 封底声明 |
| `--copyright` | `""` | 封底版权 |
| `--code-max-lines` | `30` | 代码块最大行数 |

## Architecture

```
Markdown → Preprocess(拆分合并标题) → Parse(code-fence感知) → Story(reportlab flowables) → PDF build
```

关键组件：
1. **Font system**: macOS Palatino/Songti SC/Menlo，Linux Carlito/Liberation/Droid
2. **CJK wrapper**: `_font_wrap()` — 字符级检测，动态插入 `<font face="CJK">`
3. **Mixed renderer**: `_draw_mixed()` — Canvas 层 CJK/Latin 段切换
4. **Code handler**: `esc_code()` — `\n→<br/>`、前导空格→`&nbsp;`
5. **Smart tables**: 按内容最大长度比例分配列宽，18mm 最低保障
6. **Bookmarks**: `ChapterMark` flowable 创建 PDF 侧栏书签 + 命名锚点

## Error Handling

| 错误 | 处理 |
|------|------|
| `--input` 文件不存在 | 报错并提示用户检查路径 |
| reportlab 未安装 | 自动 `pip3 install reportlab`，失败则提示安装命令 |
| Markdown 解析异常 | 检查文件编码是否 UTF-8 |
| CJK 字体缺失 | 脚本内置多平台 fallback，macOS 必定可用 |
| PDF 生成超时 | 脚本无网络依赖，超时只可能是超大文件，建议分段处理 |

## Gotchas

| 问题 | 表现 | 解决 |
|------|------|------|
| CJK 显示为 □ | reportlab Paragraph 用了 Latin 字体 | 所有含 CJK 的文本必须过 `_font_wrap()`（脚本已内置） |
| 代码块换行消失 | reportlab 把 `\n` 当空白 | `esc_code()` 预处理（脚本已内置） |
| 封面/页脚中文乱码 | `drawString()` 不支持 CJK | 用 `_draw_mixed()` 代替（脚本已内置） |
| CJK 行断在英文词中间 | 默认按空格断行 | body/bullet style 已设 `wordWrap='CJK'` |

## Dependencies

```bash
pip3 install reportlab
```

## Internal Acceptance

- **Happy-path**: 用含中英文混排 + 代码块 + 表格的测试 md 生成 PDF
- **Expected**: 封面正常、目录可点击、代码块保真、CJK 无 □
- **Command**: `python3 <skill-dir>/scripts/md2pdf_v3.py --input test.md --output test.pdf --title "测试" --theme warm-academic`

## Delivery Contract

Do **not** report "skill creation complete" unless: quick-validate ✓ → strict-validate ✓ → internal acceptance ✓ → integration proven.
Only `integrated` skills may be reported as complete to the user.
On failure: report exact failures + recommended next step.

## Source

基于 [lovstudio/any2pdf](https://github.com/lovstudio/any2pdf) (MIT License)，适配 OpenClaw 技能规范。

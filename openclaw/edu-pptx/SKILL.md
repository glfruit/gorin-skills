---
name: edu-pptx
description: >
  教学课件 PPT 生成与编辑的统一入口。从零创建用 PptxGenJS，编辑已有 PPT 用 OfficeCLI，
  对外展示类可选用 banana-slides。支持教学主题系统和视觉 QA 流程。
triggers:
  - "生成课件"
  - "制作PPT"
  - "教学课件"
  - "生成幻灯片"
  - "create slides"
  - "courseware"
negative_triggers:
  - "快速出图"
  - "图片式PPT"
---

# edu-pptx — 教学课件 PPT 技能

教学课件 PPT 的统一入口。从零创建用 PptxGenJS，编辑已有 PPT 用 OfficeCLI。

## 工具选择

| 场景 | 工具 | 说明 |
|------|------|------|
| 从零创建教学课件 | **PptxGenJS** | 可编辑、设计感强、3分钟出稿 |
| 编辑已有 PPT | **OfficeCLI** | 批量改文字/表格 |
| 对外展示/精品申报 | **banana-slides** | 图片式，视觉精致，不可编辑 |
| 快速出图 | **baoyu-slide-deck** | 非教学场景 |

**核心规则：教学课件一律用 PptxGenJS。**

## 主题系统

### 选择流程

1. 确认课程类型 → 自动匹配主题，或展示主题预览让教师选
2. 读取对应主题文件（`themes/{type}.md`）
3. 将主题配色/字体填入 PptxGenJS 脚本
4. 执行生成 → QA → 交付

### 课程类型 → 主题映射

| 课程类型 | 主题文件 | 风格描述 |
|---------|---------|---------|
| 工科/制造/机械 | `engineering` | Forest Canopy 变体，深绿工业风 |
| 计算机/IT/开发 | `computing` | Tech Innovation 变体，深蓝科技风 |
| 人文/传统文化 | `humanities` | Desert Rose 变体，水墨暖色调 |
| 通识/职业素养 | `general` | Modern Minimalist 变体，灰白简约 |
| 安全/应急教育 | `safety` | Ocean Depths 变体，深蓝专业风 |

### 自定义主题

教师可要求自定义配色。创建步骤：
1. 生成新主题 .md 文件到 `themes/` 目录
2. 包含：主题名、4 色配色板（primary/secondary/accent/dark）、字体搭配
3. 展示给教师确认后应用

## PptxGenJS 快速参考

详细 API 文档见 [pptxgenjs.md](pptxgenjs.md)。

### 最小可运行示例

```javascript
const pptxgen = require("pptxgenjs");
let pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "Edu Squad";

let slide = pres.addSlide();
slide.background = { color: "1A3C2A" };
slide.addText("课程标题", { x: 0.5, y: 1.5, w: 9, h: 1.5, fontSize: 44, fontFace: "Georgia", color: "FFFFFF", bold: true, align: "center" });

pres.writeFile({ fileName: "output.pptx" });
```

### 常见陷阱

1. **颜色不加 # 前缀** — `color: "FF0000"` ✅ `color: "#FF0000"` ❌
2. **不用 unicode 圆点** — 用 `bullet: true` 而不是 "•"
3. **多行文本用 breakLine: true**
4. **不要复用 option 对象** — pptxgenjs 会 in-place 修改
5. **shadow offset 不能为负数** — 用 angle: 270 + 正 offset
6. **不要用 8 位 hex 颜色** — 用 opacity 属性代替

## 编辑已有 PPT

### OfficeCLI 批量编辑

```bash
# 查看内容
python -m markitdown presentation.pptx

# OfficeCLI 改文字（查看 officecli --help 获取完整命令）
officecli slide edit --file presentation.pptx --slide 5 --shape 1 --text "新内容"
```

### XML 解包编辑（精细操作）

详细流程见 [editing.md](editing.md)。

```bash
python scripts/office/unpack.py input.pptx unpacked/
# 编辑 XML...
python scripts/office/pack.py unpacked/ output.pptx --original input.pptx
```

## 视觉 QA 流程（必须执行）

### 内容 QA

```bash
python -m markitdown output.pptx
```

检查：内容缺失、错别字、顺序错误、残留占位符。

### 视觉 QA

```bash
# 转 PDF → 图片
soffice --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

生成 slide-01.jpg, slide-02.jpg ... 后用子 agent 检查：

```
视觉检查这些幻灯片，找出所有问题：
- 元素重叠（文字穿过形状）
- 文字溢出或被截断
- 对比度不足
- 间距不均匀
- 0.5" 以内边距不足
检查图片：slide-01.jpg 到 slide-N.jpg
```

### 验证循环

1. 生成 → 转图片 → 检查
2. 列出问题
3. 修复
4. 重新验证受影响的页面
5. 直到一轮检查无新问题

## 读取内容

```bash
# 文本提取
python -m markitdown presentation.pptx

# 缩略图网格
python scripts/thumbnail.py presentation.pptx

# 原始 XML
python scripts/office/unpack.py presentation.pptx unpacked/
```

## 依赖

- `npm install -g pptxgenjs react-icons react react-dom sharp` — PptxGenJS + 图标
- `pip install "markitdown[pptx]"` — 文本提取
- `pip install Pillow` — 缩略图
- LibreOffice (`soffice`) — PDF 转换
- Poppler (`pdftoppm`) — PDF 转图片
- OfficeCLI — 批量编辑（可选）

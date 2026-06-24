# 教学视觉与格式化技能

本文档说明 `baoyu-skills` 中视觉、图解、图片压缩和 Markdown 格式化思路如何被吸收为教学团队可用的 `gorin-edu-*` 技能。

## 设计原则

1. 不直接使用第三方技能。第三方技能只作为流程、结构和分类方法的参考。
2. 所有教学团队定制技能统一使用 `gorin-edu-*` 前缀。
3. Markdown 是教材、课程和培训资料的源稿真源；DOCX、PDF、PPTX、HTML 是交付形态。
4. 配图、图表、信息图必须有占位符、题注、来源、生成提示词或确定性 source、QA 记录和 manifest 条目。
5. 每张图必须先确定 `figure_type`、`engine`、`engine_reason`；能脚本或确定性工具生成的，不交给 AI 图像生成。
6. 格式化技能只做结构和版式规范化，不改写事实、观点、教学目标和章节结构。
7. 能脚本检查的内容不交给 LLM 猜，技能只负责触发正确流程和保存证据。

## 借鉴来源

| baoyu 技能 | 可借鉴点 | gorin 适配技能 |
| --- | --- | --- |
| `baoyu-article-illustrator` | 先分析文章结构，再决定插图位置、类型和提示词 | `gorin-edu-chapter-illustrator` |
| `baoyu-diagram` | 图解分类、SVG 自包含、留白和层级规则 | `gorin-edu-diagram-designer` |
| `baoyu-infographic` | layout × style 的信息图设计思路 | `gorin-edu-infographic-designer` |
| `baoyu-format-markdown` | frontmatter、标题、列表、代码块、CJK/English spacing 规范化 | `gorin-edu-markdown-polisher` |
| `baoyu-compress-image` | 多工具压缩、WebP/PNG 优先级、批处理思路 | `gorin-edu-image-optimizer` |
| `baoyu-markdown-to-html` | Markdown 到 HTML 的主题化输出和 Mermaid 渲染经验 | 后续可演进为 `gorin-edu-html-publisher` |
| `baoyu-slide-deck` | 图文式 slide deck 的拆页和视觉规划 | 后续可和 `gorin-edu-pptx` 合流 |

## 技能分工

### `gorin-edu-chapter-illustrator`

用于章节级配图规划。它不直接生成图片，而是输出：

- `design/visual-plan.md`
- `assets/figures/prompts/*.md`
- `assets/figures/source/*`
- 插入点占位符
- 题注建议
- QA 清单

它必须先完成 Figure Engine Policy 判断：结构图、流程图、数据模型图、代码结果图、统计图、表格图、真实界面图优先使用 Mermaid/SVG/HTML/Python/真实截图；AI 图像只用于情境、封面和低事实风险概念图。

适用场景：教材章节、培训讲义、课程讲义需要概念图、案例图、活动卡、流程插图。

### `gorin-edu-diagram-designer`

用于生成可审计的教学图解规格。推荐输出：

- `assets/diagrams/specs/*.md`
- `assets/diagrams/source/*.svg` 或 Mermaid 源
- `assets/diagrams/rendered/*`
- manifest 条目

适用场景：流程、架构、状态机、数据流、时间线、结构关系。

### `gorin-edu-infographic-designer`

用于信息图和视觉摘要。它要求先绑定学习目标和评价证据，再选择 layout。

适用场景：知识图谱、能力图谱、章节总结、讲座海报页、课程路线图。

### `gorin-edu-markdown-polisher`

用于 Markdown 源稿格式治理。它只能修改：

- frontmatter 结构
- 标题层级格式
- 列表和缩进
- 代码围栏
- 表格 Markdown
- CJK/English spacing

它不能改写事实、观点、章节顺序或教学内容。

### `gorin-edu-image-optimizer`

用于图片资产压缩和衍生版本管理。它必须保留原图，不允许覆盖源文件。

推荐输出：

- `assets/images/originals/`
- `assets/images/optimized/`
- `assets/images/image-optimization-report.md`
- manifest 更新记录

## 教学团队接入建议

在教材、课程和培训资料三条产品线中，这组技能应作为“能力包”按需加载：

- 章节设计阶段：加载 `gorin-edu-chapter-illustrator`、`gorin-edu-diagram-designer`
- 内容编写阶段：加载 `gorin-edu-markdown-polisher`
- 视觉增强阶段：加载 `gorin-edu-infographic-designer`
- 交付打包阶段：加载 `gorin-edu-image-optimizer`

不要把全部技能常驻注入教学团队 TL prompt。应由能力解析器根据产品线、阶段和 action 动态注入，避免 prompt 膨胀。

## 验收标准

新增或修改教学视觉技能时至少满足：

- 技能名使用 `gorin-edu-*`
- `SKILL.md` 包含 `name`、`description`、`homepage`
- 每个技能有 `README.md`、`LICENSE`
- 有模板或 checklist 放在 `references/`
- 文档明确“可做什么”和“不能做什么”
- 能通过 `scripts/validate-skill.sh`

# Edu Chapter Illustrator

教学团队专用章节配图规划技能。它吸收 `baoyu-article-illustrator` 的
“先分析、再规划、再保存 prompt、最后生成与 QA”的优点，但不直接调用或依赖
baoyu skill。

## 适用场景

- 教材章节需要插图、流程图、案例场景图或活动卡。
- 培训讲义需要解释性配图。
- 课程资源需要把抽象概念转成可视化学习支架。

## 核心产出

- 视觉规划：`design/visual-plan.md`
- 生成提示词：`assets/figures/prompts/*.md`
- 确定性图源：`assets/figures/source/*`
- 图像资产：`assets/figures/generated/*`
- QA 记录：`assets/figures/qa/*.md`
- 图表清单：项目 `design/figure-manifest.json`

## 原则

- 先锁定 Markdown 源稿。
- 每张图必须服务学习目标。
- 每张图必须先确定 `figure_type`、`engine`、`generator_route`、`generation_backend` 和 `engine_reason`。
- `generation_backend` 必须是受控渲染器、脚本或已批准的 `gorin-*` 技能，不能写成“随便用某个图片工具”。
- 能用 Mermaid / SVG / HTML / Python / 真实截图生成的，不使用 AI 图像生成。
- 数据模型、代码结果、真实界面、表格和统计图禁止 AI 编造。
- 二维码必须由真实目标值确定性生成；目标暂缺时必须登记 `target_status`、`target_note` 和证据路径，不能把占位二维码当成完成图。
- 每张图必须有插入占位符、题注和 QA 证据。
- 不直接把第三方技能输出当作可交付成果。

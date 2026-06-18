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
- 图像资产：`assets/figures/generated/*`
- QA 记录：`assets/figures/qa/*.md`
- 图表清单：项目 `design/figure-manifest.json`

## 原则

- 先锁定 Markdown 源稿。
- 每张图必须服务学习目标。
- 每张图必须有插入占位符、题注和 QA 证据。
- 不直接把第三方技能输出当作可交付成果。

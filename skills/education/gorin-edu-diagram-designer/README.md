# Edu Diagram Designer

教学团队图解设计技能，用于生成教材、课程和培训资料中的流程图、结构图、状态图、
数据流图、时间线和架构图。

它借鉴 `baoyu-diagram` 的图型分类、布局和 SVG 纪律，但要求先生成图解规格、
源文件和 manifest 记录，再进入渲染和 QA。

## 推荐目录

```text
assets/diagrams/
  specs/
  source/
  rendered/
  qa/
```

## 关键要求

- 源稿为 Markdown。
- 每张图都有题注和占位符。
- 每张图都进入 `design/figure-manifest.json`。
- 复杂图必须拆分，不能一图塞完整章。

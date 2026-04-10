---
type: interactive-reader
updated: 2026-03-27
based_on: book-reader-notes, web-reader, web-content-fetcher
---

# Interactive Reader 创建经验

## 核心模式

**状态跟踪是关键**：
- 记录阅读进度（章节、页码、百分比）
- 持久化到 JSON 文件，session 重启后恢复
- 用 `~/.openclaw/workspace-{name}/data/{skill-name}/` 存储状态

**尊重用户节奏**：
- 不要一次灌太多内容——按段落/章节/时间分块
- 提供暂停、跳过、回顾的交互选项
- 长文档提供 summary → detail 的渐进式展示

**笔记同步**：
- 读书笔记直接写入 PKM vault（通过 pkm-save-note 或直接写 Markdown）
- 高亮/标注关联到原文位置
- 自动生成读书摘要和关键摘录

## 常见陷阱

- 一次性加载整本书到 context → context overflow
- 不跟踪进度 → 每次 restart 从头读
- 忽略 PDF 扫描版 OCR 问题 → 提取乱码
- 忽略用户已读标记 → 重复推送

## 质量信号

- 恢复中断会话不需要用户重复说明
- 笔记有精确的原文引用位置
- 摘要不是泛泛的"本书讲了..."，而是按章节的具体要点

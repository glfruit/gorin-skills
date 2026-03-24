# Vault 目录结构参考

## octopus（主 vault）

```
octopus/
├── Home/                    ← 仪表盘、索引页
│   ├── Home.md
│   ├── Today.md
│   ├── Active Projects.md
│   ├── Areas.md
│   ├── PARA Overview.md
│   ├── Zettel Index.md
│   ├── Idea Creator Guide.md
│   └── Skills and Workflows.md
├── Calendar/
│   ├── Journal/
│   │   └── Daily/
│   │       └── YYYY/YYYY-MM/YYYY-MM-DD.md
│   ├── Reviews/
│   │   └── YYYY/YYYY-MM Review.md
│   └── Logs/
├── Zettels/
│   ├── 1-Fleeting/          ← 闪念笔记（临时）
│   ├── 2-Literature/        ← 文献笔记
│   │   ├── Books/
│   │   │   └── {Book Title}/
│   │   │       ├── MoC-{Book}.md
│   │   │       ├── Reading-Plan-{Book}.md
│   │   │       ├── Inspectional-Reading-{Book}.md
│   │   │       └── Ch{NN}-{Section}.md
│   │   ├── Papers/
│   │   └── Articles/
│   ├── 3-Permanent/         ← 永久笔记（原子化，每个一个观点）
│   │   └── {YYYYMMDDHHMM}-{title}.md
│   └── 4-Structure/         ← 结构笔记（MOC、周报、索引）
├── Efforts/
│   ├── 1-Projects/
│   │   ├── Active/
│   │   └── Done/
│   ├── 2-Areas/
│   └── 3-Works/
├── Archives/
│   └── Temp-Files/
│       └── 0.Inbox/
└── .obsidian/               ← Obsidian 配置（不要手动修改）
```

## PKM Core 分类映射

PKM Core 的 `smart-classifier.sh` 根据笔记类型自动确定存放目录：

| type | 目录 | 模板 |
|------|------|------|
| log | `Zettels/1-Fleeting` | fleeting |
| thought | `Zettels/1-Fleeting` | fleeting |
| idea | `Zettels/1-Fleeting` | idea |
| meeting | `Efforts/1-Projects` | meeting |
| plan | `Efforts/1-Projects` | plan |
| summary | `Zettels/3-Permanent` | zettel |
| review | `Efforts/2-Areas` | review |
| decision | `Zettels/3-Permanent` | zettel |
| literature | `Zettels/2-Literature` | literature |

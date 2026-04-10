# Vault 目录结构参考

## atlas（知识图谱）

```
atlas/
├── 1-Literature/           ← 文献笔记（Agent 自动分类归档）
│   ├── Papers/             ← 学术论文
│   ├── Books/              ← 书籍
│   ├── Articles/           ← 博客/网页/公众号文章
│   ├── Repos/              ← 代码仓库笔记
│   ├── Podcasts/           ← 播客/视频笔记
│   └── Tweets/             ← X/Twitter thread 存档
├── 2-Concepts/             ← 概念节点（跨文献的知识图谱核心）
├── 3-Permanent/            ← 原子笔记（从文献中提取的独立观点）
├── 4-Structure/
│   ├── MOC/                ← Map of Content（主题索引）
│   ├── Index/              ← LLM 维护的索引文件
│   │   ├── papers-index.md
│   │   ├── concepts-index.md
│   │   └── areas-index.md
│   └── Queries/            ← 查询产物回填
├── 5-Areas/                ← 知识领域分类
│   ├── AI-ML/
│   ├── Education/
│   ├── Engineering/
│   ├── Research-Method/
│   ├── Policy/
│   ├── Management/
│   └── ...
├── 6-Outputs/              ← 多格式输出产物
│   ├── PDF/ Slides/ Charts/ Reports/
├── 7-Templates/            ← 笔记模板
├── 8-Assets/               ← 图片/附件资源
├── 9-Clippings/            ← Obsidian Web Clipper 剪藏
└── .state/                 ← 处理状态（不纳入版本管理）
    └── dropbox.db          ← SQLite 增量扫描状态
```

## octopus（日常管理）

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

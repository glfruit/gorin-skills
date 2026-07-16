---
type: pkm-integration
updated: 2026-03-25
based_on: pkm-save-note, idea-creator, zk-para-zettel, zk-router, voice-to-zettel, obsidian-ontology-sync
---

# PKM Integration 创建经验

## 核心模式

**frontmatter 是骨架，不是装饰**：
- 每条笔记必须有 frontmatter（type、tags、created、sources）
- frontmatter 里的字段决定笔记的生命周期（归档、回顾、搜索）
- 用 frontmatter 做自动分类，不靠目录结构

**关系发现是核心竞争力**：
- 新笔记创建时，主动搜索已有笔记找关联
- 5-type relations（链接、引用、灵感、对比、补充）比双向链接更有信息量
- 关系写在 frontmatter 或正文末尾的 `## Connections` 段

**原子笔记 > 长文档**：
- 一个笔记一个核心观点
- 方便引用和关联
- 长文档拆分后更容易被搜索到

## 笔记路径规范

```
Vault/
├── Zettels/
│   ├── 1-Fleeting/    # 临时笔记，定期整理或归档
│   ├── 2-Permanent/   # 永久笔记，有完整 frontmatter
│   ├── 3-Structure/   # MOC（Map of Content），索引笔记
│   └── 4-Reference/   # 文献摘录、网页存档
├── Projects/           # PARA: Projects
├── Areas/              # PARA: Areas
└── Resources/          # PARA: Resources
```

## 常见陷阱

| 陷阱 | 表现 | 解决 |
|------|------|------|
| 笔记堆砌 | 大量无关联笔记 | 创建时强制搜关联 |
| frontmatter 混乱 | 字段不一致 | 用模板 + 验证脚本 |
| Fleeting 笔记膨胀 | 1-Fleeting/ 里几百条不整理 | 定期清理（cron 或手动） |
| 重复笔记 | 同一主题多个笔记 | 创建前去重搜索 |
| 归档过度 | 什么都想永久保存 | Fleeting 有时效性，该删就删 |

## 验证清单

- [ ] frontmatter 格式统一
- [ ] 创建时有去重搜索
- [ ] 有关系发现步骤
- [ ] 目录结构遵循规范

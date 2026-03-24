---
name: zk-router
description: "ZK 统一笔记路由系统。单关键词'zk'触发，智能判断内容类型，自动路由到合适的笔记技能。"
triggers: ["zk", "保存到笔记", "save to notes", "note this"]
user-invocable: true
command-dispatch: tool
agent-usable: true
requires:
  skills: [pkm-core, pkm-save-note, zk-para-zettel, idea-creator]
---

# ZK Router — 统一笔记路由系统 v1.0

**核心理念**：只记一个词 `zk`，系统自动判断内容类型并保存到正确位置。

---

## 触发方式

### 用户触发
- `zk <内容>` — 主触发词
- `保存到笔记` / `save to notes` — Agent兼容

### Agent触发
- Agent说"保存到笔记"自动调用

---

## 智能路由逻辑

### 判断流程

```
用户输入: zk <内容>
    ↓
Step 1: URL检测 (置信度 +40%)
    ├── 微信公众号/mp.weixin.qq.com → literature/articles
    ├── 知乎/zhihu.com → literature/articles
    ├── 技术博客/文档站点 → literature/articles
    ├── 学术论文/arXiv/pdf → literature/papers
    └── GitHub/代码仓库 → literature/code
    
Step 2: 关键词检测 (置信度 +30%)
    ├── "会议/讨论/和XX聊/复盘" → meeting
    ├── "想法/灵感/突然想到/idea" → idea
    ├── "计划/task/待办/TODO" → plan
    ├── "周总结/月回顾/复盘" → review
    ├── "读书/看《XXX》/读后感" → literature/books
    └── "决策/决定/选择" → decision
    
Step 3: 内容特征 (置信度 +20%)
    ├── 长度 > 1000字 → 可能summary
    ├── 有明确结构(1./- /标题) → 可能summary
    └── 长度 < 50字 → fleeting
    
Step 4: 来源上下文 (置信度 +10%)
    ├── 来自 daily-collector → literature (默认)
    ├── 来自 edu-tl 且含"会议" → meeting
    └── 来自群聊 → 可能需要确认

Step 5: 决策
    ├── 总分 ≥ 80% → 直接保存
    ├── 50% ≤ 总分 < 80% → 保存+提示可调整
    └── 总分 < 50% → 询问确认
```

### 类型映射

| 判断类型 | 目标Skill | 保存位置 |
|----------|-----------|----------|
| literature/articles | zk-para-zettel | Zettels/2-Literature/Articles/ |
| literature/papers | zk-para-zettel | Zettels/2-Literature/Papers/ |
| literature/books | zk-para-zettel | Zettels/2-Literature/Books/ |
| idea | idea-creator | Zettels/1-Fleeting/ |
| meeting | pkm-save-note | Efforts/1-Projects/ |
| plan | pkm-save-note | Efforts/1-Projects/ |
| review | pkm-save-note | Calendar/Reviews/ |
| decision | pkm-save-note | Zettels/3-Permanent/ |
| summary | pkm-save-note | Zettels/3-Permanent/ |
| fleeting (默认) | pkm-save-note | Zettels/1-Fleeting/ |

---

## 响应模式

### 高置信度 (≥80%)
```
✅ 已保存为 [类型]

📄 标题: {title}
📁 位置: {path}
🏷️ 标签: {tags}

[相关笔记: xxx, xxx]
```

### 中置信度 (50-80%)
```
✅ 已保存为 [类型] (置信度: {score}%)

📄 标题: {title}
📁 位置: {path}

如需调整，回复:
• 改zku - 转为文献笔记
• 改zki - 转为想法笔记
• 改zkm - 转为会议记录
• 其他类型请说明
```

### 低置信度 (<50%)
```
🤔 难以确定类型，请选择:

1. 文献笔记 (zku) - 文章/网页摘录
2. 想法笔记 (zki) - 灵感/闪念
3. 会议记录 (zkm) - 会议纪要
4. 计划任务 (zkt) - 待办/计划
5. 其他 (请说明)

或回复"默认"保存为闪念笔记。
```

---

## Agent调用方式

### 标准调用
```
Agent: "保存到笔记"

系统自动:
1. 分析当前上下文
2. 判断内容类型
3. 调用对应skill
4. 返回保存结果
```

### 带类型提示
```
Agent: "保存到笔记 (会议纪要)"

zk-router识别提示词，提高meeting类型权重
```

---

## 快速调整

保存后如需调整类型，回复：

| 指令 | 动作 |
|------|------|
| `改zku` | 转为文献笔记 |
| `改zki` | 转为想法笔记 |
| `改zkm` | 转为会议记录 |
| `改zkt` | 转为计划任务 |
| `改zkl` | 转为文献(书籍) |
| `删除` | 删除刚保存的笔记 |

---

## 依赖

- `pkm-core` — vault路径、frontmatter规范
- `pkm-save-note` — 通用笔记保存执行
- `zk-para-zettel` — 文献笔记执行
- `idea-creator` — 想法笔记执行

---

## Changelog

### v1.0.0 (2026-03-23)
- 初始版本
- 单关键词`zk`智能路由
- 置信度分级响应
- Agent统一入口


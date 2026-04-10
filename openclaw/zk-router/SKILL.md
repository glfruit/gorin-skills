---
name: zk-router
description: "PKM 统一入口。zk <内容> 智能路由。pks/pkr/pko/pkp/pkh 快捷命令。"
triggers: ["zk", "pks", "pkr", "pko", "pkp", "pkh"]
user-invocable: true
command-dispatch: tool
agent-usable: true
requires:
  skills: [pkm-core, pkm-save-note, zk-literature, idea-creator, pkm-para-manager, obsidian-md]
---

# ZK Router — PKM 统一入口 v2.1

**唯一入口**：所有笔记操作都通过此路由。

## 多 Vault 支持（v2.1）

支持 `--vault` 参数路由到不同 vault：

```bash
python3 zk.py "some content" --vault atlas
python3 zk.py "some content" --vault octopus
python3 zk.py "some content" --vault loom
```

| Vault | 路径 | 角色 | 类型映射来源 |
|-------|------|------|------------|
| `atlas` | `~/pkm/atlas/` | 知识图谱 | vault-config.yaml → atlas.type_mapping |
| `octopus` | `~/Workspace/PKM/octopus/` | 日常管理 | vault-config.yaml → octopus.type_mapping |
| `loom` | `~/pkm/loom/` | 内容创作 | vault-config.yaml → loom.type_mapping |

**默认行为**：不传 `--vault` 时路由到 `octopus`（向后兼容）。

类型→目录映射由 `~/.gorin-skills/openclaw/pkm-core/vault-config.yaml` 唯一定义。

## 触发词

| 触发词 | 功能 | 目标 |
|--------|------|------|
| `zk` | 通用笔记（自动判断类型） | 智能路由 |
| `想法` / `idea` | 快速记闪念 | idea-creator |
| `pks <query>` | 搜索 vault | 内置 grep |
| `pkr` | 生成周报 | pkm-para-manager |
| `pko` | 孤儿笔记检测 | pkm-para-manager |
| `pkp [keyword]` | 闪念→永久升级 | pkm-save-note |
| `pkh` / `pkh full` | 全库健康扫描（v2，12指标） | pkm-para-manager |

## 路由逻辑

## 实现状态（2026-03-28）

| 能力 | 状态 | 当前实现 |
|---|---|---|
| 统一入口 | ✅ | `pkm_clip.py` 仅作兼容转发到 `zk-router` |
| 主执行引擎 | ✅ | `zk.py`（Python 主实现），`zk.sh` 薄包装 |
| 类型判定 | ✅ | `router.py`（Python 主实现）+ `router.sh` 薄包装 |
| 文献抓取 | ✅ | web-reader（带重试） |
| 去重 | ✅ | source_url + title，含候选打分 + dedup index 优先 |
| dedup policy | ✅ | 读取 `pkm_dedup_policy.json`，支持 intentional 标记 |
| force 新建 | ✅ | `ZK_FORCE=1` |
| metadata/frontmatter 对齐 | ✅ | URL 文献主路径已统一 author/published/site/captured_via |
| 关系发现/原子卡片 | ✅ | 已接入并默认开启（可用环境变量临时覆盖） |

### zk <内容> [--vault NAME]

```
Step 1: URL 检测（置信度 +40%）
    ├── 微信公众号/mp.weixin.qq.com → zk-literature
    ├── 知乎/zhihu.com → zk-literature
    ├── 技术博客/文档站点 → zk-literature
    ├── 学术论文/arXiv/pdf → zk-literature
    └── GitHub/代码仓库 → zk-literature

Step 2: 关键词检测（置信度 +30%）
    ├── "会议/讨论/和XX聊/复盘" → pkm-save-note(meeting)
    ├── "计划/task/待办" → pkm-save-note(plan)
    ├── "周总结/月回顾" → pkm-save-note(review)
    ├── "决定/选择" → pkm-save-note(decision)
    └── 无明确关键词 → Step 3

Step 3: 内容特征（置信度 +20%）
    ├── 长度 > 500字 + 有结构 → pkm-save-note(insight)
    ├── 长度 > 1000字 → pkm-save-note(summary)
    └── 长度 < 50字 → idea-creator

Step 4: 来源上下文（置信度 +10%）
    ├── 来自 daily-collector + URL → zk-literature
    └── 来自群聊 → 可能需要确认

Step 5: 决策
    ├── ≥ 80% → 直接保存
    ├── 50-80% → 保存 + 提示可调整
    └── < 50% → 询问确认
```

### pks <query>

```bash
VAULT="${HOME}/Workspace/PKM/octopus"
grep -rl "$query" "$VAULT" --include="*.md" -l | head -20
```

### pkr

调用 pkm-para-manager 的 `/pkm_para review`。

### pko

调用 pkm-para-manager 的 `/pkm_para orphans`。

### pkp [keyword]

调用 pkm-save-note 的 promote 子流程。

### pkh / pkh full

调用 pkm-para-manager 的 health-v2 全量扫描：

```bash
python3 ~/.gorin-skills/openclaw/pkm-para-manager/scripts/health-v2.py --vault ~/Workspace/PKM/octopus
```

输出：
- Markdown 报告：`Zettels/4-Structure/YYYYMMDD-PKM-Health-Report-WNN.md`
- JSON 指标：`Calendar/Logs/pkm-health-latest.json`


## 响应格式

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
```

### 低置信度 (<50%)
```
🤔 难以确定类型，请选择:

1. 文献笔记 - 文章/网页
2. 想法笔记 - 灵感/闪念
3. 会议记录
4. 计划任务
5. 永久笔记 - 成熟观点

或回复"默认"保存为闪念。
```

## When NOT to Use

- 内容不属于任何笔记类型。
- 纯系统命令或无关闲聊。

## Error Handling

- 路由失败时默认使用 pkm-save-note(fleeting)。
- 目标技能不存在时回退到手动创建。

## Changelog

### v2.1.0 (2026-04-04)
- 新增 `--vault` 参数支持 atlas / octopus / loom 多 vault 路由
- 类型映射从 vault-config.yaml 动态读取
- 默认 vault 仍为 octopus（向后兼容）

### v2.0.0 (2026-03-27)
- 合并 pkm-commands（pks/pkr/pko/pkp）
- 路由目标更新：zk-para-zettel → zk-literature
- 删除 /pkm_* 斜杠命令，改用简短触发词
- 新增 pkp promote 路由

### v1.0.0 (2026-03-23)
- 初始版本

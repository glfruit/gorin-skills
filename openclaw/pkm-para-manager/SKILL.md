---
name: pkm-para-manager
description: "PKM 治理与防退化引擎。提供 pkr(周报)、pko(孤儿检测)、pkh(全库健康评分 v2)。"
triggers: ["pkr", "pko", "pkh"]
user-invocable: false
command-dispatch: tool
agent-usable: true
requires:
  skills: [pkm-core]
  used-by: [zk-router]
---

# PKM PARA Manager — Governance v2.0

管理 PARA + Zettelkasten 融合库的健康度，避免 Obsidian 库随时间退化。

## 命令

| 命令 | 说明 |
|------|------|
| `pkr` | 周报（frontmatter.created 统计） |
| `pko` | 孤儿笔记检测（Permanent 为主） |
| `pkh` / `pkh full` | 全库健康扫描 v2（4 维 12 指标 + 100 分制） |

---

## pkh（健康扫描 v2）

执行脚本：

```bash
python3 ~/.gorin-skills/openclaw/pkm-para-manager/scripts/health-v2.py \
  --vault ~/Workspace/PKM/octopus
```

输出：
- 报告：`Zettels/4-Structure/YYYYMMDD-PKM-Health-Report-WNN.md`
- 机器指标：`Calendar/Logs/pkm-health-latest.json`

### 评分模型（100 分）

- Structure（25）：目录合规、命名合规
- Metadata（25）：frontmatter 合规、必填字段、日期合法性
- Graph（30）：孤儿率、出链覆盖、MOC 覆盖、断链率
- Content（20）：标题重复率、近重复率、Fleeting 积压率

等级：A≥90, B≥80, C≥70, D<70

### 关键阈值（告警）

- 孤儿率 > 15%（黄） / > 25%（红）
- 断链率 > 3%（黄） / > 8%（红）
- Fleeting 积压率 > 30%（黄）
- Frontmatter 合规率 < 95%（黄）

---

## pkr（周报）

必须按 `frontmatter.created` 统计，不使用 `find -mtime`（避免同步误报）。

简化统计逻辑：

```bash
VAULT="$HOME/Workspace/PKM/octopus"
WEEK_START=$(date -v-Mon +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)

grep -rl "created: " "$VAULT/Zettels" "$VAULT/Efforts" "$VAULT/Calendar" \
  --include="*.md" | xargs grep -l "created: $WEEK_START\|created: $TODAY"
```

---

## pko（孤儿检测）

```bash
find "$HOME/Workspace/PKM/octopus/Zettels/3-Permanent" -name "*.md" | while read f; do
  b=$(basename "$f" .md)
  c=$(grep -R "\[\[$b\]\]" "$HOME/Workspace/PKM/octopus" --include="*.md" | grep -v "$f" | wc -l)
  [ "$c" -eq 0 ] && echo "ORPHAN: $f"
done
```

---

## 与定时任务整合（推荐）

优先复用、减少任务数：

1. **每日轻巡检**（1 个任务）
   - 07:12 执行 `pkh`（不推送或仅异常推送）
2. **周治理合并任务**（1 个任务）
   - 周五 17:50 执行 `pkr + pko + pkh`（输出一页治理摘要）
   - 与现有周报时段相邻，避免再拆多个任务

---

## When NOT to Use

- 单条笔记保存（用 pkm-save-note / idea-creator）
- 文献处理（用 zk-literature）
- 非 Obsidian vault 管理

## Delivery Contract

- 返回 Markdown 摘要 + 报告路径
- 若触发告警阈值，给出 Top 风险与修复优先级
- 所有统计可在 `pkm-health-latest.json` 复核

---
name: pkm-para-manager
description: "PARA 方法实现。周报、项目状态、孤儿检测、vault 健康检查。"
triggers: ["para", "/para", "PARA", "/pkm_para"]
user-invocable: true
command-dispatch: tool
agent-usable: true
requires:
  skills: [pkm-core]
---

# PKM PARA Manager — PARA 管理 v1.1

管理 Projects-Areas-Resources-Archive 结构。

**前置依赖**: `pkm-core`

## 命令

| 命令 | 说明 |
|------|------|
| `/pkm_para review` | 生成周报 |
| `/pkm_para status` | 项目状态概览 |
| `/pkm_para orphans` | 孤儿笔记检测 |
| `/pkm_para health` | Vault 健康检查 |
| `/pkm_para archive <project>` | 归档项目 |

## 核心功能

### 周报

```bash
PKM="${HOME}/.openclaw/pkm/pkm"
VAULT="${HOME}/Workspace/PKM/octopus"

# 本周创建/修改的笔记
weekly_notes=$(find "$VAULT" -name "*.md" -mtime -7 -newer "$VAULT/.obsidian/app.json")

# 生成本周回顾
vars=$(jq -n --arg id "$(date +%Y%m%d%H%M)" --arg created "$(date +%Y-%m-%d)" \
    '{id: $id, title: "Weekly Review", created: $created}')

note=$($PKM template render "moc" "$vars")
echo "$note" > "$VAULT/Zettels/4-Structure/$(date +%Y%m%d)-PARA-Weekly-Review-W$(date +%V).md"
```

### 孤儿检测

```bash
$PKM orphan detect "$VAULT"
```

或手动：
```bash
# 找出没有 incoming links 的 permanent 笔记
find "$VAULT/Zettels/3-Permanent" -name "*.md" | while read f; do
    basename=$(basename "$f" .md)
    count=$(grep -rl "$basename" "$VAULT" --include="*.md" | grep -v "$f" | wc -l)
    if [ "$count" -eq 0 ]; then
        echo "ORPHAN: $f"
    fi
done
```

### 项目状态

```bash
for dir in "$VAULT/Efforts/1-Projects/Active"/*/; do
    name=$(basename "$dir")
    notes=$(find "$dir" -name "*.md" | wc -l | tr -d ' ')
    echo "Active: $name ($notes notes)"
done
```

## 参考文档

- `pkm-core/references/vault-structure.md` — 目录结构
- `pkm-core` — frontmatter 规范

## Changelog

### v1.1.0 (2026-03-20)
- 添加 pkm-core 依赖
- 简化重复规范说明

### v1.0.0
- 初始版本

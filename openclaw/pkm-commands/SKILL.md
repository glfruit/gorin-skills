---
name: pkm-commands
description: "PKM Telegram 命令路由器。处理 /pkm_idea、/pkm_clip、/pkm_search、/pkm_para、/pkm_health、/pkm_backup、/pkm_promote。"
triggers: ["/pkm", "/pkm_idea", "/pkm_clip", "/pkm_lit", "/pkm_search", "/pkm_para", "/pkm_health", "/pkm_backup", "/pkm_promote"]
user-invocable: true
command-dispatch: tool
---

# PKM Commands — Telegram 命令路由 v1.1

统一入口，将 /pkm_* 命令路由到对应的 skill。

## 命令路由

| 命令 | 目标 Skill | 说明 |
|------|-----------|------|
| `/pkm_idea` `想法 xxx` | `idea-creator` | 保存想法笔记 |
| `/pkm_clip` | `zk-para-zettel` | Web 摘录 → 文献笔记 |
| `/pkm_lit` | `zk-para-zettel` | 文献笔记 |
| `/pkm_search` | 直接 grep | 搜索 vault |
| `/pkm_para` | `pkm-para-manager` | PARA 管理 |
| `/pkm_health` | `pkm-para-manager` | Vault 健康检查 |
| `/pkm_backup` | 直接 tar | Vault 备份 |
| `/pkm_promote` | `zk-para-zettel` | Fleeting → Permanent |

## 搜索实现

```bash
VAULT="${HOME}/Workspace/PKM/octopus"
grep -rl "query" "$VAULT" --include="*.md" | head -20
```

## 备份实现

```bash
tar -czf ~/Desktop/octopus-backup-$(date +%Y%m%d).tar.gz \
    -C ~/Workspace/PKM octopus/
```

## 依赖

所有笔记创建命令最终依赖 `pkm-core`（通过各自的目标 skill）。

## Changelog

### v1.1.0 (2026-03-20)
- 更新命令路由表
- 添加 pkm-core 依赖说明

### v1.0.0
- 初始版本

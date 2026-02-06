# 第三方技能注册表

本文档是第三方技能库的中央注册表，这些技能库与 gorin-skills 集成或提供补充功能。

## 什么是第三方技能？

第三方技能是由社区开发的库、插件或集成，用于扩展 AI 开发工具的能力，但在本仓库之外维护。

## 如何提交

要将你的技能库添加到此注册表：

1. 确保你的技能有稳定的托管地址（GitHub 仓库、npm 包等）
2. 通过 Pull Request 提交，格式如下
3. 独立维护你的技能

## 提交格式

```yaml
name: 技能名称
category: openclaw | general | claude-code | codex | other
description: 简短描述
repository: https://github.com/user/repo
homepage: https://example.com
author: 你的名字
license: MIT | Apache-2.0 | Other
status: stable | beta | experimental
tags: [标签1, 标签2, 标签3]
integration: 如何与 gorin-skills 集成
```

## 注册表

### OpenClaw 技能

#### 社区维护

| 名称 | 描述 | 状态 | 仓库 |
|------|-------------|--------|------------|
| *(暂无提交)* | | | |

### 通用技能

#### Claude Code 扩展

| 名称 | 描述 | 状态 | 仓库 |
|------|-------------|--------|------------|
| *(暂无提交)* | | | |

#### Codex 插件

| 名称 | 描述 | 状态 | 仓库 |
|------|-------------|--------|------------|
| *(暂无提交)* | | | |

### 多工具技能

| 名称 | 描述 | 状态 | 仓库 |
|------|-------------|--------|------------|
| *(暂无提交)* | | | |

## 集成指南

### 对于技能用户

1. 查看技能的文档
2. 按照技能仓库中的说明进行安装
3. 向技能的维护者报告问题

### 对于技能作者

要使你的技能与 gorin-skills 兼容：

1. 遵循 [docs/skill-development-guide.md](./docs/skill-development-guide.md) 中的文件结构约定
2. 包含 SKILL.md 文件并填写正确的元数据
3. 提供清晰的安装说明
4. 选择合适的许可证

## 维护

此注册表会定期更新。不再维护的技能可能会被标记为已弃用。

---

最后更新：2026-02-06

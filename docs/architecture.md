# 项目架构

本文档描述 gorin-skills 项目的设计理念和架构决策。

## 概述

gorin-skills 是一个模块化的技能仓库，旨在为多种 AI 开发工具提供扩展能力。

## 设计原则

### 1. 按工具分类

技能按照目标工具类型分类存储：

- **`openclaw/`** - OpenClaw 工具的技能
- **`general/`** - 其他工具（Claude Code、Codex 等）的技能

### 2. 自包含技能

每个技能都是一个独立的单元，包含：

```
skill-name/
├── README.md        # 用户文档
├── SKILL.md         # 技能元数据（机器可读）
├── install.sh       # 安装脚本
├── LICENSE          # 许可证
└── [files]          # 技能实现文件
```

### 3. 模板驱动

使用模板确保一致性：

- **`templates/skill/`** - 通用技能模板
- **`scripts/setup-skill.sh`** - 基于模板创建新技能

### 4. 验证优先

- **`scripts/validate-skill.sh`** - 自动化验证技能结构
- GitHub Actions 集成确保 PR 质量

## 目录结构

```
gorin-skills/
├── openclaw/           # OpenClaw 技能
│   └── {skill-name}/   # 技能目录
├── general/            # 通用技能
│   └── {skill-name}/   # 技能目录
├── templates/          # 技能模板
│   └── skill/
├── scripts/            # 辅助脚本
├── docs/               # 项目文档
└── .github/            # GitHub 配置
```

## SKILL.md 格式

SKILL.md 是技能的核心元数据文件，使用 YAML frontmatter：

```yaml
---
name: skill-name
description: Brief description
homepage: https://example.com
version: 1.0.0
metadata:
  {
    "tool-type": {
      "emoji": "✨",
      "os": ["darwin", "linux"],
      "requires": { "bins": ["python3"] },
      "install": [...]
    }
  }
---
```

### 必需字段

| 字段 | 说明 |
|------|------|
| `name` | 技能名称（标识符） |
| `description` | 简短描述 |
| `homepage` | 项目主页 URL |

### 可选字段

| 字段 | 说明 |
|------|------|
| `version` | 版本号 |
| `metadata` | 工具特定的元数据 |

## 技能生命周期

### 1. 创建

```bash
./scripts/setup-skill.sh
```

### 2. 开发

编辑技能文件，实现功能

### 3. 验证

```bash
./scripts/validate-skill.sh path/to/skill
```

### 4. 提交

创建 Pull Request

### 5. 审核

自动化验证 + 人工审核

### 6. 合并

合并到主分支

## 扩展点

### 添加新的工具类别

1. 在根目录创建新的分类目录
2. 更新 `setup-skill.sh` 添加类别选项
3. 更新文档

### 添加新的模板

1. 在 `templates/` 下创建新目录
2. 实现模板文件
3. 更新 `setup-skill.sh` 支持新模板

## 集成模式

### OpenClaw 集成

OpenClaw 技能通过 SKILL.md 元数据被识别和加载：

```yaml
metadata:
  {
    "openclaw": {
      "install": [...]
    }
  }
```

### 通用工具集成

通用技能遵循相似的元数据模式，但针对不同工具定制：

```yaml
metadata:
  {
    "claude-code": {...},
    "codex": {...}
  }
```

## 依赖管理

### 技能内部依赖

- 在 SKILL.md 中声明
- 由 install.sh 处理安装

### 项目级依赖

- 最小化
- 仅用于开发和验证

## 贡献流程

```
Fork → Create Branch → Develop → Validate → PR → Review → Merge
```

## 版本控制

- 使用 Git 作为版本控制
- 遵循语义化版本（针对单个技能）
- 项目整体不使用统一版本号

# 技能开发指南

本指南将帮助你为 gorin-skills 创建新的技能。

## 前置条件

- 基本的 Shell 脚本或编程经验（Python、Node.js 等）
- 了解目标 AI 工具的基本使用
- Git 基础知识

## 快速开始

### 使用模板创建技能

```bash
# 运行交互式创建脚本
./scripts/setup-skill.sh

# 按照提示输入信息
# - 技能名称
# - 类别（openclaw/general）
# - 描述
# - 作者信息
```

### 手动创建技能

```bash
# 1. 创建目录
mkdir -p openclaw/my-skill

# 2. 复制模板
cp -r templates/skill/* openclaw/my-skill/

# 3. 替换占位符
# 编辑文件，将 {{PLACEHOLDER}} 替换为实际内容
```

## 技能结构

### 必需文件

```
my-skill/
├── README.md        # 用户文档（必需）
├── SKILL.md         # 技能元数据（必需）
└── LICENSE          # 许可证（必需）
```

### 推荐文件

```
my-skill/
├── install.sh       # 安装脚本（推荐）
├── my-skill.py      # 实现文件（取决于技能类型）
└── .gitignore       # Git 忽略规则（推荐）
```

## SKILL.md 编写

SKILL.md 是技能的核心元数据文件，包含机器可读的 YAML frontmatter 和人类可读的文档。

### 基本格式

```markdown
---
name: my-skill
description: A brief description of what this skill does
homepage: https://github.com/glfruit/gorin-skills
version: 1.0.0
metadata:
  {
    "openclaw": {
      "emoji": "✨",
      "os": ["darwin"],
      "requires": { "bins": ["python3"] },
      "install": [...]
    }
  }
---

# 技能名称

详细描述...
```

### 元数据字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 技能唯一标识符 |
| `description` | string | 是 | 简短描述 |
| `homepage` | string | 是 | 项目主页 URL |
| `version` | string | 否 | 语义化版本号 |
| `metadata` | object | 否 | 工具特定配置 |

### 工具特定元数据

#### OpenClaw

```yaml
metadata:
  {
    "openclaw": {
      "emoji": "🐻",
      "os": ["darwin"],
      "requires": { "bins": ["python3", "node"] },
      "install": [
        {
          "id": "my-skill-cli",
          "kind": "download",
          "url": "https://raw.githubusercontent.com/...",
          "extract": false,
          "targetDir": "~/.local/bin",
          "bins": ["my-skill.py"],
          "label": "Install My Skill CLI"
        }
      ]
    }
  }
```

#### Claude Code / General

```yaml
metadata:
  {
    "claude-code": {
      "emoji": "🤖",
      "os": ["darwin", "linux", "win32"],
      "requires": { "npm": ["openai"] },
      "install": [...]
    }
  }
```

## README.md 编写

README.md 是用户首先看到的文档，应该清晰、完整。

### 推荐结构

```markdown
# 技能名称

简短描述

## 简介
详细描述技能的功能和用途

## 功能特性
- 特性 1
- 特性 2

## 系统要求
- 要求 1
- 要求 2

## 安装
### 自动安装
...

### 手动安装
...

## 使用
### 示例 1
...

### 示例 2
...

## 配置
...

## 故障排除
...

## 许可证
...
```

## install.sh 编写

安装脚本负责将技能安装到用户系统中。

### 基本结构

```bash
#!/bin/bash
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# 函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# 检查前置条件
check_prerequisites() {
    ...
}

# 安装文件
install_files() {
    ...
}

# 主函数
main() {
    check_prerequisites
    install_files
    log_info "安装完成！"
}

main "$@"
```

### 最佳实践

1. **错误处理**：使用 `set -e` 确保脚本在错误时退出
2. **用户反馈**：提供清晰的进度信息
3. **权限检查**：检查必要的目录权限
4. **清理**：失败时清理部分安装的文件

## 技能实现

### Python 技能

```python
#!/usr/bin/env python3
import argparse

def main():
    parser = argparse.ArgumentParser(description="技能描述")
    parser.add_argument('--version', action='version', version='1.0.0')
    args = parser.parse_args()
    # 实现逻辑

if __name__ == '__main__':
    main()
```

### Shell 脚本技能

```bash
#!/bin/bash
set -e

# 解析参数
ACTION="$1"
shift

case "$ACTION" in
    install)
        # 安装逻辑
        ;;
    run)
        # 运行逻辑
        ;;
    *)
        echo "用法: $0 {install|run}"
        exit 1
        ;;
esac
```

## 验证

创建技能后，使用验证脚本检查：

```bash
./scripts/validate-skill.sh openclaw/my-skill
```

### 检查项

- [ ] 必需文件存在（README.md, SKILL.md, LICENSE）
- [ ] SKILL.md 有有效的 YAML frontmatter
- [ ] 必需字段完整
- [ ] install.sh 有执行权限
- [ ] 无模板占位符残留

## 测试

### 本地测试

1. **功能测试**
   ```bash
   # 运行技能
   ./my-skill/my-skill.py --help
   ```

2. **安装测试**
   ```bash
   cd my-skill
   ./install.sh
   ```

3. **集成测试**
   - 在目标 AI 工具中测试
   - 验证所有文档中的示例

## 发布

### 准备发布清单

- [ ] 所有功能已测试
- [ ] 文档完整
- [ ] 通过验证脚本
- [ ] LICENSE 文件正确
- [ ] 无敏感信息

### 提交 PR

1. 创建功能分支
2. 推送到你的 fork
3. 创建 Pull Request
4. 填写 PR 模板

### PR 描述模板

```markdown
## 技能名称
my-skill

## 描述
简短描述技能功能

## 类别
- [ ] openclaw
- [ ] general

## 测试
- [ ] 本地测试通过
- [ ] 验证脚本通过
- [ ] 在目标工具中测试

## 文档
- [ ] README.md 完整
- [ ] SKILL.md 元数据正确
```

## 最佳实践

### 代码风格

- 使用清晰的命名
- 添加注释解释复杂逻辑
- 保持函数简短和专注
- 遵循目标语言的惯例

### 错误处理

- 提供有用的错误消息
- 优雅地处理失败情况
- 记录错误以供调试

### 文档

- 从用户角度编写
- 包含完整的示例
- 说明前置条件
- 提供故障排除指南

### 安全

- 不硬编码敏感信息
- 验证用户输入
- 使用安全的默认设置
- 清晰说明权限要求

## 资源

- [项目架构](./architecture.md)
- [第三方技能](./third-party-skills.md)
- [贡献指南](../CONTRIBUTING.md)

## 获取帮助

- 提交 Issue
- 查看 [THIRD_PARTY_SKILLS.md](../THIRD_PARTY_SKILLS.md) 中的示例
- 联系维护者

# 第三方技能指南

本文档介绍如何使用和集成第三方技能库。

## 什么是第三方技能？

第三方技能是由社区独立开发和维护的技能库，它们：

- 托管在 gorin-skills 仓库之外
- 由原作者维护
- 提供额外的功能和集成

## 使用第三方技能

### 查找技能

浏览 [THIRD_PARTY_SKILLS.md](../THIRD_PARTY_SKILLS.md) 注册表，查找你需要的技能。

### 安装步骤

1. **阅读文档**
   - 访问技能的仓库主页
   - 阅读安装说明
   - 检查系统要求

2. **安装技能**
   ```bash
   # 按照技能仓库的说明进行安装
   # 通常包括：
   git clone https://github.com/user/skill-repo.git
   cd skill-repo
   ./install.sh
   ```

3. **配置技能**
   - 按照文档设置配置文件
   - 设置必需的环境变量
   - 配置 API 密钥（如需要）

4. **测试技能**
   - 运行技能的测试命令
   - 在目标 AI 工具中验证

### 安全注意事项

安装第三方技能前，请注意：

- [ ] 检查技能仓库是否活跃维护
- [ ] 查看最近的提交活动
- [ ] 阅读 ISSUE 和 PR 了解社区反馈
- [ ] 检查 LICENSE 确保符合你的使用场景
- [ ] 审查 install.sh 脚本内容
- [ ] 注意技能要求的权限

## 创建第三方技能

### 项目结构建议

遵循 gorin-skills 的结构约定：

```
your-skill/
├── README.md        # 用户文档
├── SKILL.md         # 技能元数据
├── install.sh       # 安装脚本
├── LICENSE          # 许可证
└── src/             # 源代码
```

### SKILL.md 兼容性

确保你的 SKILL.md 包含正确的元数据：

```yaml
---
name: your-skill
description: Your skill description
homepage: https://github.com/yourusername/your-skill
version: 1.0.0
metadata:
  {
    "openclaw": {
      "emoji": "✨",
      "os": ["darwin"],
      "requires": { "bins": ["python3"] }
    }
  }
---
```

### 提交到注册表

1. **确保技能稳定**
   - 经过测试
   - 有完整文档
   - 有清晰的 LICENSE

2. **Fork gorin-skills**
   ```bash
   git clone https://github.com/glfruit/gorin-skills.git
   cd gorin-skills
   ```

3. **更新 THIRD_PARTY_SKILLS.md**
   - 按照格式添加你的技能信息
   - 包含所有必需字段

4. **提交 PR**
   - 说明技能的功能
   - 提供测试结果
   - 等待审核

## 集成模式

### 与 OpenClaw 集成

```yaml
metadata:
  {
    "openclaw": {
      "install": [
        {
          "id": "your-skill",
          "kind": "git",
          "url": "https://github.com/yourusername/your-skill.git",
          "targetDir": "~/.openclaw/skills/your-skill"
        }
      ]
    }
  }
```

### 与 Claude Code 集成

```yaml
metadata:
  {
    "claude-code": {
      "install": [
        {
          "id": "your-skill",
          "kind": "npm",
          "package": "@yourusername/your-skill"
        }
      ]
    }
  }
```

## 维护建议

### 保持技能更新

- 定期发布新版本
- 及时修复 bug
- 响应用户问题
- 更新文档

### 版本管理

- 遵循语义化版本
- 使用 Git 标签标记版本
- 在 SKILL.md 中更新版本号

### 依赖管理

- 明确声明依赖
- 锁定依赖版本
- 提供依赖安装说明

### 文档维护

- 保持文档与代码同步
- 添加使用示例
- 记录变更历史

## 退出维护

如果你无法继续维护技能：

1. 在 README 中添加「寻找维护者」声明
2. 通知 gorin-skills 维护团队
3. 考虑转移仓库给新维护者
4. 在注册表中标记状态

## 示例

### 示例 1：Python 技能

```bash
# my-skill/
├── README.md
├── SKILL.md
├── install.sh
├── my_skill.py
└── requirements.txt
```

### 示例 2：Node.js 技能

```bash
# my-skill/
├── README.md
├── SKILL.md
├── install.sh
├── package.json
├── lib/
│   └── index.js
└── bin/
    └── my-skill
```

### 示例 3：Shell 脚本技能

```bash
# my-skill/
├── README.md
├── SKILL.md
├── install.sh
└── my-skill.sh
```

## 资源

- [技能开发指南](./skill-development-guide.md)
- [项目架构](./architecture.md)
- [第三方技能注册表](../THIRD_PARTY_SKILLS.md)

## 获取帮助

- 提交 Issue 到 gorin-skills
- 在技能仓库中提问
- 加入社区讨论

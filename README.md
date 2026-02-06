# gorin-skills

[![License: MIT](https://img.shshield.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/glfruit/gorin-skills)](https://github.com/glfruit/gorin-skills)

> 为 AI 开发工具构建的技能集合

## 简介

gorin-skills 是一个精心策划的仓库，用于扩展 AI 开发工具的能力。技能按用途分为两大类：

- **OpenClaw 技能** (`openclaw/`) - 为 OpenClaw AI 工具开发的集成
- **通用技能** (`general/`) - 为 Claude Code、Codex 等其他 AI 工具开发的技能

## 快速开始

### 使用现有技能

1. 浏览技能目录，找到你需要的技能
2. 查看技能目录中的 `README.md` 了解安装说明
3. 按照说明完成安装
4. 重启你的 AI 工具

### 创建新技能

1. 使用模板脚本：`./scripts/setup-skill.sh`
2. 根据需要自定义技能文件
3. 本地测试
4. 提交 Pull Request

## 目录结构

```
gorin-skills/
├── openclaw/           # OpenClaw 技能
│   └── neobear/        # Bear 笔记集成
└── general/            # 其他工具的技能
```

## 精选技能

### OpenClaw

- [neobear](./openclaw/neobear/) - 下一代 Bear 笔记集成，完美处理 URL 编码

### 第三方技能

查看 [THIRD_PARTY_SKILLS.md](./THIRD_PARTY_SKILLS.md) 了解外部技能库的注册表。

## 贡献

我们欢迎各种形式的贡献！请参阅 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解贡献指南。

## 文档

- [项目架构](./docs/architecture.md) - 项目结构和设计理念
- [技能开发指南](./docs/skill-development-guide.md) - 如何创建技能
- [第三方技能](./docs/third-party-skills.md) - 使用外部技能

## 许可证

MIT License - 详见 [LICENSE](./LICENSE)

---

由社区贡献，服务于 AI 开发生态系统

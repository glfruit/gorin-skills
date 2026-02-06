# 贡献指南

感谢你对 gorin-skills 项目的关注！本文档提供了参与项目贡献的指南。

## 行为准则

- 互相尊重和包容
- 提供建设性的反馈
- 以社区利益为重
- 对其他社区成员保持同理心

## 如何贡献

### 贡献方式

- 提交新技能
- 改进现有技能
- 修复 Bug
- 改进文档
- 报告问题
- 审查 Pull Request

### 技能分类

提交贡献时，请说明你的技能属于哪个类别：

- **openclaw/** - OpenClaw 工具的技能
- **general/** - Claude Code、Codex 等其他工具的技能

## 技能提交流程

### 1. 使用模板创建技能

```bash
./scripts/setup-skill.sh
```

按照提示输入技能名称和类别。

### 2. 技能文件要求

每个技能必须包含：

- `README.md` - 用户文档
- `SKILL.md` - 技能元数据（包含 YAML frontmatter）
- `LICENSE` - 许可证文件（推荐使用 MIT）
- `install.sh` - 安装脚本（可选但推荐）

### 3. 验证技能

```bash
./scripts/validate-skill.sh path/to/skill
```

### 4. 提交 Pull Request

创建 PR 时请包含：

- 技能描述
- 安装说明
- 使用示例
- 测试情况

## 开发工作流

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/your-skill-name`
3. 进行更改
4. 运行验证脚本
5. 提交更改：`git commit -m "Add: description of your skill"`
6. 推送到你的 fork：`git push origin feature/your-skill-name`
7. 创建 Pull Request

## 编码标准

### 通用规范

- 使用清晰、描述性的名称
- 为复杂逻辑添加注释
- 遵循现有代码风格
- 保持文件简洁和模块化

### 文档要求

- 编写清晰、简洁的文档
- 包含使用示例
- 记录前置条件
- 提供故障排除指南

## 测试要求

提交前请确保：

1. 安装脚本可以正常工作
2. 所有文档中的功能都已测试
3. 在目标平台上测试通过
4. 运行验证脚本无错误

## Pull Request 审查流程

1. 确保代码通过验证
2. 更新相关文档
3. 引用相关 Issue
4. 使用 PR 模板
5. 响应审查反馈

---

感谢你为 gorin-skills 做出的贡献！

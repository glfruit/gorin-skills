---
type: tool-wrapper
updated: 2026-03-25
based_on: obsidian-search, apple-notes, apple-reminders, send-email, tmux
---

# Tool Wrapper 创建经验

## 核心模式

**双层输出是标配**，不是可选项：
- JSON 给 agent / 程序化消费者
- 人类可读文本给用户
- 用一个 `--json` flag 或输出格式参数切换

**配置必须外部化**：
- 用 `~/.openclaw/config.env` 或 SKILL.md 里的环境变量
- 绝不硬编码路径（`/Users/gorin/...`）
- 用 `$HOME`、`Path.home()`、或配置变量
- 工具可能不存在——`command -v` 检查后再调用

## 输入验证

- 输入先验证，再处理。不要假设格式正确
- 文件路径：检查存在性 + 可读性
- skill name：`^[a-z0-9-]+$` 正则校验
- URL：`urlparse` 解析后再用

## Shell 安全

- 所有变量必须双引号：`"$var"` 而不是 `$var`
- `grep`/`rg` 用固定字符串匹配时加 `-F`
- 不直接拼接用户输入到 shell 命令

## 常见陷阱

| 陷阱 | 表现 | 解决 |
|------|------|------|
| 工具未安装 | 技能静默失败 | `command -v` + 友好错误提示 + 安装指令 |
| 路径假设 | 在其他机器上 break | 用配置变量或 `$HOME` |
| 输出格式不分 | agent 读不了 | JSON/text 双输出 |
| 单一错误路径 | 不同错误返回相同 exit code | 区分 exit code 1/2/3 或 JSON error 字段 |

---
type: monitor-cron
updated: 2026-03-25
based_on: cron-scheduling, healthcheck, blogwatcher, invest-alerts
---

# Monitor/Cron 创建经验

## 核心模式

**launchd 优先于 cron**：
- macOS 上 launchd 处理 sleep/wake 更好
- 环境隔离更干净
- 但 launchd plist 格式繁琐——用 Python 脚本生成

**检查逻辑 vs 通知逻辑分离**：
- 检查脚本：纯逻辑，输出结构化结果（JSON 或 exit code）
- 通知脚本：读结果，格式化，发送
- 不要在检查脚本里混杂通知代码

**静默 vs 告警**：
- 正常状态：静默（不产生输出 = 没问题）
- 异常状态：明确告警（什么异常 + 严重程度 + 建议操作）
- 不要每次 cron 都发一条"一切正常"

## 定时策略

| 场景 | 推荐 | 原因 |
|------|------|------|
| 固定时间执行 | launchd plist StartCalendarInterval | 精确 |
| 周期性检查 | OpenClaw cron (every) | 管理方便 |
| 需要交互 | cron isolated session | agent 可用工具 |
| 需要主 session | cron main session (systemEvent) | 轻量提醒 |

## 常见陷阱

| 陷阱 | 表现 | 解决 |
|------|------|------|
| 无限告警 | 同一个问题反复通知 | 去重/冷却期/状态文件 |
| 环境变量缺失 | cron 里跑脚本缺 PATH | launchd plist 设 EnvironmentVariables |
| 时区错误 | 定时时间不对 | plist 里 TZ=Asia/Shanghai |
| 资源泄漏 | 检查脚本不退出 | timeout 命令包裹 |
| 日志膨胀 | 无清理 | launchd StandardErrorPath + logrotate |

## 验证清单

- [ ] 正常状态不产生噪音
- [ ] 异常状态有明确输出
- [ ] 告警有去重/冷却机制
- [ ] 脚本有 timeout 兜底

---
name: log-watchdog
description: "Gateway 错误日志增量扫描器。只报真正需要关注的问题，安静时不出声。"
triggers:
  - log watchdog
  - check logs
  - scan errors
  - log monitor
---

# Log Watchdog

Gateway 错误日志增量扫描器。安静时零输出。

## 运行方式

- 由 monitor heartbeat 调用：`python3.13 scripts/log_watchdog.py`
- Shell 包装：`bash scripts/log-watchdog.sh`

## 核心变更（v2）

| 旧版问题 | v2 方案 |
|----------|---------|
| 报已解决的旧错误 | 持久化 pos + hash 去重，pos 丢失只看最近 2000 行 |
| 定时 digest 刷屏 | 取消定时 digest，只在实际发现新错误时记日志 |
| WebSocket 500 也报 | 噪音过滤：Skipping skill + WebSocket fallback 直接跳过 |
| sendChatAction 429 也报 | 只报 sendMessage 429，typing indicator 不报 |
| 状态文件在 /tmp 重启丢失 | 移到 ~/.openclaw/logs/ |
| Python 3.9 类型兼容 | 使用 python3.13 |

## 告警分级

| 错误 | 级别 | 行为 | 冷却 |
|------|------|------|------|
| uncaughtException / FATAL | P0 | 即时通知 + 样本 | 30min |
| FailoverError（非 401）| P0 | 即时通知 + agent 名 + 时长 | 30min |
| auth 401 ≥ 3 次 | P1 | 自动修复 + 通知 | 30min |
| sendMessage 429 | P2 | 仅记日志 | — |
| ETIMEDOUT / ENOENT | P3 | 仅记日志 | — |

## 状态文件

- `~/.openclaw/logs/log-watchdog-pos` — 扫描位置
- `~/.openclaw/logs/log-watchdog-state.json` — 冷却 + hash 去重

## 职责分界

- log-watchdog: 错误检测 + auth 修复 + P0/P1 告警
- gateway-watchdog: 进程健康 + 重启恢复
- config-sentinel: 配置完整性 + 回滚

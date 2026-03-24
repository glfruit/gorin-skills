---
type: api-integration
updated: 2026-03-25
based_on: send-email, baoyu-image-gen, download-anything, openmaic
---

# API Integration 创建经验

## 核心模式

**API 密钥永远不放代码里**：
- `~/.openclaw/openclaw.json` 的 `skills.entries.<name>.env` 段
- 或 `~/.openclaw/config.env`
- SKILL.md 只引用变量名（`$API_KEY`），不写值

**Retry + 降级是必须的**：
- 网络请求必 retry（3次，指数退避）
- 超时必设置（不要无限等）
- 有备选方案时自动降级（主 API 挂了 → 备选 API）

**Payload 格式要写死**：
- API 的请求体格式写在 SKILL.md 或 references/ 里
- 不要让 agent "猜测" JSON 结构——直接给示例
- 响应格式也一样，给 agent 示例输出方便解析

## 认证模式

| 模式 | 适用场景 | 注意点 |
|------|---------|--------|
| API Key (header) | REST API | `Authorization: Bearer $KEY` |
| API Key (query param) | 简单 API | 注意 URL 编码 |
| OAuth | 需要 refresh token | token 过期后自动刷新 |
| Cookie | 需要浏览器登录态 | 用 browser 工具 profile=user |

## 常见陷阱

| 陷阱 | 表现 | 解决 |
|------|------|------|
| 没有超时 | agent 卡死 | 所有请求设 `timeout` |
| 没有重试 | 瞬时失败 = 永久失败 | 指数退避 retry |
| 密钥泄露 | 代码里有明文 key | 环境变量 + .gitignore |
| API 变更 | 技能突然不工作 | SKILL.md 记录 API 版本 |
| 速率限制 | 429 错误 | 检测 429 + Retry-After header |
| 响应格式变化 | 解析崩溃 | 先验证 JSON 结构再提取字段 |

## 验证清单

- [ ] 密钥只在环境变量里
- [ ] 所有请求有超时
- [ ] 有 retry 逻辑
- [ ] 429/5xx 有降级处理
- [ ] 请求/响应格式有文档示例

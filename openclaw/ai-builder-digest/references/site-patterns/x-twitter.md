---
domain: x.com
aliases: [twitter.com, X, Twitter]
updated: 2026-03-26
---

## 平台特征
- SPA 架构，JS 渲染，L1 (defuddle/Scrapling) 只能拿到空壳
- 需要登录态才能看到完整时间线
- 反爬：频繁请求会返回 403 或空内容
- 公开推文可通过 Nitter 或搜索获取

## 有效模式
1. **PinchTab L2 + x-twitter profile**：web_reader 默认路由，需要预先登录
2. **web_search 备选**：`web_search "{handle} site:x.com"` 可发现最近推文，然后用 web_fetch 抓取具体推文
3. **Nitter 实例**：`web_reader https://nitter.net/{handle}`，但实例不稳定，经常换域名

## 已知陷阱
- Nitter 公共实例（nitter.net 等）经常被封或宕机，不要依赖单一实例
- PinchTab cookie 过期后 L2 返回登录页而非错误，需要检查返回内容是否包含 "login" 或 "sign in"
- X 的搜索 API 需要登录，web_search 工具走的是搜索引擎而非 X 内部搜索
- rate limit：同 IP 短时间请求太多 X 页面会被临时封禁（通常 15 分钟）

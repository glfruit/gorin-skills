---
domain: mp.weixin.qq.com
aliases: [微信公众号, WeChat MP, 微信]
updated: 2026-03-26
---

## 平台特征
- 大部分文章是静态 HTML，不需要登录即可阅读
- 部分（尤其是较新的）文章可能有 JS 动态加载
- 没有稳定 RSS 源（第三方 RSS 服务经常失效）
- 文章 URL 格式：`https://mp.weixin.qq.com/s/xxxxx`

## 有效模式
1. **web_reader L1 (Scrapling)**：默认路由，对大部分文章有效
2. **搜索引擎发现**：`web_search "{公众号名} site:mp.weixin.qq.com"` 发现最新文章 URL
3. **web_fetch 直接抓**：对简单文章可用 `web_fetch` 工具直接获取

## 已知陷阱
- 微信文章 URL 不含标题信息，无法从 URL 判断内容
- 同一篇文章可能有多个 URL（短链重定向）
- 部分文章有阅读量限制（需关注公众号后才能阅读全文），这种情况 L1 和 L2 都无法获取完整内容
- 文章中的图片可能是懒加载的，Scrapling 可能获取不到
- `mp.weixin.qq.com/s/` 短链会 302 重定向到长 URL，web_fetch 能自动跟随

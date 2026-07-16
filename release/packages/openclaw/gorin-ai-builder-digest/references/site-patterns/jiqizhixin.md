---
domain: jiqizhixin.com
aliases: [机器之心, jiqizhixin]
updated: 2026-03-26
---

## 平台特征
- 主站 (jiqizhixin.com) 大部分文章在 PRO 付费墙后，L1 Scrapling 只能抓到标题和 teasers
- 部分文章同步发布到微信公众号 (mp.weixin.qq.com)，但需要正确的 __biz/mid/idx/sn 参数
- 36kr 有机器之心的官方转载页，文章完整可读

## 有效模式
1. **36kr 转载页（推荐）**: `https://m.36kr.com/user/214166`
   - web_reader L1 defuddle 即可抓取，获取文章列表和链接
   - 具体文章链接格式：`https://m.36kr.com/p/{id}`
   - 正文完整（3000+ 字），含图片
2. **搜索引擎发现**: 搜索 "机器之心 {关键词}" 找到转载链接

## 抓取流程
1. web_reader 打开 `https://m.36kr.com/user/214166`，获取文章列表（标题 + /p/xxx 链接）
2. 选择最新/最相关的 1 篇文章
3. web_reader 抓取 `https://m.36kr.com/p/{id}` 正文
4. ⚠️ 两次 36kr 请求之间间隔 ≥ 30s，避免触发 WAF

## 已知陷阱
- 不要直接抓 jiqizhixin.com 主站文章 URL，会命中付费墙
- 不要用 `机器之心 site:mp.weixin.qq.com` 搜索，Tavily 搜索引擎返回 0 结果
- jigou.jiqizhixin.com（PRO 会员专区）同样付费
- 36kr 有 WAF（JavaScript challenge），短时间内重复请求（< 30s）会被拦截，表现为 L1/L2 均返回空内容
- 不要连续抓取 36kr 多篇文章，每天 digest 取 1 篇即可
- web_fetch 工具对 m.36kr.com 直接拦截（报 "resolves to private/internal IP"），必须走 web_reader

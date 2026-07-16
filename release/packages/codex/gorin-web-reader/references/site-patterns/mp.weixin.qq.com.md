---
domain: mp.weixin.qq.com
aliases: [微信公众号, WeChat]
updated: 2026-03-25
---
## 平台特征
- 大部分文章公开可读，无需登录
- Jina Reader 对此域名返回 403，不可用
- 部分较新文章可能需要浏览器渲染

## 有效模式
- L1 Scrapling 作为首选（python3 fetch.py）
- web_fetch 工具有时也能获取，但不稳定
- 如果 L1 获取内容过短或不完整，升级到 L2 浏览器渲染

## 已知陷阱
- Jina Reader 永远失败（403），不要尝试
- 文章中的图片通常以 CDN 链接形式存在，可直接提取
- 部分付费/加密文章无法获取，会返回登录墙或付费提示

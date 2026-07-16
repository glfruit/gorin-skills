---
domain: zhihu.com
aliases: [知乎]
updated: 2026-03-25
---
## 平台特征
- SPA 架构，静态抓取只能拿到空壳
- 需登录才能看完整回答和评论
- 反爬检测严格，headless 模式容易被拦截

## 有效模式
- 必须走 L2 浏览器渲染（PinchTab profile=zhihu，headless=false）
- 使用用户 Chrome 登录态（browser 工具 profile=user）也是可靠方案
- `zhuanlan.zhihu.com` 文章页可用 defuddle 部分提取，但完整内容仍需浏览器

## 已知陷阱
- defuddle/Scrapling 返回的内容通常只有问题标题，回答内容为空
- headless Chrome 会被知乎检测并返回验证码页面
- 带登录态的浏览器才能获取完整内容

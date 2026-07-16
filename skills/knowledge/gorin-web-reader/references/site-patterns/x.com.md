---
domain: x.com
aliases: [twitter.com, 推特, X]
updated: 2026-03-25
---
## 平台特征
- SPA 架构，推文内容通过 JS 动态加载
- 需登录才能查看完整推文和回复
- 推文 DOM 结构：`[data-testid="tweetText"]`，用户名：`[data-testid="User-Name"]`，时间：`time[datetime]`

## 有效模式
- PinchTab L2 专用提取路径：等待 `[data-testid="tweetText"]` 渲染后用 eval 提取
- defuddle 对 X SPA 的 HTML 清洗效果差，推文内容会丢失
- browser 工具的 snapshot 可以获取渲染后的推文文本
- 多条推文/回复：所有 `tweetText` 元素按顺序排列

## 已知陷阱
- 导航后需额外等待 2-8 秒才能获取渲染完的推文
- 推文中的图片/视频需要从 DOM 单独提取 URL
- URL 状态（如 deleted/suspended）可能不反映真实情况，可能是反爬触发

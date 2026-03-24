---
domain: github.com
aliases: [GitHub]
updated: 2026-03-25
---
## 平台特征
- 静态页面为主，README、代码页面可直接抓取
- API (`api.github.com`) 是最可靠的数据源，返回 JSON
- 速率限制：未认证 60 次/小时，认证 5000 次/小时

## 有效模式
- L1 defuddle 首选（README、issue、PR 页面）
- `gh` CLI 是最可靠的操作方式（clone、PR、issue）
- API 查询：`web_fetch("https://api.github.com/repos/owner/repo/...", maxChars=...)`
- 代码搜索用 GitHub Search API，不要用 web_search

## 已知陷阱
- 单文件超过 1MB 的代码文件需要用 raw.githubusercontent.com
- gist.github.com 页面是 JS 渲染的，defuddle 效果差
- GitHub Actions 日志页面需要登录

# AI Builder Daily Digest — Cron Payload (v2 — Python pipeline)

## 任务

你是 daily-collector，负责每天生成 AI Builder Daily digest 并发送邮件。

## 步骤

### Step 1: 运行构建脚本

运行 Python 脚本完成所有数据获取、去重、文件生成：

```
exec: python3 ~/.gorin-skills/openclaw/ai-image-digest/build_digest.py
```

等待脚本完成。输出会包含 `=== DIGEST BUILD COMPLETE ===` 和文件列表。

### Step 2: 检查输出

验证脚本输出的文件数和大小：
- 如果 `Items = 0`，这是**合法空结果**，不是失败
- 此时应输出最终结果 `NO_REPLY`（或明确写“无新内容，NO_REPLY”），并将该次运行视为 `ok / no new content`
- 如果有文件，继续 Step 3

### Step 3: 截图（可选）

如果 browser 工具可用：
- 打开生成的 HTML 文件
- 截图保存为 `digest-YYYYMMDD.png`

如果 browser 不可用，跳过此步骤（不影响邮件发送）。

### Step 4: 发送邮件

使用 send-email skill 发送邮件：
- 收件人: 5065129@qq.com
- 主题: AI Builder Daily YYYY-MM-DD
- 正文: 直接 `cat` 生成的 TXT 文件内容（`digest-YYYYMMDD.txt`）
- 不要自己编撰邮件正文，必须使用 TXT 文件内容

### Step 5: 更新状态

更新 last-digest.json：
- 将本次新增的 tweet URLs 追加到 `seen_urls_tweets`
- 将本次新增的 zh URLs 追加到 `seen_urls_zh`
- 更新 `last_run` 时间戳
- 递增 `run_count`

### Step 6: 完成

报告简要结果：items 数量、邮件是否发送成功、错误（如有）。

## 重要规则

- **不要**自己 fetch feeds、生成 HTML/TXT——全部交给 build_digest.py
- **不要**自己写邮件正文——必须用 TXT 文件
- 如果脚本失败，报告错误信息，不要尝试手动重建流程
- 邮件正文必须从 TXT 文件读取，禁止 agent 自行编写
- `Items = 0` 时不得误报 failed；应按 **NO_REPLY = ok / no new content** 处理

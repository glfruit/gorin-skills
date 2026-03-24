---
name: voice-to-zettel
description: "语音消息转写为 Zettel 笔记，自动关系发现。"
triggers: ["voice", "语音", "audio"]
user-invocable: false
command-dispatch: tool
agent-usable: true
requires:
  skills: [pkm-core]
---

# Voice-to-Zettel — 语音转笔记 v1.1

接收语音消息 → 转写 → 创建 Zettel 笔记 → 自动关联。

**前置依赖**: `pkm-core`

## 流程

### 1. 转写语音

使用 OpenAI Whisper CLI：
```bash
whisper "$audio_file" --language zh --model turbo --output_format txt
```

### 2. 创建笔记

使用 PKM Core（同 `pkm-save-note` 流程）：
```bash
PKM="${HOME}/.openclaw/pkm/pkm"
VAULT="${HOME}/Workspace/PKM/octopus"

# 分类 → 通常为 idea 或 zettel
classification=$($PKM classify classify "$transcript" "" "" "")
location=$(echo "$classification" | jq -r '.location')

# 去重
$PKM dedup check "$title" "$transcript"

# 关系发现
$PKM relation batch "$transcript" ""

# 渲染 + 保存
note=$($PKM template render "$detected_type" "$vars")
echo "$note" > "$VAULT/$location/$($PKM vault generate-filename "$title")"
```

### 3. Frontmatter 合规

遵守 `pkm-core` 硬性规则。

## 输出

保存后通知用户：
- 笔记标题和位置
- 发现的关联笔记数
- 如有转写质量问题，提示用户

## 隐私

语音转写在本地完成，不发送到外部 API（Whisper 本地模型）。

## Changelog

### v1.1.0 (2026-03-20)
- 添加 pkm-core 依赖
- 简化重复规范说明

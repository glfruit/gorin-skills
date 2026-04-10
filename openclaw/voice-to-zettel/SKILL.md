---
name: voice-to-zettel
description: "轻量语音笔记编排。把语音/音频先交给 openai-whisper 转写，再按 pkm-core 规范整理，并通过 pkm-save-note 落库。不要恢复旧的独立厚脚本实现。"
triggers: []
user-invocable: false
command-dispatch: tool
agent-usable: true
requires:
  skills: [openai-whisper, pkm-core, pkm-save-note]
  used-by: [daily-reader]
---

# Voice to Zettel

把语音消息转换成可保存的 PKM 笔记，但只做**轻量编排**，不自带旧式独立转写/入库脚本。

## 适用场景

- 用户发送语音消息、播客片段、录音备忘
- daily-reader 需要把阅读感想语音沉淀为笔记
- 已经拿到本地音频文件路径，或上游已把语音附件下载到本地

## 不做的事

- 不重新实现 Whisper 转写引擎
- 不维护独立虚拟环境、常驻服务或厚 shell 管线
- 不绕开 `pkm-core` 与 `pkm-save-note` 直接写 vault

## 依赖关系

1. `openai-whisper` 负责本地转写
2. `pkm-core` 提供 vault、frontmatter、命名规则
3. `pkm-save-note` 负责最终保存

## 编排步骤

### 1. 转写音频

优先直接调用 `openai-whisper` skill，使用本地 `whisper` CLI。

参考命令：

```bash
whisper /path/to/audio.m4a --model turbo --output_format txt --output_dir /tmp/voice-to-zettel
```

如果用户要更高精度，可升级到 `--model medium`；默认先用 `turbo` 做最小闭环。

### 2. 清洗转写结果

将转写文本整理为适合笔记保存的结构：
- 去掉明显口头禅、纯语气词、重复片段
- 保留阅读对象、核心观点、个人判断
- 若内容很短且像临时想法，按 `fleeting` 处理
- 若内容已形成观点或结论，优先按 `insight` 或 `summary` 处理

### 3. 交给 PKM 保存

调用 `pkm-save-note`，并遵守 `pkm-core` 规范：
- 自动或显式确定 `type`
- 需要时补 `title`、`tags`、`source`
- 默认保存到 PKM 规范目录，不直接手写路径

### 4. 返回结果

至少回传：
- 是否转写成功
- 笔记类型
- 保存位置或标题
- 若有歧义，需要用户补充哪本书/哪篇文章

## daily-reader 使用约定

当 daily-reader 收到语音类阅读输入时，按下面顺序处理：
1. 确认语音对应的书/文章/主题（若上下文足够可直接推断）
2. 调用 `voice-to-zettel` 完成转写与整理
3. 再由 `pkm-save-note` 落成笔记，必要时补上 `book`、`related` 等上下文

## 最小实现原则

- 这个 skill 以说明性编排为主，允许上游 agent 直接串联已有 skills
- 如需兼容入口，只保留薄包装，不新增厚实现
- 新增自动化前，先证明现有三段式链路不够用

## 最小验证

满足以下条件即可认为 scaffold 就绪：
- `voice-to-zettel/SKILL.md` 可被发现并可读
- `openclaw.json` 不再保留失效的旧 entry
- daily-reader 文档改为引用轻量编排，而不是旧实现真源

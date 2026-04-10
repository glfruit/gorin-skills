---
name: neobear
description: "Next-gen Bear notes integration with perfect URL encoding. Create, search, and manage Bear notes. Do NOT use for Bear Blog publishing (use bearclaw-native) or non-Bear apps."
homepage: https://bear.app
metadata:
  {
    "openclaw":
      {
        "emoji": "🐻💫",
        "os": ["darwin"],
        "requires": { "bins": ["python3"] },
        "install":
          [
            {
              "id": "neobear-cli",
              "kind": "download",
              "url": "https://raw.githubusercontent.com/glfruit/neobear/main/neobear_cli.py",
              "extract": false,
              "targetDir": "~/.local/bin",
              "bins": ["neobear_cli.py"],
              "label": "Install neobear_cli.py (Python script)",
            },
          ],
      },
  }
---


# 🐻💫 NeoBear - Next-Gen Bear Notes Integration

**Where old Bear links become new again.**

NeoBear is a modern Bear notes integration that properly handles URL encoding. Uses correct percent-encoding (`%20` for spaces) instead of plus-encoding (`+`), preventing the "spaces become plus signs" bug.

## Key Features

- ✅ **Perfect Encoding** — Uses `%20` not `+` for spaces
- ✅ **Modern Code** — Python 3.7+ best practices
- ✅ **Smart Validation** — Catches errors before they happen
- ✅ **Rich Output** — JSON support for automation
- ✅ **Better UX** — Clear feedback, helpful errors

## Usage in OpenClaw

### Create Notes

```
Create a Bear note titled "Meeting Notes" with content "Discussed project timeline"
Create a Bear note from the file `<path>` with title "Monthly Report"
```

With tags:
```
Create a Bear note:
- Title: "Project Ideas"
- Content: "New feature brainstorming"
- Tags: work, projects, 2026
```

### Search Notes

```
Search Bear notes for "project"
Find all Bear notes tagged with "work"
Search Bear for "meeting" and show only titles
```

### Open/Manage Notes

```
Open the Bear note titled "Daily Journal"
Append "Update: Project completed" to Bear note "Project Status"
Archive the Bear note "Old Ideas"
Delete the Bear note "Temporary Note"
```

## CLI Quick Reference

```bash
neobear_cli.py create --title "Note" --text "Content" [--tags work] [--pin] [--timestamp]
neobear_cli.py search --query "project" [--tag work] [--json] [--titles-only]
neobear_cli.py open --id "NOTE_ID" [--title "My Note"] [--new-window] [--edit]
neobear_cli.py add-text --id "NOTE_ID" --text "Content" [--mode append] [--new-line]
neobear_cli.py archive --id "NOTE_ID"
neobear_cli.py trash --id "NOTE_ID"
```

详见 `references/cli-reference.md`（安装、完整命令参考、高级用法、示例、故障排除）

## Requirements

- Bear app installed on macOS
- Python 3.6+
- Bear API token (for some operations) — see `references/cli-reference.md`

## Links

- **Bear App**: https://bear.app
- **Bear URL Scheme Docs**: https://bear.app/faq/X-callback-url%20Scheme%20documentation/

---

**Version:** 2.0.0 | **Platform:** macOS only | **License:** MIT

## When NOT to Use

- 不用于 Bear Blog 发布（用 bearclaw-native）。
- 不用于非 Bear 的笔记应用。
- Bear app 未安装时不使用。

## Error Handling

- Bear URL scheme 不可用时，提示用户启动 Bear。
- 笔记搜索无结果时，建议放宽关键词。
- URL 编码失败时，尝试 fallback 编码方式。

## Internal Acceptance

- Bear 操作成功完成（创建/搜索/更新）。
- URL 编码正确处理中英文和特殊字符。
- 返回的笔记内容与 Bear 中显示一致。

## Gotchas

- Bear x-callback-url 的 URL 编码规则不标准，空格用 `%20` 不是 `+`。
- Bear 笔记的 note_id 是内部标识，用户看不到。
- 标签中的 `/` 需要双重编码。

## Delivery Contract

- 创建笔记后输出 Bear URL 和 note_id。
- 搜索结果以列表形式展示，包含标题和摘要。
- 更新操作后确认变更内容。
**注意：本技能是大型流水线的一部分。Do **not** report completion to the user unless all dependent tools/scripts/skills have been verified as integrated.**not** report completion to the user unless all dependent tools/scripts/skills integration tests have passed.**

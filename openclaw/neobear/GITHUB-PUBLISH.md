# 🚀 NeoBear - GitHub 发布指南

## ⚡ 3 分钟快速发布

### 步骤 1: 初始化 Git

```bash
cd neobear

git init
git add .
git commit -m "🐻💫 NeoBear v2.0.0 - Next-Gen Bear Notes Integration

Features:
- Perfect URL encoding (%20 not +)
- Modern Python 3.7+ code
- JSON output support
- Dry-run mode
- Comprehensive documentation

'Where old Bear links become new again.'"
```

---

### 步骤 2: 创建 GitHub 仓库

1. 访问 https://github.com/new

2. 填写:
   - **Repository name**: `neobear`
   - **Description**: `🐻💫 Next-gen Bear Notes integration for OpenClaw - Perfect URL encoding, no more space bugs!`
   - **Public** ✅

3. **不要勾选**任何初始化选项

4. **Create repository**

---

### 步骤 3: 推送代码

```bash
git remote add origin https://github.com/你的用户名/neobear.git
git branch -M main
git push -u origin main
```

**认证:** 使用 Personal Access Token

---

## 🎁 创建 Release

访问: `https://github.com/你的用户名/neobear/releases/new`

**填写:**

- **Tag**: `v2.0.0`
- **Title**: `🐻💫 NeoBear v2.0.0 - Neo-Era Bear Integration`
- **Description**:

```markdown
## 🎉 NeoBear v2.0.0 - Initial Release

**Next-gen Bear Notes integration for OpenClaw**

### ✨ What's New

NeoBear solves the infamous "spaces become plus signs" bug that plagued older Bear tools.

**The Problem:**
```
Old tools: "My Note" → "My+Note" ❌
NeoBear:   "My Note" → "My Note"  ✅
```

### 🌟 Features

- ✅ **Perfect Encoding** - Uses `%20` not `+` for spaces
- ✅ **Modern Code** - Python 3.7+ best practices  
- ✅ **JSON Output** - Automation-friendly
- ✅ **Dry Run** - Test before executing
- ✅ **Rich Docs** - Comprehensive guide included

### 🚀 Quick Start

```bash
# Install
mkdir -p ~/.openclaw/skills/neobear
cp SKILL.md neobear_cli.py ~/.openclaw/skills/neobear/
openclaw restart

# Use
Create a Bear note titled "Test" with content "Hello World"
```

### 📦 Installation

Download the repository and run:
```bash
./install.sh
```

### 🆚 vs Old Tools

| Feature | Old Tools | NeoBear |
|---------|-----------|---------|
| Space Encoding | `+` ❌ | `%20` ✅ |
| JSON Output | No | Yes ✅ |
| Dry Run | No | Yes ✅ |
| Documentation | Basic | Comprehensive ✅ |

### 📚 Documentation

- [README.md](./README.md) - Overview
- [SKILL.md](./SKILL.md) - Complete reference

### 🔗 Links

- **Bear App**: https://bear.app
- **OpenClaw**: https://openclaw.ai

---

**"Where old Bear links become new again."** 🐻💫
```

---

## 📝 添加 Topics

```
bear-notes
bear-app
openclaw
openclaw-skill
url-encoding
macos
python
cli-tool
```

---

## 🌟 分享

### Bear Community

分享到 Bear 用户社区和论坛

### Reddit

- r/bearapp
- r/OpenClaw
- r/Python

### Twitter/X

```
🐻💫 NeoBear - 新时代 Bear Notes 工具！

✅ 修复空格 → + 号 bug
✅ 完美 URL 编码
✅ 现代化设计
✅ OpenClaw 集成

https://github.com/你的用户名/neobear

#BearNotes #OpenClaw #Python
```

---

## ✅ 发布检查清单

- [ ] Git 仓库初始化
- [ ] 代码提交
- [ ] GitHub 仓库创建
- [ ] 代码推送
- [ ] Release 创建
- [ ] Topics 添加
- [ ] 社区分享

---

**Happy Publishing!** 🐻💫

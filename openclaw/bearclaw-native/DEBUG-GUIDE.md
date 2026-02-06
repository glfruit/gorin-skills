# 🐛 BearClaw Native 调试指南（基于真实页面）

## 📋 Bear Blog 真实页面结构

### 新建文章页面

**URL 格式：** `https://bearblog.dev/{username}/dashboard/posts/new/`

例如：`https://bearblog.dev/gorin/dashboard/posts/new/`

### 表单结构

```html
<form method="POST" class="post-form full-width">
    <!-- 隐藏字段 -->
    <input type="text" name="publish" id="publish" value="" hidden>
    
    <!-- Header Content (Frontmatter) - ContentEditable Div -->
    <div
        id="header_content"
        class="editable"
        contenteditable="true"
    >
        <b>title:</b> <br>
    </div>
    
    <!-- Hidden field for header content -->
    <input type="hidden" id="hidden_header_content" name="header_content">
    
    <!-- Body Content - Textarea -->
    <textarea
        name="body_content"
        id="body_content"
        style="min-height: 500px;"
    ></textarea>
</form>
```

### 按钮

```html
<!-- 发布 (设置 publish=true) -->
<button 
    type="submit" 
    id="publish-button"
    onclick="document.getElementById('publish').value = true;"
>
    Publish
</button>

<!-- 保存为草稿 (设置 publish=false) -->
<button
    type="submit"
    id="save-button"
    onclick="document.getElementById('publish').value = false;"
>
    Save as draft
</button>
```

### Frontmatter 格式

在 `header_content` div 中：

```
title: My Post Title
link: my-custom-url
tags: tag1, tag2, tag3
is_page: false
make_discoverable: true
```

---

## 🔍 手动测试步骤

### 1. 打开新建文章页面

```bash
# 获取你的用户名
openclaw browser open https://bearblog.dev

# 导航到新建文章页面（替换 gorin 为你的用户名）
openclaw browser navigate https://bearblog.dev/gorin/dashboard/posts/new/
```

### 2. 检查页面元素

```bash
# 获取页面快照
openclaw browser snapshot --interactive

# 查找关键元素
openclaw browser snapshot | grep -i "header_content"
openclaw browser snapshot | grep -i "body_content"
openclaw browser snapshot | grep -i "publish-button"
```

### 3. 手动填充表单（测试）

```bash
# 填充 header content
openclaw browser evaluate --fn '
  const header = document.getElementById("header_content");
  header.innerHTML = "title: Test Post<br>tags: test";
'

# 填充 body content
openclaw browser evaluate --fn '
  const body = document.getElementById("body_content");
  body.value = "This is a test post content.";
'

# 点击发布按钮
openclaw browser evaluate --fn '
  const btn = document.getElementById("publish-button");
  btn.click();
'
```

---

## 🧪 调试 BearClaw Native

### 启用完整调试

```bash
export BEARCLAW_DEBUG=true
export BEARCLAW_TIMEOUT=60000
export BEARCLAW_MAX_RETRIES=5
```

### 测试发布流程

```
在 OpenClaw 中说：
"使用 bearclaw-native 创建一篇测试文章，标题是 Test，内容是 Hello World"
```

### 查看调试输出

```bash
# 查看日志（OpenClaw 的日志位置）
tail -f ~/.openclaw/logs/*.log

# 查看截图
ls -lt /tmp/bearclaw-*.png

# 打开截图
open /tmp/bearclaw-form-ready-*.png
open /tmp/bearclaw-form-filled-*.png
open /tmp/bearclaw-after-save-*.png
```

---

## 🔧 常见问题及解决

### 问题 1: 找不到用户名

**错误:**
```
Cannot determine Bear Blog username
```

**原因:** 浏览器未在 Bear Blog 页面

**解决:**
```bash
# 先访问 Bear Blog dashboard
openclaw browser navigate https://bearblog.dev

# 或直接访问你的 dashboard（替换用户名）
openclaw browser navigate https://bearblog.dev/gorin/dashboard/
```

---

### 问题 2: header_content 未填充

**检查:**
```bash
openclaw browser evaluate --fn '
  const header = document.getElementById("header_content");
  console.log("Header exists:", !!header);
  console.log("Header content:", header ? header.innerHTML : "NOT FOUND");
'
```

**手动修复:**
```bash
openclaw browser evaluate --fn '
  const header = document.getElementById("header_content");
  if (header) {
    header.innerHTML = "title: My Title<br>tags: test";
  }
'
```

---

### 问题 3: body_content 未填充

**检查:**
```bash
openclaw browser evaluate --fn '
  const body = document.getElementById("body_content");
  console.log("Body exists:", !!body);
  console.log("Body value:", body ? body.value : "NOT FOUND");
'
```

**手动修复:**
```bash
openclaw browser evaluate --fn '
  const body = document.getElementById("body_content");
  if (body) {
    body.value = "My content here";
  }
'
```

---

### 问题 4: 发布按钮未点击

**检查按钮是否存在:**
```bash
openclaw browser evaluate --fn '
  const btn = document.getElementById("publish-button");
  console.log("Button exists:", !!btn);
  console.log("Button text:", btn ? btn.textContent : "NOT FOUND");
'
```

**手动点击:**
```bash
openclaw browser evaluate --fn '
  const btn = document.getElementById("publish-button");
  if (btn) {
    btn.click();
  } else {
    throw new Error("Button not found");
  }
'
```

---

### 问题 5: JavaScript 评估被禁用

**错误:**
```
browser.evaluateEnabled=false
```

**解决:**
```bash
# 在 OpenClaw 配置中启用 evaluate
openclaw config set browser.evaluateEnabled true
openclaw restart
```

---

## 📸 截图分析

### form-ready 截图应该显示:
- ✅ "New post | Bear Blog" 标题
- ✅ header_content div (可编辑)
- ✅ body_content textarea
- ✅ "Publish" 和 "Save as draft" 按钮

### form-filled 截图应该显示:
- ✅ header_content 包含 "title: XXX"
- ✅ body_content 包含文章内容
- ✅ 表单已填充

### after-save 截图应该显示:
- ✅ URL 已改变（不再是 /new/）
- ✅ 可能显示文章列表或文章详情
- ✅ 没有错误消息

---

## 🧩 完整测试脚本

```bash
#!/bin/bash
# test-bearclaw-native.sh - 完整测试流程

echo "🧪 测试 BearClaw Native"
echo ""

# 1. 检查浏览器状态
echo "1️⃣ 检查浏览器..."
openclaw browser status

# 2. 打开 Bear Blog
echo "2️⃣ 打开 Bear Blog..."
openclaw browser navigate https://bearblog.dev

# 3. 等待加载
sleep 2

# 4. 获取快照
echo "3️⃣ 获取页面快照..."
openclaw browser snapshot > /tmp/bearblog-snapshot.txt

# 5. 提取用户名
USERNAME=$(grep -o '/[^/]*/dashboard/' /tmp/bearblog-snapshot.txt | head -1 | cut -d'/' -f2)
echo "   用户名: $USERNAME"

# 6. 导航到新建文章页
echo "4️⃣ 导航到新建文章页..."
openclaw browser navigate "https://bearblog.dev/$USERNAME/dashboard/posts/new/"

# 7. 等待页面加载
sleep 2

# 8. 填充表单
echo "5️⃣ 填充表单..."
openclaw browser evaluate --fn '
  const header = document.getElementById("header_content");
  const body = document.getElementById("body_content");
  
  if (header) header.innerHTML = "title: Test Post<br>tags: test";
  if (body) body.value = "This is a test post.";
  
  console.log("Header:", header ? "OK" : "FAILED");
  console.log("Body:", body ? "OK" : "FAILED");
'

# 9. 截图
echo "6️⃣ 截图..."
openclaw browser screenshot --full-page

# 10. 点击发布
echo "7️⃣ 点击发布..."
openclaw browser evaluate --fn '
  const btn = document.getElementById("publish-button");
  if (btn) {
    btn.click();
  } else {
    throw new Error("Publish button not found");
  }
'

# 11. 等待保存
echo "8️⃣ 等待保存..."
sleep 3

# 12. 获取最终 URL
echo "9️⃣ 检查结果..."
openclaw browser tabs

echo ""
echo "✅ 测试完成！"
echo "检查截图: ls /tmp/*.png"
```

保存为 `test-bearclaw-native.sh` 并运行:

```bash
chmod +x test-bearclaw-native.sh
./test-bearclaw-native.sh
```

---

## 📝 重要发现总结

### Bear Blog 页面的关键特征:

1. **URL 包含用户名**: `/gorin/dashboard/posts/new/`
2. **Header Content 是 ContentEditable Div**: 不是 input，而是可编辑的 div
3. **Frontmatter 格式**: `title: xxx` (不是 YAML 前缀 `---`)
4. **两个提交按钮**: 
   - Publish (publish=true)
   - Save as draft (publish=false)
5. **表单提交**: JavaScript 会将 header_content 复制到 hidden_header_content

### BearClaw Native 的实现要点:

1. **获取用户名**: 从 URL 或页面快照提取
2. **填充 header_content**: 使用 `innerHTML` 设置（带 `<br>`）
3. **填充 body_content**: 使用 `value` 属性
4. **点击发布**: 直接调用 `document.getElementById('publish-button').click()`
5. **无需手动设置 publish 字段**: 按钮的 onclick 会处理

---

## 🎯 下一步

如果上述测试通过，BearClaw Native 应该能正常工作。

如果仍有问题：

1. 启用调试模式
2. 查看截图
3. 检查 JavaScript console 错误
4. 查看网络请求
5. 手动测试每个步骤

需要帮助？提供：
- 调试日志
- 截图
- 错误消息
- 页面快照

祝调试顺利！🐻🦞

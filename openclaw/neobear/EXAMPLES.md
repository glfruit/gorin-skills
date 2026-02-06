# 🐻💫 NeoBear - 使用示例

## 基础使用

### 1. 转换单个 URL

```bash
# 基本用法
$ ./neobear.py "bear://x-callback-url/open-note?title=My%20Note"
bear://x-callback-url/open-note?title=My+Note

# 带多个参数
$ ./neobear.py "bear://x-callback-url/open-note?title=My%20Note&text=Some%20content"
bear://x-callback-url/open-note?title=My+Note&text=Some+content
```

---

## 剪贴板集成

### 2. 从剪贴板转换

```bash
# 1. 在 Bear 中复制链接
# 2. 运行 NeoBear
$ ./neobear.py --clipboard
✓ Converted and copied to clipboard!
Result: bear://x-callback-url/open-note?title=My+Note

# 3. 粘贴使用
```

**工作流程：**
```
Bear App → Copy Link → NeoBear → Fixed Link in Clipboard
```

---

## 批量处理

### 3. 从文件读取

**urls.txt:**
```
bear://x-callback-url/open-note?title=Note%201
bear://x-callback-url/open-note?title=Note%202
bear://x-callback-url/open-note?title=Note%203
```

**转换：**
```bash
$ ./neobear.py --file urls.txt
bear://x-callback-url/open-note?title=Note+1
bear://x-callback-url/open-note?title=Note+2
bear://x-callback-url/open-note?title=Note+3
```

### 4. 保存到文件

```bash
$ ./neobear.py --file urls.txt --output fixed-urls.txt
✓ Processed 3 URLs
✓ Saved to fixed-urls.txt
```

---

## 管道操作

### 5. 通过管道输入

```bash
# 从 echo
$ echo "bear://x-callback-url/open-note?title=Test%20Note" | ./neobear.py
bear://x-callback-url/open-note?title=Test+Note

# 从文件
$ cat urls.txt | ./neobear.py
bear://x-callback-url/open-note?title=Note+1
bear://x-callback-url/open-note?title=Note+2

# 结合 grep
$ grep "bear://" document.txt | ./neobear.py
```

---

## 高级用法

### 6. 与 xargs 结合

```bash
# 批量处理并保存
$ cat urls.txt | xargs -I {} ./neobear.py {} >> output.txt

# 只处理特定 URL
$ grep "open-note" urls.txt | xargs -I {} ./neobear.py {}
```

### 7. 在脚本中使用

**fix-bear-links.sh:**
```bash
#!/bin/bash
# 批量修复 Bear 链接

INPUT_FILE="$1"
OUTPUT_FILE="$2"

if [ -z "$INPUT_FILE" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 <input_file> <output_file>"
    exit 1
fi

./neobear.py --file "$INPUT_FILE" --output "$OUTPUT_FILE"

echo "✓ Fixed $(wc -l < "$OUTPUT_FILE") URLs"
```

**使用：**
```bash
chmod +x fix-bear-links.sh
./fix-bear-links.sh urls.txt fixed-urls.txt
```

---

## Python 集成

### 8. 作为 Python 模块

```python
#!/usr/bin/env python3
from neobear import NeoBear

# 转换单个 URL
url = "bear://x-callback-url/open-note?title=My%20Note"
fixed = NeoBear.convert(url)
print(fixed)

# 批量转换
urls = [
    "bear://x-callback-url/open-note?title=Note%201",
    "bear://x-callback-url/open-note?title=Note%202"
]
fixed_urls = NeoBear.convert_batch(urls)
for url in fixed_urls:
    print(url)

# 从剪贴板
try:
    fixed = NeoBear.from_clipboard()
    NeoBear.to_clipboard(fixed)
    print("✓ Converted!")
except RuntimeError as e:
    print(f"Error: {e}")

# 文件操作
urls = NeoBear.from_file('input.txt')
NeoBear.to_file(urls, 'output.txt')
```

---

## Alfred Workflow

### 9. Alfred 集成

**Script Filter:**
```bash
#!/bin/bash
# Alfred Script Filter

query="{query}"

# 转换 URL
result=$(./neobear.py "$query")

# 输出 JSON for Alfred
cat << EOF
{
  "items": [
    {
      "title": "$result",
      "subtitle": "Press Enter to copy",
      "arg": "$result",
      "text": {
        "copy": "$result",
        "largetype": "$result"
      }
    }
  ]
}
EOF
```

---

## Keyboard Maestro

### 10. Keyboard Maestro Macro

**步骤：**
1. **Get Clipboard** → Variable: `originalURL`
2. **Execute Shell Script**:
   ```bash
   /path/to/neobear.py "$KMVAR_originalURL"
   ```
3. **Set Clipboard** → From results
4. **Display Notification**: "✓ Bear URL Fixed!"

---

## 自动化场景

### 11. 监视文件夹

```bash
#!/bin/bash
# watch-and-convert.sh
# 监视文件夹中的 URL 文件并自动转换

WATCH_DIR="$HOME/Downloads/bear-urls"
OUTPUT_DIR="$HOME/Downloads/bear-urls-fixed"

fswatch -o "$WATCH_DIR" | while read num; do
    for file in "$WATCH_DIR"/*.txt; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            ./neobear.py --file "$file" --output "$OUTPUT_DIR/$filename"
            echo "✓ Processed $filename"
        fi
    done
done
```

### 12. Cron Job

```bash
# 每小时自动处理新文件
# crontab -e

0 * * * * /path/to/neobear.py --file /path/to/urls.txt --output /path/to/fixed.txt
```

---

## 集成示例

### 13. Obsidian Plugin

在 Obsidian 插件中使用：

```javascript
// Obsidian plugin code
const { exec } = require('child_process');

function fixBearURL(url) {
    return new Promise((resolve, reject) => {
        exec(`/path/to/neobear.py "${url}"`, (error, stdout) => {
            if (error) {
                reject(error);
                return;
            }
            resolve(stdout.trim());
        });
    });
}

// 使用
const fixedURL = await fixBearURL('bear://x-callback-url/...');
```

### 14. Web Service

```python
from flask import Flask, request, jsonify
from neobear import NeoBear

app = Flask(__name__)

@app.route('/convert', methods=['POST'])
def convert():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        fixed_url = NeoBear.convert(url)
        return jsonify({'original': url, 'fixed': fixed_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
```

---

## 故障排除

### 常见问题

**Q: 剪贴板功能不工作？**
```bash
# 安装 pyperclip
pip install pyperclip

# macOS 权限
# 系统偏好设置 → 安全性与隐私 → 隐私 → 辅助功能
```

**Q: 权限被拒绝？**
```bash
chmod +x neobear.py
```

**Q: Python 版本问题？**
```bash
# 确保 Python 3.7+
python3 --version

# 使用正确的 Python
python3 neobear.py "..."
```

---

## 💡 专业技巧

1. **创建别名**
   ```bash
   # 添加到 ~/.bashrc 或 ~/.zshrc
   alias neobear='/path/to/neobear.py'
   alias nbear='/path/to/neobear.py --clipboard'
   ```

2. **快捷键绑定**
   - macOS: 使用 Keyboard Maestro
   - Linux: 使用 xbindkeys
   - Windows: 使用 AutoHotkey

3. **与编辑器集成**
   - VS Code: 创建任务
   - Vim: 创建命令
   - Emacs: 编写 elisp 函数

---

**更多示例请访问 GitHub Issues 或 Discussions!** 🐻💫

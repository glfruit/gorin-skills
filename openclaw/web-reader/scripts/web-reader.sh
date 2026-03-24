#!/usr/bin/env bash
# web-reader.sh — 统一网页读取脚本（三层架构）
# L1: defuddle/Scrapling 快速抓取
# L2: PinchTab 浏览器渲染（持久化登录态）
# L3: defuddle 内容清洗（统一 markdown 输出）
#
# 用法:
#   bash web-reader.sh <url> [--browser] [--profile <name>] [--save <path>] [--json] [--max-chars <n>] [--timeout <s>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WCF_FETCH="$HOME/.openclaw/skills/web-content-fetcher/scripts/fetch.py"

# ─── 默认参数 ─────────────────────────────────────────
URL=""
FORCE_BROWSER=false
PROFILE=""
SAVE_PATH=""
OUTPUT_JSON=false
MAX_CHARS=50000
TIMEOUT=30

# ─── 参数解析 ─────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --browser)    FORCE_BROWSER=true; shift ;;
    --profile)    PROFILE="$2"; shift 2 ;;
    --save)       SAVE_PATH="$2"; shift 2 ;;
    --json)       OUTPUT_JSON=true; shift ;;
    --max-chars)  MAX_CHARS="$2"; shift 2 ;;
    --timeout)    TIMEOUT="$2"; shift 2 ;;
    -h|--help)
      echo "用法: web-reader.sh <url> [--browser] [--profile <name>] [--save <path>] [--json] [--max-chars <n>] [--timeout <s>]"
      exit 0
      ;;
    -*)
      echo "错误: 未知参数 $1" >&2; exit 1 ;;
    *)
      if [[ -z "$URL" ]]; then URL="$1"; else echo "错误: 多余参数 $1" >&2; exit 1; fi
      shift ;;
  esac
done

if [[ -z "$URL" ]]; then
  echo "错误: 未提供 URL" >&2
  echo "用法: web-reader.sh <url> [--browser] [--profile <name>] [--save <path>] [--json]" >&2
  exit 1
fi

# ─── 辅助函数 ─────────────────────────────────────────

# 从 URL 提取域名
get_domain() {
  echo "$1" | sed -E 's|^https?://||' | sed -E 's|/.*||' | sed -E 's|:.*||'
}

# 获取当前 ISO 时间戳
now_iso() {
  date +"%Y-%m-%dT%H:%M:%S%z"
}

# 域名→PinchTab profile 映射
domain_to_profile() {
  local domain="$1"
  case "$domain" in
    *zhihu.com)            echo "zhihu" ;;
    *x.com|*twitter.com)   echo "x-twitter" ;;
    *mp.weixin.qq.com)     echo "wechat" ;;
    *)                     echo "default" ;;
  esac
}

# 判断域名是否需要 L2（浏览器渲染）
needs_browser() {
  local domain="$1"
  case "$domain" in
    *zhihu.com)          return 0 ;;   # 知乎需登录
    *x.com|*twitter.com) return 0 ;;   # X 需登录
    *)                   return 1 ;;   # 其他默认 L1
  esac
}

# 检查 markdown 内容是否有效（非空、非登录墙）
content_is_valid() {
  local content="$1"
  local len=${#content}

  # 太短 = 无效
  if [[ $len -lt 100 ]]; then
    return 1
  fi

  # 检测常见登录墙标志
  if echo "$content" | grep -qiE '(请登录|sign.?in.?to.?continue|login.?required|403.?forbidden|access.?denied|验证码)'; then
    return 1
  fi

  return 0
}

# 构建 YAML front matter + markdown 输出
build_output() {
  local content="$1"
  local title="$2"
  local author="$3"
  local published="$4"
  local site="$5"
  local word_count="$6"
  local captured_via="$7"

  local captured_at
  captured_at="$(now_iso)"

  # 使用 python3 统一输出，避免 YAML 特殊字符问题
  python3 << 'PYEOF' - "$URL" "$title" "$author" "$published" "$site" "$word_count" "$captured_via" "$captured_at" "$OUTPUT_JSON" "$content"
import sys

args = sys.argv[1:]
url, title, author, published, site, wc, via, cap_at, output_json = args[:9]
content = args[9]

if output_json == "true":
    import json
    print(json.dumps({
        "url": url, "title": title, "author": author,
        "published": published, "site": site,
        "word_count": int(wc) if wc.isdigit() else 0,
        "captured_via": via, "captured_at": cap_at,
        "content": content
    }, ensure_ascii=False, indent=2))
else:
    # YAML-safe: 用引号包裹含特殊字符的值
    def yval(v):
        if not v:
            return '""'
        if any(c in v for c in ':#{}[]&*?|->!%@`'):
            return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'
        return v

    print("---")
    print(f"url: {url}")
    print(f"title: {yval(title)}")
    print(f"author: {yval(author)}")
    print(f"published: {yval(published)}")
    print(f"site: {yval(site)}")
    print(f"word_count: {wc}")
    print(f"captured_at: {cap_at}")
    print(f"captured_via: {via}")
    print("---")
    print()
    print(content)
PYEOF
}

# ─── L1: defuddle 快速抓取 ─────────────────────────────

try_defuddle() {
  local url="$1"
  local json_output

  # defuddle parse --json --markdown 直接获取 URL
  if ! json_output=$(defuddle parse --json --markdown "$url" 2>/dev/null); then
    return 1
  fi

  # 用单次 python3 调用解析所有字段，通过临时文件传递 JSON
  local tmpjson="/tmp/web-reader-defuddle-$$.json"
  echo "$json_output" > "$tmpjson"

  local parsed
  parsed=$(python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
# Each field on its own line, empty fields as empty lines
print(d.get('title', ''))
print(d.get('author', ''))
print(d.get('published', ''))
print(d.get('site', ''))
print(d.get('wordCount', 0))
print('<<<CONTENT_SEP>>>')
sys.stdout.write(d.get('content', ''))
" "$tmpjson" 2>/dev/null) || { rm -f "$tmpjson"; return 1; }
  rm -f "$tmpjson"

  local content
  local meta_block="${parsed%%<<<CONTENT_SEP>>>*}"
  content="${parsed#*<<<CONTENT_SEP>>>}"
  content="${content#$'\n'}"

  # Read fields line by line
  local title author published site word_count
  { read -r title; read -r author; read -r published; read -r site; read -r word_count; } <<< "$meta_block"

  # 截断
  content="${content:0:$MAX_CHARS}"

  if content_is_valid "$content"; then
    build_output "$content" "$title" "$author" "$published" "${site:-$(get_domain "$url")}" "${word_count:-0}" "defuddle"
    return 0
  fi
  return 1
}

# ─── L1 备选: Scrapling ──────────────────────────────

try_scrapling() {
  local url="$1"
  local content

  if [[ ! -f "$WCF_FETCH" ]]; then
    return 1
  fi

  if ! content=$(python3 "$WCF_FETCH" "$url" "$MAX_CHARS" 2>/dev/null); then
    return 1
  fi

  if content_is_valid "$content"; then
    local domain
    domain="$(get_domain "$url")"
    build_output "$content" "" "" "" "$domain" "0" "scrapling"
    return 0
  fi
  return 1
}

# ─── L2: PinchTab 浏览器渲染 ─────────────────────────

try_pinchtab() {
  local url="$1"
  local profile="$2"

  # 检查 PinchTab 是否可用
  if ! command -v pinchtab &>/dev/null; then
    echo "错误: PinchTab 未安装" >&2
    return 1
  fi

  # 检查 daemon 是否运行（通过 CLI，自带 token）
  if ! pinchtab health &>/dev/null; then
    echo "警告: PinchTab daemon 未运行，尝试启动..." >&2
    pinchtab daemon start 2>/dev/null || true
    sleep 3
    if ! pinchtab health &>/dev/null; then
      echo "错误: PinchTab daemon 启动失败" >&2
      return 1
    fi
  fi

  local html_file="/tmp/web-reader-$$.html"
  local tmpjson="/tmp/web-reader-pt-$$.json"

  # 读取 PinchTab API token
  local token
  token=$(python3 -c "import json; print(json.load(open('$HOME/.pinchtab/config.json'))['server']['token'])" 2>/dev/null) || true

  # 确定 --server 参数（非 default profile 需要指向对应实例端口）
  local server_flag=""
  if [[ "$profile" != "default" && -n "$token" ]]; then
    # 启动 profile 实例（如果未运行）
    # 知乎反爬检测 headless → 必须 headed 模式
    local headless_val="true"
    case "$profile" in
      zhihu) headless_val="false" ;;
    esac
    curl -sf -X POST "http://127.0.0.1:9867/profiles/$profile/start" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $token" \
      -d "{\"headless\":$headless_val}" >/dev/null 2>/dev/null || true
    sleep 2

    # 查询 /instances 获取 profile 对应的端口
    local instances_json instance_port
    instances_json=$(curl -sf "http://127.0.0.1:9867/instances" \
      -H "Authorization: Bearer $token" 2>/dev/null) || true

    if [[ -n "$instances_json" ]]; then
      instance_port=$(python3 -c "
import json, sys
data = json.loads(sys.argv[1])
instances = data if isinstance(data, list) else data.get('instances', data.get('data', []))
for inst in instances:
    p = inst.get('profile', inst.get('profileName', ''))
    if p == sys.argv[2]:
        # 尝试多种字段名
        port = inst.get('port', inst.get('cdpPort', inst.get('debugPort', '')))
        if port:
            print(port)
            break
" "$instances_json" "$profile" 2>/dev/null) || true
    fi

    if [[ -n "$instance_port" ]]; then
      server_flag="--server http://127.0.0.1:$instance_port"
      echo "## [web-reader] PinchTab profile '$profile' → 端口 $instance_port" >&2
    else
      echo "警告: 未找到 profile '$profile' 的实例端口，使用默认" >&2
    fi
  fi

  # 导航到 URL
  if ! pinchtab $server_flag nav "$url" &>/dev/null; then
    echo "警告: PinchTab 导航失败" >&2
    return 1
  fi

  # 等待页面加载完成
  pinchtab $server_flag wait --load networkidle --timeout 15000 >/dev/null 2>/dev/null || sleep 3
  # X SPA 需要额外时间渲染推文内容
  sleep 2

  # ─── X/Twitter 专用提取（defuddle 对 X SPA 效果差）───
  local domain
  domain="$(get_domain "$url")"
  if [[ "$domain" == *x.com || "$domain" == *twitter.com ]]; then
    # 等待推文 DOM 元素渲染（最多等 8 秒）
    local wait_count=0
    while [[ $wait_count -lt 4 ]]; do
      local has_tweet
      has_tweet=$(pinchtab $server_flag eval 'document.querySelector("[data-testid=\"tweetText\"]") ? "yes" : "no"' 2>/dev/null) || true
      if echo "$has_tweet" | grep -q '"yes"'; then
        break
      fi
      sleep 2
      wait_count=$((wait_count + 1))
    done

    local x_extract_json="/tmp/web-reader-x-extract-$$.json"
    pinchtab $server_flag eval '
(() => {
  const tweets = document.querySelectorAll("[data-testid=\"tweetText\"]");
  const user = document.querySelector("[data-testid=\"User-Name\"]");
  const time = document.querySelector("time");
  // 主推文是第一个 tweetText，后续是回复
  const parts = [];
  tweets.forEach((t, i) => {
    parts.push(t.innerText);
  });
  const userParts = user ? user.innerText.split("\n") : ["", ""];
  return JSON.stringify({
    text: parts.join("\n\n---\n\n"),
    displayName: userParts[0] || "",
    handle: userParts[1] || "",
    time: time ? time.getAttribute("datetime") : "",
    title: document.title,
    tweetCount: tweets.length
  });
})()
' > "$x_extract_json" 2>/dev/null || true

    if [[ -s "$x_extract_json" ]]; then
      local x_result
      x_result=$(python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    outer = json.loads(f.read(), strict=False)
inner = json.loads(outer.get('result', '{}'))
text = inner.get('text', '').strip()
if not text:
    sys.exit(1)
name = inner.get('displayName', '')
handle = inner.get('handle', '')
time_str = inner.get('time', '')
title = inner.get('title', '').replace(' / X', '').replace('(1) X 上的 ', '')
# Output fields
print(title)
print(name)
print(time_str)
print('x.com')
print(len(text.split()))
print('<<<CONTENT_SEP>>>')
author_line = f'**{name}** {handle}' if name else ''
time_line = f'*{time_str}*' if time_str else ''
header = '  \\n'.join(filter(None, [author_line, time_line]))
if header:
    sys.stdout.write(header + '\\n\\n' + text)
else:
    sys.stdout.write(text)
" "$x_extract_json" 2>/dev/null) || true
      rm -f "$x_extract_json"

      if [[ -n "$x_result" ]]; then
        local meta_block="${x_result%%<<<CONTENT_SEP>>>*}"
        local content="${x_result#*<<<CONTENT_SEP>>>}"
        content="${content#$'\n'}"
        local title author published site word_count
        { read -r title; read -r author; read -r published; read -r site; read -r word_count; } <<< "$meta_block"

        content="${content:0:$MAX_CHARS}"

        if [[ ${#content} -gt 10 ]]; then
          build_output "$content" "$title" "$author" "$published" "${site:-x.com}" "${word_count:-0}" "pinchtab+x-extract"
          return 0
        fi
      fi
    fi
    rm -f "$x_extract_json"
  fi

  # ─── 通用提取: HTML → defuddle ───
  pinchtab $server_flag eval 'document.documentElement.outerHTML' > "$tmpjson" 2>/dev/null || true

  # 从 eval JSON 提取 HTML 并直接写入 html_file（全部在 python 中完成，不经过 bash 变量）
  local extract_ok=false
  if [[ -s "$tmpjson" ]]; then
    if python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    data = json.loads(f.read(), strict=False)
html = data.get('result', '')
if len(html) > 200:
    with open(sys.argv[2], 'w') as out:
        out.write(html)
    sys.exit(0)
else:
    sys.exit(1)
" "$tmpjson" "$html_file" 2>/dev/null; then
      extract_ok=true
    fi
    rm -f "$tmpjson"
  fi

  if [[ "$extract_ok" == "true" ]]; then
    # defuddle 清洗 HTML 文件
    local defuddle_json="/tmp/web-reader-defuddle-pt-$$.json"
    if defuddle parse --json --markdown "$html_file" > "$defuddle_json" 2>/dev/null; then
      local parsed
      parsed=$(python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    d = json.loads(f.read(), strict=False)
print(d.get('title', ''))
print(d.get('author', ''))
print(d.get('published', ''))
print(d.get('site', ''))
print(d.get('wordCount', 0))
print('<<<CONTENT_SEP>>>')
sys.stdout.write(d.get('content', ''))
" "$defuddle_json" 2>/dev/null) || true
      rm -f "$defuddle_json"

      if [[ -n "$parsed" ]]; then
        local meta content title author published site word_count
        local meta_block="${parsed%%<<<CONTENT_SEP>>>*}"
        content="${parsed#*<<<CONTENT_SEP>>>}"
        content="${content#$'\n'}"
        { read -r title; read -r author; read -r published; read -r site; read -r word_count; } <<< "$meta_block"

        rm -f "$html_file"
        content="${content:0:$MAX_CHARS}"

        if content_is_valid "$content"; then
          build_output "$content" "$title" "$author" "$published" "${site:-$(get_domain "$url")}" "${word_count:-0}" "pinchtab+defuddle"
          return 0
        fi
      fi
    fi
    rm -f "$html_file" "$defuddle_json"
  fi

  # 降级: 用 PinchTab text 输出（纯文本）
  local text_json="/tmp/web-reader-text-$$.json"
  pinchtab $server_flag text --raw > "$text_json" 2>/dev/null || true

  if [[ -s "$text_json" ]]; then
    local clean_text
    clean_text=$(python3 -c "
import json, sys, re
with open(sys.argv[1]) as f:
    data = json.loads(f.read(), strict=False)
text = data.get('text', '')
m = re.search(r'<untrusted_web_content[^>]*>(.*?)</untrusted_web_content>', text, re.DOTALL)
if m:
    print(m.group(1).strip())
else:
    print(text)
" "$text_json" 2>/dev/null) || true
    rm -f "$text_json"

    if content_is_valid "$clean_text"; then
      build_output "$clean_text" "" "" "" "$(get_domain "$url")" "0" "pinchtab-text"
      return 0
    fi
  fi
  rm -f "$text_json"

  return 1
}

# ─── 主路由逻辑 ──────────────────────────────────────

DOMAIN="$(get_domain "$URL")"

# 确定 profile
if [[ -z "$PROFILE" ]]; then
  PROFILE="$(domain_to_profile "$DOMAIN")"
fi

# 捕获输出的辅助函数
run_and_capture() {
  local output_file="/tmp/web-reader-output-$$.md"

  # 强制浏览器模式
  if [[ "$FORCE_BROWSER" == "true" ]]; then
    echo "## [web-reader] L2: 浏览器渲染 (profile: $PROFILE)" >&2
    if try_pinchtab "$URL" "$PROFILE" > "$output_file"; then
      cat "$output_file"
      if [[ -n "$SAVE_PATH" ]]; then
        mkdir -p "$(dirname "$SAVE_PATH")"
        cp "$output_file" "$SAVE_PATH"
        echo "## [web-reader] 已保存到 $SAVE_PATH" >&2
      fi
      rm -f "$output_file"
      return 0
    fi
    rm -f "$output_file"
    echo "错误: 浏览器渲染失败" >&2
    return 1
  fi

  # 域名需要浏览器
  if needs_browser "$DOMAIN"; then
    echo "## [web-reader] 域名 $DOMAIN → L2 浏览器渲染 (profile: $PROFILE)" >&2
    if try_pinchtab "$URL" "$PROFILE" > "$output_file"; then
      cat "$output_file"
      if [[ -n "$SAVE_PATH" ]]; then
        mkdir -p "$(dirname "$SAVE_PATH")"
        cp "$output_file" "$SAVE_PATH"
        echo "## [web-reader] 已保存到 $SAVE_PATH" >&2
      fi
      rm -f "$output_file"
      return 0
    fi
    echo "警告: L2 失败，降级到 L1 尝试..." >&2
  fi

  # L1: defuddle 优先
  echo "## [web-reader] L1: defuddle 快速抓取" >&2
  if try_defuddle "$URL" > "$output_file"; then
    cat "$output_file"
    if [[ -n "$SAVE_PATH" ]]; then
      mkdir -p "$(dirname "$SAVE_PATH")"
      cp "$output_file" "$SAVE_PATH"
      echo "## [web-reader] 已保存到 $SAVE_PATH" >&2
    fi
    rm -f "$output_file"
    return 0
  fi

  # L1 备选: Scrapling
  echo "## [web-reader] L1: Scrapling 备选" >&2
  if try_scrapling "$URL" > "$output_file"; then
    cat "$output_file"
    if [[ -n "$SAVE_PATH" ]]; then
      mkdir -p "$(dirname "$SAVE_PATH")"
      cp "$output_file" "$SAVE_PATH"
      echo "## [web-reader] 已保存到 $SAVE_PATH" >&2
    fi
    rm -f "$output_file"
    return 0
  fi

  # L2 兜底
  echo "## [web-reader] L2: 浏览器渲染兜底 (profile: $PROFILE)" >&2
  if try_pinchtab "$URL" "$PROFILE" > "$output_file"; then
    cat "$output_file"
    if [[ -n "$SAVE_PATH" ]]; then
      mkdir -p "$(dirname "$SAVE_PATH")"
      cp "$output_file" "$SAVE_PATH"
      echo "## [web-reader] 已保存到 $SAVE_PATH" >&2
    fi
    rm -f "$output_file"
    return 0
  fi

  rm -f "$output_file"
  echo "错误: 所有抓取策略均失败 (URL: $URL)" >&2
  return 1
}

run_and_capture
exit $?

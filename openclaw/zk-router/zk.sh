#!/bin/bash
# ZK Router - 完整执行脚本
# 统一笔记入口，智能判断类型，实际保存到 Obsidian vault

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT="$1"
SOURCE_CONTEXT="${2:-user}"

# Vault 路径
VAULT="${HOME}/Workspace/PKM/octopus"
PKM="${HOME}/.openclaw/pkm/pkm"

# 错误处理函数
error_exit() {
    echo "❌ 错误: $1" >&2
    exit 1
}

# 确保 vault 存在
if [ ! -d "$VAULT" ]; then
    error_exit "Vault 不存在: $VAULT"
fi

# 如果没有输入，退出
if [ -z "$INPUT" ]; then
    error_exit "请输入内容"
fi

# ===== 运行路由判断 =====
echo "🔍 分析内容类型..."
ROUTE_RESULT=$($SCRIPT_DIR/router.sh "$INPUT" "$SOURCE_CONTEXT" 2>/dev/null) || error_exit "路由判断失败"

TYPE=$(echo "$ROUTE_RESULT" | jq -r '.type') || error_exit "解析路由结果失败"
SUBTYPE=$(echo "$ROUTE_RESULT" | jq -r '.subtype') || error_exit "解析路由结果失败"
SCORE=$(echo "$ROUTE_RESULT" | jq -r '.score') || error_exit "解析路由结果失败"
LENGTH=$(echo "$ROUTE_RESULT" | jq -r '.length') || error_exit "解析路由结果失败"

if [ -z "$TYPE" ] || [ "$TYPE" = "null" ]; then
    error_exit "无法确定笔记类型"
fi

# 生成标题
generate_title() {
    local content="$1"
    # 移除URL
    local clean_content=$(echo "$content" | sed -E 's|https?://[^[:space:]]+||g')
    # 提取第一行或前30字符
    local first_line=$(echo "$clean_content" | head -1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [ ${#first_line} -gt 30 ]; then
        echo "${first_line:0:30}..."
    else
        echo "$first_line"
    fi
}

TITLE=$(generate_title "$INPUT")
DATE=$(date +%Y-%m-%d)
ID=$(date +%Y%m%d%H%M)

# ===== 提取URL（如果有）=====
extract_url() {
    echo "$1" | grep -oE 'https?://[^[:space:]]+' | head -1
}

URL=$(extract_url "$INPUT")

# ===== 全局变量：网页内容临时文件 =====
WEB_CONTENT_FILE=""

# ===== 如果是URL，抓取网页内容 =====
fetch_web_content() {
    local url=$1
    
    # 使用 web-reader skill
    local web_reader="${HOME}/.openclaw/skills/web-reader/scripts/web-reader.sh"
    
    if [ -f "$web_reader" ]; then
        echo "🌐 使用 web-reader 抓取网页..." >&2
        local raw_file=$(mktemp)
        local clean_file=$(mktemp)
        
        if bash "$web_reader" "$url" --save "$raw_file" >/dev/null 2>/dev/null; then
            if [ -s "$raw_file" ] && [ $(wc -c < "$raw_file") -gt 200 ]; then
                # 提取网页标题（从 frontmatter 的 title 字段）
                WEB_TITLE=$(grep '^title:' "$raw_file" | head -1 | sed 's/^title:[[:space:]]*//' | tr -d '"')
                # 提取正文：跳过第一个 YAML frontmatter (--- 到 ---)
                awk 'BEGIN{in_fm=0} /^---$/{in_fm=!in_fm; next} in_fm==0{print}' "$raw_file" > "$clean_file"
                rm "$raw_file"
                WEB_CONTENT_FILE="$clean_file"
                return 0
            fi
        fi
        rm -f "$raw_file" "$clean_file"
    fi
    
    return 1
}

if [ -n "$URL" ] && [ "$TYPE" = "literature" ]; then
    echo "🌐 抓取网页内容..."
    if fetch_web_content "$URL"; then
        echo "✅ 网页内容已抓取"
        # 用网页标题替换用户输入的简短标题
        if [ -n "$WEB_TITLE" ]; then
            TITLE="$WEB_TITLE"
        fi
    else
        echo "⚠️  无法抓取网页，仅保存URL"
        WEB_CONTENT_FILE=""
    fi
fi

# ===== 根据类型确定保存路径 =====
get_save_path() {
    local type=$1
    local subtype=$2
    
    case $type in
        "literature")
            if [ "$subtype" = "papers" ]; then
                echo "Zettels/2-Literature/Papers"
            elif [ "$subtype" = "books" ]; then
                echo "Zettels/2-Literature/Books"
            else
                echo "Zettels/2-Literature/Articles"
            fi
            ;;
        "idea")
            echo "Zettels/1-Fleeting"
            ;;
        "meeting")
            echo "Efforts/1-Projects"
            ;;
        "plan")
            echo "Efforts/1-Projects"
            ;;
        "review")
            echo "Calendar/Reviews"
            ;;
        "decision"|"summary"|"question")
            echo "Zettels/3-Permanent"
            ;;
        *)
            echo "Zettels/1-Fleeting"
            ;;
    esac
}

SAVE_DIR=$(get_save_path "$TYPE" "$SUBTYPE")
mkdir -p "$VAULT/$SAVE_DIR"

# ===== 生成文件名 =====
generate_filename() {
    local title="$1"
    local type=$2
    local url="$3"
    
    # 清理标题中的特殊字符（文件名用 ASCII 安全字符）
    local clean_title=$(echo "$title" | tr -cd '[:alnum:][:space:]-' | tr '[:space:]' '-')
    clean_title=$(echo "$clean_title" | sed 's/-*$//;s/^-*//')
    
    # 如果标题为空或太短，使用URL或ID
    if [ -z "$clean_title" ] || [ ${#clean_title} -lt 3 ]; then
        if [ -n "$url" ]; then
            # 从URL提取最后一部分作为标题
            clean_title=$(echo "$url" | sed 's|/$||' | awk -F'/' '{print $NF}' | cut -c1-30)
        fi
        # 如果还是空，使用ID
        if [ -z "$clean_title" ] || [ ${#clean_title} -lt 3 ]; then
            clean_title="note-${ID}"
        fi
    fi
    
    case $type in
        "literature"|"decision"|"summary"|"question")
            echo "${clean_title}.md"
            ;;
        "idea"|"fleeting")
            echo "idea-${ID}.md"
            ;;
        "meeting")
            echo "meeting-${ID}.md"
            ;;
        "plan")
            echo "plan-${ID}.md"
            ;;
        "review")
            echo "review-${ID}.md"
            ;;
        *)
            echo "note-${ID}.md"
            ;;
    esac
}

FILENAME=$(generate_filename "$TITLE" "$TYPE" "$URL")
FILEPATH="$VAULT/$SAVE_DIR/$FILENAME"

# ===== 生成 frontmatter =====
generate_frontmatter() {
    local type=$1
    local title="$2"
    local url="$3"
    
    case $type in
        "literature")
            cat << EOF
---
title: "$title"
type: literature
date: $DATE
source_url: "$url"
tags: []
---

EOF
            ;;
        "idea")
            cat << EOF
---
title: "$title"
type: idea
date: $DATE
tags: []
---

EOF
            ;;
        "meeting")
            cat << EOF
---
title: "$title"
type: meeting
date: $DATE
participants: []
tags: []
---

EOF
            ;;
        "plan")
            cat << EOF
---
title: "$title"
type: plan
date: $DATE
due: 
tags: []
---

EOF
            ;;
        "review")
            cat << EOF
---
title: "$title"
type: review
date: $DATE
period: 
tags: []
---

EOF
            ;;
        "decision")
            cat << EOF
---
title: "$title"
type: decision
date: $DATE
decision_status: proposed
tags: []
---

EOF
            ;;
        "summary")
            cat << EOF
---
title: "$title"
type: summary
date: $DATE
topics: []
tags: []
---

EOF
            ;;
        "question")
            cat << EOF
---
title: "$title"
type: question
date: $DATE
status: open
tags: []
---

EOF
            ;;
        *)
            cat << EOF
---
title: "$title"
type: fleeting
date: $DATE
tags: []
---

EOF
            ;;
    esac
}

# ===== 处理内容 =====
process_content() {
    local input="$1"
    local type=$2
    
    # 如果有网页内容文件，直接使用
    if [ -n "$WEB_CONTENT_FILE" ] && [ -s "$WEB_CONTENT_FILE" ]; then
        cat "$WEB_CONTENT_FILE"
        return
    fi
    
    # 否则处理原始输入
    # 移除URL（已经在frontmatter中）
    local content=$(echo "$input" | sed -E 's|https?://[^[:space:]]+||g')
    
    # 清理多余空行
    content=$(echo "$content" | sed '/^[[:space:]]*$/N;/^[[:space:]]*\n[[:space:]]*$/D')
    
    echo "$content"
}

PROCESSED_CONTENT=$(process_content "$INPUT" "$TYPE")

# ===== 构建完整笔记内容 =====
{
    generate_frontmatter "$TYPE" "$TITLE" "$URL"
    
    # 根据类型添加标题
    case $TYPE in
        "literature")
            echo "# $TITLE"
            echo ""
            if [ -n "$URL" ]; then
                echo "> 来源: [$URL]($URL)"
                echo ""
            fi
            ;;
        "meeting")
            echo "# 会议记录: $TITLE"
            echo ""
            echo "**时间**: $DATE"
            echo ""
            echo "**参与者**: "
            echo ""
            ;;
        "plan")
            echo "# 计划: $TITLE"
            echo ""
            echo "**创建时间**: $DATE"
            echo ""
            ;;
        "review")
            echo "# 回顾: $TITLE"
            echo ""
            echo "**时间**: $DATE"
            echo ""
            ;;
        "question")
            echo "# 问题: $TITLE"
            echo ""
            echo "**提出时间**: $DATE"
            echo ""
            echo "**状态**: 🟡 待解决"
            echo ""
            ;;
    esac
    
    # 添加内容
    echo "$PROCESSED_CONTENT"
    
    # 根据类型添加尾部
    case $TYPE in
        "literature")
            echo ""
            echo "---"
            echo ""
            echo "## 摘录时间"
            echo ""
            echo "$DATE"
            ;;
        "meeting")
            echo ""
            echo "---"
            echo ""
            echo "## 行动项"
            echo ""
            echo "- [ ] "
            ;;
        "plan")
            echo ""
            echo "---"
            echo ""
            echo "## 进度"
            echo ""
            echo "- [ ] 待开始"
            ;;
        "question")
            echo ""
            echo "---"
            echo ""
            echo "## 思考过程"
            echo ""
            echo "## 可能的答案"
            echo ""
            echo "## 相关资源"
            ;;
    esac
    
} > "$FILEPATH"

# ===== 输出结果 =====
echo ""
if [ "$SCORE" -ge 80 ]; then
    echo "✅ 已保存为 $TYPE 笔记 (置信度: $SCORE%)"
elif [ "$SCORE" -ge 50 ]; then
    echo "✅ 已保存为 $TYPE 笔记 (置信度: $SCORE%)"
    echo ""
    echo "💡 如需调整类型，回复: 改zku(文献)/zki(想法)/zkm(会议)/zkt(计划)"
else
    echo "⚠️  已保存为 $TYPE 笔记 (置信度较低: $SCORE%)"
    echo ""
    echo "💡 建议检查类型是否正确，可回复改zku/zki/zkm/zkt调整"
fi

echo ""
echo "📄 标题: $TITLE"
echo "📁 位置: $SAVE_DIR/$FILENAME"
echo "📅 日期: $DATE"

# 返回JSON结果
echo ""
echo '{"status": "success", "type": "'$TYPE'", "score": '$SCORE', "title": "'$TITLE'", "path": "'$SAVE_DIR/$FILENAME'"}'

# 清理临时文件
rm -f "$WEB_CONTENT_FILE"

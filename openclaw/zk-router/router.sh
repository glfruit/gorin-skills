#!/bin/bash
# ZK Router - 智能路由判断脚本

set -e

INPUT="$1"
SOURCE_CONTEXT="${2:-user}"
VAULT="${HOME}/Workspace/PKM/octopus"
PKM="${HOME}/.openclaw/pkm/pkm"

# 初始化分数
SCORE=0
DETECTED_TYPE="fleeting"
SUBTYPE=""

# 输出到 stderr
debug() {
    echo "$1" >&2
}

debug "=== ZK Router Analysis ==="

# ===== Step 1: URL检测 (+40%) =====
if echo "$INPUT" | grep -qE 'https?://[^[:space:]]+'; then
    URL=$(echo "$INPUT" | grep -oE 'https?://[^[:space:]]+' | head -1)
    SCORE=$((SCORE + 40))
    
    # URL类型细分
    if echo "$URL" | grep -qE '(mp\.weixin\.qq\.com|zhihu\.com|csdn|juejin|medium|dev\.to)'; then
        DETECTED_TYPE="literature"
        SUBTYPE="articles"
        debug "URL: Article site detected (+40)"
    elif echo "$URL" | grep -qE '(arxiv\.org|pdf|researchgate|ieee|acm)'; then
        DETECTED_TYPE="literature"
        SUBTYPE="papers"
        debug "URL: Paper site detected (+40)"
    elif echo "$URL" | grep -qE '(github\.com|gitlab\.com)'; then
        DETECTED_TYPE="literature"
        SUBTYPE="code"
        debug "URL: Code repo detected (+40)"
    else
        DETECTED_TYPE="literature"
        SUBTYPE="articles"
        debug "URL: Generic site (+40)"
    fi
fi

# ===== Step 2: 关键词检测 (+30%) =====
KEYWORD_SCORE=0

# 会议关键词
if echo "$INPUT" | grep -qiE '(会议|讨论|和.*聊|复盘|纪要|与会|参会)'; then
    if [ "$DETECTED_TYPE" = "fleeting" ]; then
        DETECTED_TYPE="meeting"
    fi
    KEYWORD_SCORE=$((KEYWORD_SCORE + 30))
    debug "Keyword: meeting detected (+30)"

# 想法关键词
elif echo "$INPUT" | grep -qiE '(想法|灵感|突然想到|idea|闪念|想到)'; then
    if [ "$DETECTED_TYPE" = "fleeting" ]; then
        DETECTED_TYPE="idea"
    fi
    KEYWORD_SCORE=$((KEYWORD_SCORE + 30))
    debug "Keyword: idea detected (+30)"

# 计划关键词
elif echo "$INPUT" | grep -qiE '(计划|plan|task|待办|TODO|安排)'; then
    if [ "$DETECTED_TYPE" = "fleeting" ]; then
        DETECTED_TYPE="plan"
    fi
    KEYWORD_SCORE=$((KEYWORD_SCORE + 30))
    debug "Keyword: plan detected (+30)"

# 回顾关键词
elif echo "$INPUT" | grep -qiE '(周总结|月回顾|复盘|review|总结)'; then
    if [ "$DETECTED_TYPE" = "fleeting" ]; then
        DETECTED_TYPE="review"
    fi
    KEYWORD_SCORE=$((KEYWORD_SCORE + 30))
    debug "Keyword: review detected (+30)"

# 决策关键词
elif echo "$INPUT" | grep -qiE '(决策|决定|选择|decision|确定)'; then
    if [ "$DETECTED_TYPE" = "fleeting" ]; then
        DETECTED_TYPE="decision"
    fi
    KEYWORD_SCORE=$((KEYWORD_SCORE + 30))
    debug "Keyword: decision detected (+30)"

# 总结关键词
elif echo "$INPUT" | grep -qiE '(总结|摘要|summary|overview|归纳)'; then
    if [ "$DETECTED_TYPE" = "fleeting" ]; then
        DETECTED_TYPE="summary"
    fi
    KEYWORD_SCORE=$((KEYWORD_SCORE + 30))
    debug "Keyword: summary detected (+30)"

# 问题关键词
elif echo "$INPUT" | grep -qiE '(问题|疑问|question|怎么|为什么|如何)'; then
    if [ "$DETECTED_TYPE" = "fleeting" ]; then
        DETECTED_TYPE="question"
    fi
    KEYWORD_SCORE=$((KEYWORD_SCORE + 30))
    debug "Keyword: question detected (+30)"

# 读书关键词
elif echo "$INPUT" | grep -qiE '(读书|看《|读后感|书籍|book)'; then
    if [ "$DETECTED_TYPE" = "fleeting" ]; then
        DETECTED_TYPE="literature"
        SUBTYPE="books"
    fi
    KEYWORD_SCORE=$((KEYWORD_SCORE + 30))
    debug "Keyword: book detected (+30)"
fi

SCORE=$((SCORE + KEYWORD_SCORE))

# ===== Step 3: 内容特征 (+20%) =====
CONTENT_LEN=${#INPUT}

if [ $CONTENT_LEN -gt 1000 ]; then
    SCORE=$((SCORE + 20))
    debug "Feature: Long content +1000 chars (+20)"
    if [ "$DETECTED_TYPE" = "fleeting" ]; then
        DETECTED_TYPE="summary"
    fi
elif [ $CONTENT_LEN -lt 50 ]; then
    debug "Feature: Short content <50 chars"
    if [ "$DETECTED_TYPE" = "fleeting" ]; then
        DETECTED_TYPE="fleeting"
    fi
fi

# 检测结构化内容
if echo "$INPUT" | grep -qE '^[0-9]+\.|^- |^#{1,6} '; then
    SCORE=$((SCORE + 10))
    debug "Feature: Structured content (+10)"
fi

# ===== Step 4: 来源上下文 (+10%) =====
if [ "$SOURCE_CONTEXT" = "daily-collector" ] && [ "$DETECTED_TYPE" = "fleeting" ]; then
    DETECTED_TYPE="literature"
    SUBTYPE="articles"
    SCORE=$((SCORE + 10))
    debug "Context: daily-collector (+10)"
elif [ "$SOURCE_CONTEXT" = "edu-tl" ]; then
    if echo "$INPUT" | grep -qiE '(会议|讨论)'; then
        DETECTED_TYPE="meeting"
        SCORE=$((SCORE + 10))
        debug "Context: edu-tl meeting (+10)"
    fi
fi

# ===== 输出结果 (只输出JSON到stdout) =====
cat << EOF
{
  "type": "$DETECTED_TYPE",
  "subtype": "$SUBTYPE",
  "score": $SCORE,
  "length": $CONTENT_LEN
}
EOF

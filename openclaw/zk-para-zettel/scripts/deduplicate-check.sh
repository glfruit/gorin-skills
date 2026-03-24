#!/bin/bash
# ZK-PARA-Zettel 去重检查脚本
# 使用 ripgrep 检查 Vault 中是否已有相似内容

VAULT_PATH="${OBSIDIAN_VAULT_PATH:-/Users/gorin/Workspace/PKM/octopus}"

# 检查 ripgrep
if ! command -v rg &> /dev/null; then
    echo "❌ 错误: ripgrep 未安装"
    echo "请运行: brew install ripgrep"
    exit 1
fi

# 获取搜索词
QUERY="${1:-}"
if [ -z "$QUERY" ]; then
    echo "用法: $0 <搜索关键词>"
    echo "示例: $0 'OpenClaw best practices'"
    exit 1
fi

echo "🔍 去重检查"
echo "搜索词: $QUERY"
echo "Vault: $VAULT_PATH"
echo "工具: ripgrep"
echo ""

# 搜索路径
SEARCH_PATHS=("Zettels/3-Permanent" "Zettels/4-Structure")

# 执行搜索并统计匹配
MATCH_COUNT=0
MATCHING_FILES=""

for path in "${SEARCH_PATHS[@]}"; do
    FULL_PATH="$VAULT_PATH/$path"
    if [ -d "$FULL_PATH" ]; then
        # 搜索匹配的文件
        FILES=$(rg -i "$QUERY" "$FULL_PATH" --type md -l 2>/dev/null || echo "")
        if [ -n "$FILES" ]; then
            COUNT=$(echo "$FILES" | wc -l | tr -d ' ')
            MATCH_COUNT=$((MATCH_COUNT + COUNT))
            MATCHING_FILES="$MATCHING_FILES$FILES\n"
        fi
    fi
done

# 计算相似度
if [ "$MATCH_COUNT" -eq 0 ]; then
    SIMILARITY="0.0"
elif [ "$MATCH_COUNT" -eq 1 ]; then
    SIMILARITY="0.3"
elif [ "$MATCH_COUNT" -le 3 ]; then
    SIMILARITY="0.6"
else
    SIMILARITY="0.8"
fi

echo "匹配笔记数: $MATCH_COUNT"
echo "相似度: $SIMILARITY"

# 显示匹配文件（最多 5 个）
if [ "$MATCH_COUNT" -gt 0 ]; then
    echo ""
    echo "匹配文件:"
    echo -e "$MATCHING_FILES" | head -5 | sed 's/^/  - /'
    if [ "$MATCH_COUNT" -gt 5 ]; then
        echo "  ... 还有 $((MATCH_COUNT - 5)) 个"
    fi
fi

echo ""

# 根据相似度输出建议
if awk "BEGIN {exit !($SIMILARITY < 0.4)}"; then
    echo "✅ 未发现相似笔记，可以继续创建"
    exit 0
elif awk "BEGIN {exit !($SIMILARITY < 0.7)}"; then
    echo "⚠️ 建议: 发现相似笔记，可选择创建新笔记或查看已有笔记"
    exit 1
else
    echo "🛑 建议: 考虑更新已有笔记而非创建新笔记"
    exit 2
fi

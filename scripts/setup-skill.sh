#!/bin/bash
#
# gorin-skills Skill Setup Script
# 交互式技能创建工具
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_DIR="$PROJECT_ROOT/templates/skill"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Prompt for input
prompt() {
    local prompt_text="$1"
    local default_value="$2"
    local result

    if [ -n "$default_value" ]; then
        read -p "$(echo -e ${BLUE}$prompt_text${NC} [$default_value]): " result
        echo "${result:-$default_value}"
    else
        read -p "$(echo -e ${BLUE}$prompt_text${NC}): " result
        echo "$result"
    fi
}

# Select category
select_category() {
    echo ""
    log_info "选择技能类别:"
    echo "  1) openclaw  - OpenClaw 工具的技能"
    echo "  2) general   - Claude Code、Codex 等其他工具的技能"
    echo ""

    local choice
    read -p "$(echo -e ${BLUE}请选择 [1-2]:${NC}) " choice

    case $choice in
        1) echo "openclaw" ;;
        2) echo "general" ;;
        *) log_error "无效选择"; exit 1 ;;
    esac
}

# Main function
main() {
    echo ""
    echo "=========================================="
    echo "  gorin-skills 技能创建向导"
    echo "=========================================="
    echo ""

    # Gather information
    local skill_name
    local category
    local description
    local emoji
    local target_tool
    local author
    local license

    skill_name=$(prompt "技能名称" "my-skill")
    category=$(select_category)
    description=$(prompt "简短描述" "A awesome skill")
    emoji=$(prompt "表情符号" "✨")
    author=$(prompt "作者" "$(git config user.name 2>/dev/null || echo 'Your Name')")
    license=$(prompt "许可证" "MIT")

    # Set target tool based on category
    if [ "$category" = "openclaw" ]; then
        target_tool="OpenClaw"
    else
        target_tool=$(prompt "目标工具" "Claude Code")
    fi

    # Create skill directory
    local skill_dir="$PROJECT_ROOT/$category/$skill_name"
    if [ -d "$skill_dir" ]; then
        log_error "目录已存在: $skill_dir"
        exit 1
    fi

    log_info "创建技能目录: $skill_dir"
    mkdir -p "$skill_dir"

    # Copy template files
    log_info "复制模板文件..."
    for file in README.md SKILL.md install.sh .gitignore LICENSE; do
        if [ -f "$TEMPLATE_DIR/$file" ]; then
            cp "$TEMPLATE_DIR/$file" "$skill_dir/$file"
        fi
    done

    # Replace placeholders
    log_info "替换占位符..."
    local placeholders=(
        "SKILL_NAME=$skill_name"
        "SKILL_DESCRIPTION=$description"
        "SKILL_EMOJI=$emoji"
        "TARGET_TOOL=$target_tool"
        "TOOL_TYPE=$(echo $category | tr '[:lower:]' '[:upper:]')"
        "HOMEPAGE=https://github.com/glfruit/gorin-skills"
        "VERSION=0.1.0"
        "STATUS=beta"
        "MAINTAINER=$author"
        "LICENSE_TYPE=$license"
        "INSTALL_DIR=~/.local/bin"
        "OS=darwin"
        "OS_CHECK=darwin"
        "INSTALL_ID=${skill_name}-cli"
        "INSTALL_KIND=download"
        "INSTALL_URL="
        "EXTRACT=false"
        "TARGET_DIR=~/.local/bin"
        "BINARIES=${skill_name}.py"
        "INSTALL_LABEL=Install ${skill_name}"
    )

    # Simple replacement (could use sed for better patterns)
    for placeholder in "${placeholders[@]}"; do
        local key="${placeholder%%=*}"
        local value="${placeholder#*=}"
        find "$skill_dir" -type f -exec sed -i '' "s|{{$key}}|$value|g" {} \;
    done

    # Make install.sh executable
    chmod +x "$skill_dir/install.sh"

    # Create basic skill script placeholder
    cat > "$skill_dir/${skill_name}.py" << 'EOF'
#!/usr/bin/env python3
"""
{{SKILL_NAME}} - {{SKILL_DESCRIPTION}}
"""

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="{{SKILL_DESCRIPTION}}")
    parser.add_argument('--version', action='version', version='{{VERSION}}')

    args = parser.parse_args()

    # TODO: Implement your skill here
    print("{{SKILL_NAME}} is ready!")

if __name__ == '__main__':
    main()
EOF

    # Replace placeholders in skill script too
    for placeholder in "${placeholders[@]}"; do
        local key="${placeholder%%=*}"
        local value="${placeholder#*=}"
        sed -i '' "s|{{$key}}|$value|g" "$skill_dir/${skill_name}.py"
    done

    chmod +x "$skill_dir/${skill_name}.py"

    # Print summary
    echo ""
    log_info "技能创建完成！"
    echo ""
    echo "位置: $skill_dir"
    echo ""
    echo "包含文件:"
    echo "  - README.md        用户文档"
    echo "  - SKILL.md         技能元数据"
    echo "  - install.sh       安装脚本"
    echo "  - ${skill_name}.py   主程序"
    echo "  - LICENSE          许可证"
    echo ""
    log_warn "下一步:"
    echo "  1. 编辑 $skill_dir/${skill_name}.py 实现技能功能"
    echo "  2. 更新 $skill_dir/README.md 添加使用说明"
    echo "  3. 更新 $skill_dir/SKILL.md 完善元数据"
    echo "  4. 运行 ./scripts/validate-skill.sh $category/$skill_name 验证"
    echo "  5. 提交 Pull Request"
    echo ""
}

main "$@"

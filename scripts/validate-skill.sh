#!/bin/bash
#
# gorin-skills Skill Validation Script
# 验证技能结构是否符合要求
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Counters
errors=0
warnings=0
checks=0

log_info() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((checks++))
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
    ((warnings++))
    ((checks++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((errors++))
    ((checks++))
}

log_check() {
    echo -e "${BLUE}[?]${NC} $1"
}

# Check if skill directory exists
check_skill_dir() {
    local skill_path="$1"

    if [ ! -d "$skill_path" ]; then
        log_error "技能目录不存在: $skill_path"
        exit 1
    fi

    log_info "技能目录存在: $skill_path"
}

# Check required files
check_required_files() {
    local skill_path="$1"

    log_check "检查必需文件..."

    local required_files=("README.md" "SKILL.md" "LICENSE")
    local missing_files=()

    for file in "${required_files[@]}"; do
        if [ ! -f "$skill_path/$file" ]; then
            missing_files+=("$file")
        fi
    done

    if [ ${#missing_files[@]} -gt 0 ]; then
        for file in "${missing_files[@]}"; do
            log_error "缺少必需文件: $file"
        done
    else
        log_info "所有必需文件存在"
    fi
}

# Check SKILL.md frontmatter
check_skill_frontmatter() {
    local skill_path="$1"
    local skill_md="$skill_path/SKILL.md"

    if [ ! -f "$skill_md" ]; then
        return
    fi

    log_check "检查 SKILL.md frontmatter..."

    # Check if file starts with ---
    if ! head -n 1 "$skill_md" | grep -q '^---$'; then
        log_error "SKILL.md 必须以 YAML frontmatter 开头 (---)"
        return
    fi

    # Check for required fields
    local required_fields=("name" "description" "homepage")
    local missing_fields=()

    for field in "${required_fields[@]}"; do
        if ! grep -q "^${field}:" "$skill_md"; then
            missing_fields+=("$field")
        fi
    done

    if [ ${#missing_fields[@]} -gt 0 ]; then
        for field in "${missing_fields[@]}"; do
            log_error "SKILL.md 缺少必需字段: $field"
        done
    else
        log_info "SKILL.md frontmatter 有效"
    fi
}

# Check install.sh
check_install_script() {
    local skill_path="$1"
    local install_sh="$skill_path/install.sh"

    if [ ! -f "$install_sh" ]; then
        log_warn "未找到 install.sh（推荐但非必需）"
        return
    fi

    log_check "检查 install.sh..."

    if [ ! -x "$install_sh" ]; then
        log_error "install.sh 没有执行权限"
    else
        log_info "install.sh 有执行权限"
    fi

    # Check for shebang
    if ! head -n 1 "$install_sh" | grep -q '^#!'; then
        log_error "install.sh 缺少 shebang"
    else
        log_info "install.sh 有有效的 shebang"
    fi
}

# Check for common issues
check_common_issues() {
    local skill_path="$1"

    log_check "检查常见问题..."

    # Check for trailing whitespace
    if grep -q ' $' "$skill_path"/*.md 2>/dev/null; then
        log_warn "发现行尾空白字符"
    else
        log_info "未发现行尾空白字符"
    fi

    # Check for TODO/FIXME comments
    if grep -r -i 'todo\|fixme' "$skill_path"/*.md "$skill_path"/*.py 2>/dev/null | grep -q .; then
        log_warn "发现 TODO/FIXME 注释"
    else
        log_info "未发现 TODO/FIXME 注释"
    fi

    # Check for placeholder values
    if grep -r '{{' "$skill_path"/*.md 2>/dev/null | grep -q .; then
        log_error "发现未替换的模板占位符 {{}}"
    else
        log_info "未发现模板占位符"
    fi
}

# Main validation
main() {
    local skill_path="$1"

    if [ -z "$skill_path" ]; then
        echo "用法: $0 <skill-path>"
        echo "示例: $0 openclaw/neobear"
        exit 1
    fi

    # Resolve full path
    if [[ ! "$skill_path" = /* ]]; then
        skill_path="$PROJECT_ROOT/$skill_path"
    fi

    echo ""
    echo "=========================================="
    echo "  gorin-skills 技能验证"
    echo "=========================================="
    echo ""
    echo "验证路径: $skill_path"
    echo ""

    # Run checks
    check_skill_dir "$skill_path"
    check_required_files "$skill_path"
    check_skill_frontmatter "$skill_path"
    check_install_script "$skill_path"
    check_common_issues "$skill_path"

    # Print summary
    echo ""
    echo "=========================================="
    echo "  验证摘要"
    echo "=========================================="
    echo ""
    echo "总检查数: $checks"
    echo -e "${GREEN}通过: $((checks - errors - warnings))${NC}"
    [ $warnings -gt 0 ] && echo -e "${YELLOW}警告: $warnings${NC}"
    [ $errors -gt 0 ] && echo -e "${RED}错误: $errors${NC}"
    echo ""

    if [ $errors -gt 0 ]; then
        log_error "验证失败，请修复错误后重试"
        exit 1
    elif [ $warnings -gt 0 ]; then
        log_warn "验证通过，但有警告"
        exit 0
    else
        log_info "验证通过！"
        exit 0
    fi
}

main "$@"

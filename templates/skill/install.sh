#!/bin/bash
#
# {{SKILL_NAME}} Installation Script
# Version: {{VERSION}}
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SKILL_NAME="{{SKILL_NAME}}"
VERSION="{{VERSION}}"
INSTALL_DIR="{{INSTALL_DIR}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "检查前置条件..."

    # Check if running on supported OS
    if [[ "{{OS_CHECK}}" == "darwin" ]] && [[ "$OSTYPE" != "darwin"* ]]; then
        log_error "此技能仅支持 macOS"
        exit 1
    fi

    # Check required binaries
    {{PREREQUISITE_CHECKS}}

    log_info "前置条件检查通过"
}

# Create install directory
create_install_dir() {
    log_info "创建安装目录: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
}

# Install files
install_files() {
    log_info "安装文件..."

    {{INSTALL_COMMANDS}}

    log_info "文件安装完成"
}

# Set permissions
set_permissions() {
    log_info "设置文件权限..."

    {{PERMISSION_COMMANDS}}

    log_info "权限设置完成"
}

# Print post-install message
post_install_message() {
    echo ""
    log_info "{{SKILL_NAME}} 安装完成！"
    echo ""
    echo "下一步:"
    echo "  1. 重启 {{TOOL_TYPE}}"
    echo "  2. 检查技能是否可用"
    echo ""
    echo "如需帮助，请访问: {{HELP_URL}}"
    echo ""
}

# Main installation
main() {
    echo "{{SKILL_NAME}} v${VERSION} 安装程序"
    echo "================================"
    echo ""

    check_prerequisites
    create_install_dir
    install_files
    set_permissions
    post_install_message
}

# Run main function
main "$@"

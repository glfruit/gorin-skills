#!/bin/bash
# install.sh - Install BearClaw Native to OpenClaw

set -e

echo ""
echo "═══════════════════════════════════════════════"
echo "🐻🦞 BearClaw Native - OpenClaw Browser Edition"
echo "═══════════════════════════════════════════════"
echo ""
echo "Installing BearClaw Native to OpenClaw..."
echo ""

# Check for required files
if [[ ! -f "SKILL.md" ]] || [[ ! -f "bearclaw-native.js" ]]; then
    echo "❌ Error: SKILL.md or bearclaw-native.js not found"
    echo "Please run this script from the bearclaw-native directory"
    exit 1
fi

# Determine installation path
DEFAULT_PATH="$HOME/.openclaw/skills/bearclaw-native"
echo "Installation path: $DEFAULT_PATH"
read -p "Use this path? (y/n, default: y): " use_default
use_default=${use_default:-y}

if [[ "$use_default" == "n" || "$use_default" == "N" ]]; then
    read -p "Enter custom path: " INSTALL_PATH
    INSTALL_PATH="${INSTALL_PATH/#\~/$HOME}"
else
    INSTALL_PATH="$DEFAULT_PATH"
fi

echo ""
echo "📁 Creating directory: $INSTALL_PATH"
mkdir -p "$INSTALL_PATH"

echo "📄 Copying SKILL.md..."
cp SKILL.md "$INSTALL_PATH/"

echo "📄 Copying bearclaw-native.js..."
cp bearclaw-native.js "$INSTALL_PATH/"

echo ""
echo "✅ BearClaw Native installed successfully!"
echo ""
echo "═══════════════════════════════════════════════"
echo "🔧 Browser Setup"
echo "═══════════════════════════════════════════════"
echo ""

# Check if openclaw command exists
if ! command -v openclaw &> /dev/null; then
    echo "⚠️  OpenClaw command not found"
    echo "Please ensure OpenClaw is properly installed"
    echo ""
else
    # Check browser status
    echo "Checking browser status..."
    if openclaw browser status &> /dev/null; then
        echo "✅ Browser is enabled and running"
    else
        echo "⚠️  Browser may not be enabled"
        echo ""
        echo "To enable browser:"
        echo "  openclaw config set browser.enabled true"
        echo "  openclaw restart"
        echo ""
    fi
fi

echo "═══════════════════════════════════════════════"
echo "📚 Next Steps"
echo "═══════════════════════════════════════════════"
echo ""
echo "1. Ensure browser is enabled:"
echo "   openclaw config set browser.enabled true"
echo "   openclaw browser start"
echo ""
echo "2. Restart OpenClaw (if running):"
echo "   openclaw restart"
echo ""
echo "3. Login to Bear Blog in OpenClaw browser:"
echo "   openclaw browser open https://bearblog.dev"
echo "   # Log in manually in the browser window"
echo ""
echo "4. (Optional) Configure environment variables:"
echo "   export BEARCLAW_TIMEOUT=30000"
echo "   export BEARCLAW_DEBUG=true"
echo "   export BEARCLAW_MAX_RETRIES=3"
echo ""
echo "5. Test BearClaw Native:"
echo '   Say: "Create a Bear Blog post titled Test"'
echo ""
echo "═══════════════════════════════════════════════"
echo "🐛 Troubleshooting"
echo "═══════════════════════════════════════════════"
echo ""
echo "Check browser status:"
echo "  openclaw browser status"
echo ""
echo "Test browser manually:"
echo "  openclaw browser open https://bearblog.dev"
echo "  openclaw browser snapshot"
echo ""
echo "Enable debug mode:"
echo "  export BEARCLAW_DEBUG=true"
echo ""
echo "View screenshots:"
echo "  ls -lt /tmp/bearclaw-*.png"
echo ""
echo "═══════════════════════════════════════════════"
echo ""
echo "🎉 Installation complete!"
echo ""
echo "BearClaw Native is ready with OpenClaw's native browser! 🐻🦞"
echo ""

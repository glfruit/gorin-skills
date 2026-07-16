#!/bin/bash
# install.sh - Install NeoBear OpenClaw Skill

set -e

echo ""
echo "═══════════════════════════════════════════════"
echo "🐻💫 NeoBear - OpenClaw Skill Installation"
echo "═══════════════════════════════════════════════"
echo ""

# Check for required files
if [[ ! -f "SKILL.md" ]] || [[ ! -f "neobear_cli.py" ]]; then
    echo "❌ Error: SKILL.md or neobear_cli.py not found"
    echo "Please run this script from the neobear directory"
    exit 1
fi

# Check if running on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "⚠️  Warning: NeoBear requires macOS and the Bear app"
    read -p "Continue anyway? (y/n): " continue
    if [[ "$continue" != "y" ]]; then
        exit 0
    fi
fi

# Install to OpenClaw skills directory
SKILLS_DIR="$HOME/.openclaw/skills/neobear"

echo "📁 Installing to: $SKILLS_DIR"
mkdir -p "$SKILLS_DIR"

echo "📄 Copying SKILL.md..."
cp SKILL.md "$SKILLS_DIR/"

echo "📄 Copying neobear_cli.py..."
cp neobear_cli.py "$SKILLS_DIR/"

# Also install CLI to ~/.local/bin
BIN_DIR="$HOME/.local/bin"
echo ""
echo "📦 Installing CLI to: $BIN_DIR"
mkdir -p "$BIN_DIR"
cp neobear_cli.py "$BIN_DIR/"
chmod +x "$BIN_DIR/neobear_cli.py"

echo ""
echo "✅ NeoBear installed successfully!"
echo ""
echo "═══════════════════════════════════════════════"
echo "📋 Next Steps"
echo "═══════════════════════════════════════════════"
echo ""
echo "1. Ensure ~/.local/bin is in your PATH:"
echo "   echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc"
echo "   source ~/.zshrc"
echo ""
echo "2. Get Bear API token (optional, for some operations):"
echo "   Bear → Help → API Token → Copy"
echo "   mkdir -p ~/.config/bear"
echo "   echo \"YOUR_TOKEN\" > ~/.config/bear/token"
echo ""
echo "3. Restart OpenClaw:"
echo "   openclaw restart"
echo ""
echo "4. Test the CLI:"
echo "   neobear_cli.py --version"
echo ""
echo "5. Use in OpenClaw:"
echo "   Say: \"Create a Bear note titled Test\""
echo ""
echo "═══════════════════════════════════════════════"
echo ""
echo "🎉 Installation complete!"
echo ""
echo "\"Where old Bear links become new again.\" 🐻💫"
echo ""

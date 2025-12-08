#!/bin/bash
# Code Whisperers - Quick Install Script
# Usage: curl -fsSL https://raw.githubusercontent.com/sethjchalmers/code-whisperers/master/scripts/install.sh | bash

set -e

echo "🎭 Installing Code Whisperers..."

# Check for Python 3.10+
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ $(echo "$PYTHON_VERSION < 3.10" | bc -l) -eq 1 ]]; then
    echo "❌ Python 3.10+ is required (found $PYTHON_VERSION)"
    exit 1
fi

# Determine install location
INSTALL_DIR="${HOME}/.code-whisperers"

# Clone or update repository
if [ -d "$INSTALL_DIR" ]; then
    echo "📦 Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull --quiet
else
    echo "📦 Cloning repository..."
    git clone --quiet https://github.com/sethjchalmers/code-whisperers.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Create virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --quiet --upgrade pip
pip install --quiet -e .

# Create wrapper script
WRAPPER_SCRIPT="${HOME}/.local/bin/code-whisperers"
mkdir -p "${HOME}/.local/bin"

cat > "$WRAPPER_SCRIPT" << 'EOF'
#!/bin/bash
source "${HOME}/.code-whisperers/.venv/bin/activate"
python -m cli.main "$@"
EOF

chmod +x "$WRAPPER_SCRIPT"

echo ""
echo "✅ Code Whisperers installed successfully!"
echo ""
echo "🚀 Quick Start:"
echo "   code-whisperers review --diff HEAD~1  # Review last commit"
echo "   code-whisperers review --base main     # Review changes vs main"
echo "   code-whisperers review --help          # Show all options"
echo ""
echo "🔑 Set your GitHub token for free AI access:"
echo "   export GITHUB_TOKEN=ghp_your_token_here"
echo ""
echo "📝 Add to your shell profile (~/.bashrc or ~/.zshrc):"
echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
echo "   export GITHUB_TOKEN=ghp_your_token_here"

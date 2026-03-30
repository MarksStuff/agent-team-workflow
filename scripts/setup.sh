#!/usr/bin/env bash
# Idempotent dev environment setup for agent-team-workflow.
# Safe to re-run at any time.
set -euo pipefail

REQUIRED_PYTHON="3.11"

echo "🚀 Setting up agent-team-workflow dev environment..."

# ── Sanity checks ────────────────────────────────────────────────────────────
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Run this script from the project root."
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "❌ python3 not found. Install Python $REQUIRED_PYTHON+ first."
    exit 1
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"; then
    echo "✅ Python $PYTHON_VER"
else
    echo "❌ Python $REQUIRED_PYTHON+ required (found $PYTHON_VER)."
    exit 1
fi

if ! command -v claude &>/dev/null; then
    echo "⚠️  claude CLI not found — agent execution will not work."
    echo "   Install from: https://github.com/anthropics/claude-code"
else
    echo "✅ claude CLI: $(claude --version 2>/dev/null | head -1)"
fi

# ── GitHub CLI (gh) ────────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
    echo "⚠️  Homebrew not found. Please install Homebrew to install the gh CLI (https://brew.sh)"
    echo "   PR integration will not work without the gh CLI."
elif ! command -v gh &>/dev/null; then
    echo "🔧 Installing gh CLI using Homebrew..."
    brew install gh
    echo "✅ gh CLI installed"
fi

if ! command -v gh &>/dev/null; then
    echo "⚠️  gh CLI not found — PR integration will not work."
    echo "   Install from: https://cli.github.com"
else
    echo "✅ gh CLI: $(gh --version | head -1)"
fi

# ── Virtual environment ───────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
else
    echo "✅ Virtual environment already exists"
fi

source .venv/bin/activate

echo "📦 Upgrading pip..."
pip install --upgrade pip --quiet

echo "📦 Installing dependencies (including dev extras)..."
pip install -e ".[dev]" --quiet

echo "✅ Dependencies installed"

# ── Pre-commit hook (blocks commits on lint/test failure + blocks main) ───────
HOOK_PATH=".git/hooks/pre-commit"
EXPECTED_SCRIPT="scripts/pre-commit.sh"

if [ ! -f ".git/hooks/pre-commit" ] || ! grep -q "$EXPECTED_SCRIPT" ".git/hooks/pre-commit" 2>/dev/null; then
    echo "🔧 Installing pre-commit hook..."
    cat > "$HOOK_PATH" <<'HOOK'
#!/usr/bin/env bash
exec "$(git rev-parse --show-toplevel)/scripts/pre-commit.sh"
HOOK
    chmod +x "$HOOK_PATH"
    echo "✅ Pre-commit hook installed"
else
    echo "✅ Pre-commit hook already installed"
fi

# ── Pre-push hook (blocks pushes directly to main) ───────────────────────────
PUSH_HOOK=".git/hooks/pre-push"
if [ ! -f "$PUSH_HOOK" ] || ! grep -q "pre-push.sh" "$PUSH_HOOK" 2>/dev/null; then
    echo "🔧 Installing pre-push hook..."
    cat > "$PUSH_HOOK" <<'HOOK'
#!/usr/bin/env bash
exec "$(git rev-parse --show-toplevel)/scripts/pre-push.sh"
HOOK
    chmod +x "$PUSH_HOOK"
    echo "✅ Pre-push hook installed"
else
    echo "✅ Pre-push hook already installed"
fi

# ── CLAUDE.md symlink (global master in agent-instructions/) ─────────────────
CLAUDE_SOURCE="agent-instructions/CLAUDE.md"
CLAUDE_LINK="CLAUDE.md"

if [ -L "$CLAUDE_LINK" ] && [ "$(readlink "$CLAUDE_LINK")" = "$CLAUDE_SOURCE" ]; then
    echo "✅ CLAUDE.md symlink already correct"
elif [ -e "$CLAUDE_LINK" ] && [ ! -L "$CLAUDE_LINK" ]; then
    echo "⚠️  CLAUDE.md exists but is not a symlink — leaving it alone."
    echo "   To use the canonical version: rm CLAUDE.md && ln -s $CLAUDE_SOURCE $CLAUDE_LINK"
else
    ln -sf "$CLAUDE_SOURCE" "$CLAUDE_LINK"
    echo "✅ CLAUDE.md → $CLAUDE_SOURCE symlink created"
fi

# ── Git identity (Roxy's account) ────────────────────────────────────────────
ROXY_EMAIL="269813048+roxy-mstriebeck@users.noreply.github.com"
CURRENT_EMAIL=$(git config user.email 2>/dev/null || echo "")
if [ "$CURRENT_EMAIL" != "$ROXY_EMAIL" ]; then
    echo "🔧 Setting git commit identity to Roxy..."
    git config user.name "Roxy"
    git config user.email "$ROXY_EMAIL"
    echo "✅ Git identity: Roxy <$ROXY_EMAIL>"
else
    echo "✅ Git identity already set to Roxy"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Activate the venv:  source .venv/bin/activate"
echo "Run lint:           scripts/lint.sh"
echo "Run tests:          scripts/test.sh"
echo "Fix auto-fixables:  scripts/autofix.sh"

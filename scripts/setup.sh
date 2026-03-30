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

# ── Global ~/.claude/CLAUDE.md symlink ───────────────────────────────────────
# Points to agent-instructions/CLAUDE.md in this repo so global Claude Code
# guidelines are version-controlled here and applied to all sessions.
GLOBAL_CLAUDE_SOURCE="$(pwd)/agent-instructions/CLAUDE.md"
GLOBAL_CLAUDE_LINK="$HOME/.claude/CLAUDE.md"

mkdir -p "$HOME/.claude"

if [ -L "$GLOBAL_CLAUDE_LINK" ] && [ "$(readlink "$GLOBAL_CLAUDE_LINK")" = "$GLOBAL_CLAUDE_SOURCE" ]; then
    echo "✅ ~/.claude/CLAUDE.md symlink already correct"
elif [ -e "$GLOBAL_CLAUDE_LINK" ] && [ ! -L "$GLOBAL_CLAUDE_LINK" ]; then
    echo "⚠️  ~/.claude/CLAUDE.md exists but is not a symlink — leaving it alone."
    echo "   To replace with the canonical version:"
    echo "     rm ~/.claude/CLAUDE.md && ln -s $GLOBAL_CLAUDE_SOURCE $GLOBAL_CLAUDE_LINK"
else
    ln -sf "$GLOBAL_CLAUDE_SOURCE" "$GLOBAL_CLAUDE_LINK"
    echo "✅ ~/.claude/CLAUDE.md → $GLOBAL_CLAUDE_SOURCE"
fi

# ── Global ~/.claude/agents/ symlinks ──────────────────────────────────────
# Symlinks all agent definition files from agent-definitions/ in this repo
# to ~/.claude/agents/ so Claude Code can load them automatically.
AGENT_DEFINITIONS_DIR="$(pwd)/agent-definitions"
GLOBAL_AGENTS_DIR="$HOME/.claude/agents"

mkdir -p "$GLOBAL_AGENTS_DIR"

for agent_file in "$AGENT_DEFINITIONS_DIR"/*.md; do
    if [ -f "$agent_file" ]; then
        agent_name=$(basename "$agent_file")
        GLOBAL_AGENT_LINK="$GLOBAL_AGENTS_DIR/$agent_name"
        if [ -L "$GLOBAL_AGENT_LINK" ] && [ "$(readlink "$GLOBAL_AGENT_LINK")" = "$agent_file" ]; then
            echo "✅ ~/.claude/agents/$agent_name symlink already correct"
        elif [ -e "$GLOBAL_AGENT_LINK" ] && [ ! -L "$GLOBAL_AGENT_LINK" ]; then
            echo "⚠️  ~/.claude/agents/$agent_name exists but is not a symlink — leaving it alone."
            echo "   To replace with the canonical version:"
            echo "     rm ~/.claude/agents/$agent_name && ln -s $agent_file $GLOBAL_AGENT_LINK"
        else
            ln -sf "$agent_file" "$GLOBAL_AGENT_LINK"
            echo "✅ ~/.claude/agents/$agent_name → $agent_file"
        fi
    fi
done

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

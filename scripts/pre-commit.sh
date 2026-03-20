#!/usr/bin/env bash
# Pre-commit hook: autofix → lint → test.
# Installed by scripts/setup.sh into .git/hooks/pre-commit.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# ── Block direct commits to main ─────────────────────────────────────────────
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")
if [ "$BRANCH" = "main" ]; then
    echo ""
    echo "❌ Direct commits to 'main' are not allowed."
    echo "   Create a branch, open a PR, and let CI validate it."
    echo ""
    exit 1
fi

[ -d ".venv" ] && source .venv/bin/activate

run() {
    local name="$1"
    echo ""
    echo "▶ $name..."
    echo "────────────────────────────────"
    if ! "$ROOT/scripts/${name}.sh"; then
        echo ""
        echo "❌ $name failed — fix the issues above and re-commit."
        exit 1
    fi
    echo "✅ $name passed"
}

echo "🚀 Pre-commit checks..."

# Step 1: autofix (may stage more changes)
run "autofix"
if ! git diff --quiet; then
    echo "📝 Staging autofix changes..."
    git add .
fi

# Step 2: strict lint + type check
run "lint"

# Step 3: tests
run "test"

echo ""
echo "🎉 All pre-commit checks passed — proceeding with commit."

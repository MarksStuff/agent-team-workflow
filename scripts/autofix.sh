#!/usr/bin/env bash
# Auto-fix what ruff can fix automatically. Does not fail on remaining issues.
set -euo pipefail

if [ ! -f "pyproject.toml" ]; then
    echo "❌ Run from the project root."
    exit 1
fi

[ -d ".venv" ] && source .venv/bin/activate

echo "🔧 Running ruff autofix..."
ruff check --fix --exit-zero .
ruff format .

echo "✅ Autofix complete. Run scripts/lint.sh to check for remaining issues."

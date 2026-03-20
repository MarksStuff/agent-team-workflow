#!/usr/bin/env bash
# Run ruff (check + format) and mypy. Fails on any issue.
set -euo pipefail

if [ ! -f "pyproject.toml" ]; then
    echo "❌ Run from the project root."
    exit 1
fi

[ -d ".venv" ] && source .venv/bin/activate

echo "🔍 Lint & type-check..."
echo "  ruff:  $(ruff --version)"
echo "  mypy:  $(mypy --version)"
echo ""

echo "▶ ruff check..."
ruff check .

echo "▶ ruff format --check..."
ruff format --check .

echo "▶ mypy..."
mypy agent_design/

echo ""
echo "✅ All lint and type checks passed!"

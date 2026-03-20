#!/usr/bin/env bash
# Run the full test suite. Fails if any test fails or suite exceeds 120s.
set -euo pipefail

if [ ! -f "pyproject.toml" ]; then
    echo "❌ Run from the project root."
    exit 1
fi

[ -d ".venv" ] && source .venv/bin/activate

echo "🧪 Running tests..."
START=$(date +%s)

pytest tests/

END=$(date +%s)
DURATION=$((END - START))

if [ $DURATION -gt 120 ]; then
    echo "❌ Test suite took ${DURATION}s — exceeds the 120s limit!"
    exit 1
fi

echo ""
echo "✅ All tests passed in ${DURATION}s!"

#!/usr/bin/env bash
# Exit-2 hook: gates "implement*" and "fix*" tasks behind test suite.
# Claude Code calls this as a PreToolUse hook on TaskUpdate.
# Tool input JSON arrives on stdin. TEST_CMD and REPO_PATH are in env.
set -euo pipefail
INPUT=$(cat)
TASK_TITLE=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('subject',''))" 2>/dev/null || echo "")
if [[ "$TASK_TITLE" == *"implement"* || "$TASK_TITLE" == *"fix"* ]]; then
    cd "$REPO_PATH"
    if ! eval "$TEST_CMD"; then
        echo "Tests are failing. Fix before marking done." >&2
        exit 2
    fi
fi

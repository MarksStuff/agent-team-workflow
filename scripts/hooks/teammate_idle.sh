#!/usr/bin/env bash
# Stop hook: nudges agents to update TASKS.md before going idle.
set -euo pipefail
TASKS_FILE="${REPO_PATH}/TASKS.md"
if [ -f "$TASKS_FILE" ]; then
    if grep -q "🔄 in progress" "$TASKS_FILE"; then
        echo "You have in-progress tasks. Update TASKS.md status before going idle." >&2
    fi
fi

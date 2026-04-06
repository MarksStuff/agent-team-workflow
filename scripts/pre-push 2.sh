#!/usr/bin/env bash
# Pre-push hook: blocks pushes directly to main.
# Installed by scripts/setup.sh into .git/hooks/pre-push.
set -euo pipefail

while read -r local_ref local_sha remote_ref remote_sha; do
    if [[ "$remote_ref" == "refs/heads/main" ]]; then
        echo ""
        echo "❌ Direct pushes to 'main' are not allowed."
        echo "   Open a PR and let it merge through GitHub."
        echo ""
        exit 1
    fi
done

exit 0

#!/usr/bin/env bash
# Native git pre-commit hook to block commits with unstaged changes
# This runs BEFORE pre-commit framework stashes unstaged files

set -euo pipefail

# Check for unstaged changes (excluding untracked files)
if ! git diff --quiet; then
    echo "BLOCKED: Unstaged changes detected. Run 'git add -A' before commit."
    echo ""
    echo "Unstaged files:"
    git diff --name-only
    exit 1
fi

exit 0

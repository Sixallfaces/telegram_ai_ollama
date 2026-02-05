#!/usr/bin/env bash
set -e

# Safety: require clean working tree
if [ -n "$(git status --porcelain)" ]; then
  echo "⚠️ You have local changes. Commit or stash them before running this script."
  echo "If you want to force update, run: git fetch origin && git reset --hard origin/main"
  exit 1
fi

# Ensure we're on main
git checkout main

# Fetch and hard-reset to remote main
git fetch origin
git reset --hard origin/main

# Update submodules if any
git submodule update --init --recursive || true

# Optional: run project-specific post-update steps (uncomment if needed)
# echo "Running post-update steps..."
# ./scripts/restart.sh || true

echo "✅ Updated to $(git rev-parse --abbrev-ref HEAD) $(git rev-parse --short HEAD)"
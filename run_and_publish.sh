#!/bin/bash
set -e

REPO_DIR="/Users/sukanto/Desktop/CS50/Reddit-Daily"
PYTHON_BIN="/Users/sukanto/Desktop/CS50/venv/bin/python"
BRANCH="main"   # change if your main branch is named differently

cd "$REPO_DIR"

echo "[INFO] Running reddit-daily.py..."
"$PYTHON_BIN" reddit-daily.py

echo "[INFO] Updating git repo..."

# Stage only the things this pipeline touches
git add docs social reddit-daily.py

# If nothing staged, skip commit + push
if git diff --cached --quiet; then
    echo "[INFO] No changes to commit. Skipping git commit/push."
    exit 0
fi

COMMIT_MSG="Auto update: $(date +'%Y-%m-%d %H:%M')"

git commit -m "$COMMIT_MSG"
echo "[OK] Committed with message: $COMMIT_MSG"

git push origin "$BRANCH"
echo "[OK] Pushed to origin/$BRANCH"
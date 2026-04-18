#!/bin/bash
set -euo pipefail

ROOT="/home/sithmm2_admin/grants-system"
cd "$ROOT"

if [ $# -lt 1 ]; then
    echo "Usage: scripts/commit-and-push.sh \"commit message\""
    exit 1
fi

message="$1"
branch="$(git branch --show-current)"

if [ -z "$branch" ]; then
    echo "No current branch found."
    exit 1
fi

if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
    echo "Refusing to commit and push directly from $branch."
    echo "Create a feature branch first."
    exit 1
fi

echo "Branch: $branch"
git status -sb

python3 -m unittest discover -s tests
python3 -m py_compile \
    hermes-tasks/telegram-bot.py \
    hermes-tasks/telegram-handlers.py \
    tests/test_telegram_bot.py
git diff --check

git add \
    .env.example \
    .gitignore \
    DEVELOPER_GUIDE.md \
    IMPLEMENTATION_PLAN.md \
    README.md \
    USER_GUIDE.md \
    configs \
    dashboard.html \
    data \
    hermes-tasks \
    outputs \
    reports \
    run-all.py \
    scripts \
    start-services.sh \
    tests

if git diff --cached --quiet; then
    echo "No staged changes to commit."
else
    git diff --cached --stat
    git commit -m "$message"
fi

git push -u origin "$branch"

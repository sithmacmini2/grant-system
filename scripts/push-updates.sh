#!/bin/bash
set -euo pipefail

ROOT="/home/sithmm2_admin/grants-system"
cd "$ROOT"

branch="$(git branch --show-current)"

if [ -z "$branch" ]; then
    echo "No current branch found."
    exit 1
fi

echo "Branch: $branch"
git status -sb

if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
    echo "Refusing to push directly from $branch."
    echo "Create a feature branch first."
    exit 1
fi

python3 -m unittest discover -s tests
python3 -m py_compile \
    hermes-tasks/telegram-bot.py \
    hermes-tasks/telegram-handlers.py \
    tests/test_telegram_bot.py
git diff --check

git push -u origin "$branch"

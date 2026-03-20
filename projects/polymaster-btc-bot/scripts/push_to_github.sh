#!/bin/bash
set -e

cd /Users/stevenwang/.openclaw/workspace/projects/polymaster-btc-bot

echo "🚀 Polymaster BTC Bot - Push to GitHub"
echo "======================================"
echo ""

# Configure git user
git config --global user.email "stevenking@polymaster.io"
git config --global user.name "Steven King"
echo "✓ Git configured"

# Check remote
REMOTE=$(git remote -v 2>/dev/null | grep origin)
if [ -z "$REMOTE" ]; then
    echo "❌ ERROR: No remote repository configured!"
    echo ""
    echo "Please do this first:"
    echo "1. Go to https://github.com/new"
    echo "2. Create new repository named: polymaster-btc-bot"
    echo "3. Run these commands after creating:"
    echo ""
    echo "   git remote add origin git@github.com:YOUR_USERNAME/polymaster-btc-bot.git"
    echo "   ./scripts/push_to_github.sh"
    echo ""
    exit 1
fi

echo "✓ Remote: $REMOTE"
echo ""

# Stage files
git add -A
echo "✓ Files staged"

# Commit if there are changes
if ! git diff-index --quiet HEAD --; then
    git commit -m "Initial commit: Polymaster BTC Bot v2.1" || true
    echo "✓ Committed"
else
    echo "ℹ️ All changes already committed"
fi

# Push
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $BRANCH"
echo ""

if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
    echo "🚀 Pushing..."
    git push -u origin $BRANCH
    echo ""
    echo "✅ SUCCESS! Code pushed to GitHub!"
    echo ""
    echo "Your VPS clone command:"
    echo "  cd /root && git clone <REPLACE_WITH_GITHUB_URL>"
else
    echo "Creating main branch..."
    git checkout -b main 2>/dev/null || git checkout -b master 2>/dev/null || true
    git push -u origin main
    echo "✅ Done! Branch created and pushed."
fi

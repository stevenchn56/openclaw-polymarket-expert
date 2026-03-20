#!/bin/bash
# Quick check runner

cd /Users/stevenwang/.openclaw/workspace/projects/polymaster-btc-bot

echo "=========================================="
echo "  POLYMASTER WS CHECK - v2.0.1"
echo "=========================================="
echo ""

# Check if Python is available
if ! command -v python3 &>/dev/null; then
    echo "❌ Python3 not found!"
    echo "Please install Python 3.10+ first"
    exit 1
fi

echo "✅ Python: $(python3 --version)"
echo ""

# Try running the simple check
python3 simple_ws_check.py 2>&1

exit_code=$?
echo ""

if [ $exit_code -eq 0 ]; then
    echo "=========================================="
    echo "  ✅ CHECK COMPLETE - READY TO DEPLOY!"
    echo "=========================================="
else
    echo "=========================================="
    echo "  ❌ Check failed with code: $exit_code"
    echo "=========================================="
fi

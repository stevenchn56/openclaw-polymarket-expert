#!/usr/bin/env python3
"""Run backtest and save results to file for viewing"""

import subprocess
import sys

print("=" * 60)
print("  RUNNING BACKTEST AND SAVING RESULTS")
print("=" * 60)

# Run the minimal backtest
result = subprocess.run(
    ['python3', 'backtest_minimal.py'],
    capture_output=True,
    text=True,
    cwd='/Users/stevenwang/.openclaw/workspace/projects/polymaster-btc-bot'
)

# Save stdout to file
with open('backtest_result.txt', 'w') as f:
    f.write(result.stdout)
    f.write("\n" + "=" * 60 + "\n")
    f.write("STDERR:\n")
    f.write(result.stderr)

print("\n✅ Backtest completed!")
print("\n📄 Results saved to:")
print("   • backtest_result.txt")
print("\nView with:")
print("   cat backtest_result.txt")
print("   tail -40 backtest_result.txt  # See summary section")
print("=" * 60)

#!/usr/bin/env python3
"""Check backtest_enhanced.py for 'direction' key issue"""

import re
from pathlib import Path

P = Path(__file__).parent.absolute()
bt_path = P / "backtest_enhanced.py"

print("=" * 60)
print("BACKTEST LOGIC CHECK")
print("=" * 60)

# Read file content
with open(bt_path, 'r') as f:
    content = f.read()
    lines = content.split('\n')

print(f"\nFile: {bt_path}")
print(f"Total lines: {len(lines)}")

# Find all return statements around run_scenario_test
print("\n🔍 Looking for 'return' statements in run_scenario_test function...")

in_run_scenario = False
return_count = 0
for i, line in enumerate(lines, 1):
    if 'def run_scenario_test' in line:
        in_run_scenario = True
        print(f"\n[Line {i}] Found function definition:")
        print(f"  {line.strip()}")
    
    if in_run_scenario and line.strip().startswith('return'):
        return_count += 1
        # Get context (5 lines before and after)
        start = max(0, i - 6)
        end = min(len(lines), i + 2)
        
        print(f"\n--- Return #{return_count} at Line {i} ---")
        print("Context:")
        for j in range(start, end):
            marker = ">>>" if j == i - 1 else "   "
            print(f"{marker} {j+1:4d}: {lines[j]}")
    
    # End of function (next def or class at same indent)
    if in_run_scenario and i > 180 and re.match(r'^\w', line.strip()) and not line.strip().startswith('#'):
        break

# Also check compare_all_scenarios
print("\n\n🔍 Checking compare_all_scenarios usage of 'direction'...")
for i, line in enumerate(lines, 1):
    if 'compare_all_scenarios' in line.lower():
        print(f"[Line {i}] Found: {line.strip()}")
    if "'direction'" in line:
        print(f"[Line {i}] Uses direction: {line.strip()}")

# Summary
print("\n" + "=" * 60)
print(f"Found {return_count} return statement(s) in run_scenario_test")
print("=" * 60)

if return_count == 0:
    print("\n⚠ No returns found - function may be incomplete!")
else:
    print("\n✅ Returns found - checking what keys are returned...")

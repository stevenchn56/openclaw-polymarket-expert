#!/usr/bin/env python3
"""Quick backtest status check"""

from pathlib import Path
import re

result_file = Path(__file__).parent / "backtest_complete_results.txt"

print("="*70)
print("  BACKTEST RESULTS STATUS CHECK")
print("="*70)

if not result_file.exists():
    print(f"\n❌ File not found: {result_file}")
    print("\nTrying alternative locations...")
    
    # Search for any result files
    for f in Path(__file__).parent.glob("**/*.txt"):
        if "backtest" in str(f).lower() or "result" in str(f).lower():
            size = f.stat().st_size
            print(f"  ✓ {f.name} - {size:,} bytes")
    
    exit(1)

# Get file info
size = result_file.stat().st_size
lines = 0
with open(result_file, 'r') as f:
    lines = sum(1 for _ in f)

print(f"\n📄 File Information:")
print(f"  Location: {result_file}")
print(f"  Size: {size:,} bytes ({size/1024:.1f} KB)")
print(f"  Lines: {lines:,}")

if lines == 0 or size < 100:
    print("\n⚠️  File appears empty or minimal")
    print("   Running backtest again?")
    exit(1)

print(f"\n✅ File looks complete!")
print("\n🔍 Key Sections Detected:")

# Read and search for key sections
with open(result_file, 'r') as f:
    content = f.read()

sections = [
    ('SCENARIO', 'Scenario Testing'),
    ('RESULTS SUMMARY', 'Results Summary'),
    ('Overall Statistics', 'Overall Stats'),
    ('Best Result', 'Best Performer'),
    ('Worst Result', 'Worst Performer'),
    ('COMPREHENSIVE BACKTEST COMPLETE', 'Completion Section'),
]

for keyword, description in sections:
    if keyword in content:
        print(f"  ✓ {description:25s} FOUND")
    else:
        print(f"  ⚠ {description:25s} NOT FOUND")

# Count scenario runs
scenario_count = len(re.findall(r'SCENARIO:', content))
print(f"\n📊 Execution Metrics:")
print(f"  Total Scenario Headers: {scenario_count}")

# Check for successful completions
complete_count = len(re.findall(r'BACKTEST COMPLETE|PASSED|SUCCESS', content, re.IGNORECASE))
print(f"  Success Markers Found: {complete_count}")

# Extract some numbers if possible
runs_match = re.search(r'(\d+)\s*runs?', content, re.IGNORECASE)
if runs_match:
    print(f"  Runs Mentioned: {runs_match.group(1)}")

print("\n" + "="*70)
print("💡 TIP: Run 'tail -100 backtest_complete_results.txt' for final summary")
print("="*70)

#!/usr/bin/env python3
"""Check backtest result file"""

from pathlib import Path

result_file = Path(__file__).parent / "backtest_full_results.txt"

if not result_file.exists():
    print("⚠️  Result file not found yet")
    print(f"   Waiting for backtest to complete...")
    
    # Try running it directly instead
    print("\n🔄 Running backtest directly...")
    import subprocess
    import sys
    
    result = subprocess.run(
        [sys.executable, 'backtest_v2_working.py'],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent)
    )
    
    with open(result_file, 'w') as f:
        f.write(result.stdout)
    
    print(f"✅ Results saved to {result_file}")

# Read and display key parts
with open(result_file, 'r') as f:
    lines = f.readlines()

print(f"\n📊 File has {len(lines)} lines")

# Find and display summary section
for i, line in enumerate(lines):
    if 'COMPREHENSIVE BACKTEST' in line or 'ALL TESTS COMPLETED' in line:
        # Print context around this
        start = max(0, i-15)
        end = min(len(lines), i+16)
        print("\n" + "="*70)
        print("  KEY RESULTS SECTION:")
        print("="*70)
        print(''.join(lines[start:end]))
        break

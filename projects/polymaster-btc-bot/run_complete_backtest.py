#!/usr/bin/env python3
"""Run backtest and save to file"""

import subprocess
import sys
from pathlib import Path

output_file = Path(__file__).parent / "backtest_full_results.txt"

print(f"Running comprehensive backtest...")
print(f"Results will be saved to: {output_file}")
print("-" * 70)

# Run the backtest with timeout
result = subprocess.run(
    ['python3', 'backtest_v2_working.py'],
    capture_output=True,
    text=True,
    cwd=str(Path(__file__).parent),
    env={**os.environ, 'PYTHONWARNINGS': 'ignore'}
)

# Save output
with open(output_file, 'w') as f:
    f.write(result.stdout)
    f.write("\n" + "="*70 + "\n")
    f.write("STDERR:\n")
    f.write(result.stderr if result.stderr else "None")

print(f"\n✅ Backtest complete!")
print(f"\n📄 Full results saved to: {output_file}")
print("\nTo view summary:")
print(f"  tail -40 {output_file}")
print("\nTo view full file:")
print(f"  cat {output_file}")
print("=" * 70)

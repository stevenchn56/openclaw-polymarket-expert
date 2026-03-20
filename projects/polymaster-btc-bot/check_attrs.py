#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from strategies.btc_window_5m import BTCWindowStrategy as Btc

s = Btc()

# Get all attributes containing 'min', 'conf', or 'threshold' (case insensitive)
matching = []
for attr in dir(s):
    if not attr.startswith('_'):
        lower_attr = attr.lower()
        if any(keyword in lower_attr for keyword in ['min', 'conf', 'threshold']):
            try:
                val = getattr(s, attr)
                matching.append(f"{attr}: {val}")
            except Exception as e:
                matching.append(f"{attr}: <error - {e}>")

with open('/Users/stevenwang/.openclaw/workspace/projects/polymaster-btc_bot/check_out.txt', 'w') as f:
    f.write("=== Matching Attributes ===\n")
    for line in sorted(matching):
        f.write(line + "\n")
    
    f.write("\n=== All Public Attributes ===\n")
    for attr in sorted(dir(s)):
        if not attr.startswith('_'):
            val = getattr(s, attr)
            if not callable(val):
                f.write(f"{attr}: {val}\n")

print("Done! Check check_out.txt")

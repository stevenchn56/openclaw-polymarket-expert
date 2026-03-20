#!/usr/bin/env python3
"""Diagnose strategy - write output to file"""

import sys
from pathlib import Path
from decimal import Decimal

P = Path(__file__).parent.absolute()
sys.path.insert(0, str(P))

output_lines = []

def log(msg):
    print(msg)
    output_lines.append(str(msg))

log("=" * 60)
log("STRATEGY DIAGNOSIS")
log("=" * 60)

# Import
try:
    from strategies.btc_window_5m import BTCWindowStrategy
    s = BTCWindowStrategy(lookback_minutes=5)
    log("✅ Strategy loaded")
except Exception as e:
    log(f"❌ Load failed: {e}")
    with open("diagnosis.txt", "w") as f:
        f.write("\n".join(output_lines))
    sys.exit(1)

# Check attributes
log("\n=== ATTRIBUTES ===")
attrs = [a for a in dir(s) if not a.startswith('_')]
for attr in sorted(attrs):
    val = getattr(s, attr)
    log(f"{attr}: {type(val).__name__} = {repr(val)[:60]}")

# Test update
log("\n=== UPDATE TEST ===")
result = s.update_price(Decimal("45000"))
log(f"update_price returned: {type(result).__name__ if result else 'None'}")

# Test quote methods
quote_methods = ['get_latest_quote', 'current_quote', 'generate_bidirectional_quote']
log("\n=== QUOTE METHODS ===")
for method_name in quote_methods:
    if hasattr(s, method_name):
        try:
            result = getattr(s, method_name)()
            log(f"{method_name}: SUCCESS → {type(result).__name__}")
        except Exception as e:
            log(f"{method_name}: ERROR → {e}")
    else:
        log(f"{method_name}: NOT FOUND")

# Write to file
with open("diagnosis.txt", "w") as f:
    f.write("\n".join(output_lines))

log("\n✅ Full diagnosis written to diagnosis.txt")
log("Read it with: cat diagnosis.txt")

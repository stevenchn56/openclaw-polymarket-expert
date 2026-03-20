#!/usr/bin/env python3
"""Diagnose v2.0 quote implementation - write to file"""

from strategies.btc_window_5m import BTCWindowStrategy
import sys

sys.path.insert(0, '/Users/stevenwang/.openclaw/workspace/projects/polymaster-btc-bot')

lines = []
def log(msg):
    print(msg)
    lines.append(str(msg))

log("=" * 60)
log("V2.0 BIDIRECTIONAL QUOTE DIAGNOSIS")
log("=" * 60)

# Initialize
s = BTCWindowStrategy(lookback_minutes=5)
log("\n✅ Strategy initialized")
log(f"   spread_bps: {s.spread_bps}")
log(f"   pricer type: {type(s.pricer).__name__ if s.pricer else 'None'}")

# Test with prices
from decimal import Decimal
for price in [Decimal("45000"), Decimal("45100"), Decimal("45050")]:
    s.update_price(price)
    log(f"✓ Updated with ${float(price):,.2f}")

# Check state
log(f"\ncurrent_quote: {s.current_quote}")
log(f"generate_bidirectional_quote exists: {hasattr(s, 'generate_bidirectional_quote')}")

# Summary
log("\n" + "=" * 60)
if not hasattr(s, 'generate_bidirectional_quote'):
    log("❌ MISSING: generate_bidirectional_quote() method!")
else:
    try:
        quote = s.generate_bidirectional_quote()
        log(f"✅ Works! Quote: {quote}")
    except Exception as e:
        log(f"⚠ Error calling it: {e}")

# Write to file
with open("v2_diagnosis.txt", "w") as f:
    f.write("\n".join(lines))

log("\n📄 Full diagnosis saved to v2_diagnosis.txt")

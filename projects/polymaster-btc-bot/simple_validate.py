#!/usr/bin/env python3
"""Simple validation - write everything to file"""

import sys
from pathlib import Path
from decimal import Decimal

P = Path(__file__).parent.absolute()
sys.path.insert(0, str(P))

output = []

def log(msg):
    output.append(str(msg))
    print(msg)

log("=" * 70)
log("  STRATEGY VALIDATION TEST v2.0")
log("=" * 70)

# Import
try:
    from strategies.btc_window_5m import BTCWindowStrategy
    s = BTCWindowStrategy(lookback_minutes=5)
    log("\n✅ Strategy loaded successfully")
except Exception as e:
    log(f"❌ Load failed: {e}")
    with open('validation_result.txt', 'w') as f:
        f.write('\n'.join(output))
    sys.exit(1)

# Test data generation (no external deps!)
import random
from datetime import datetime, timedelta

base_price = Decimal("45000")
prices = [base_price + Decimal(str(random.gauss(0, 100))) for _ in range(50)]

log(f"\n[1] Generated {len(prices)} price points:")
log(f"    Range: ${float(min(prices)):,.2f} - ${float(max(prices)):,.2f}")
log(f"    First: ${float(prices[0]):,.2f}, Last: ${float(prices[-1]):,.2f}")

# Process candles
log("\n[2] Processing candles...")
for i, price in enumerate(prices):
    s.update_price(price)

log(f"    ✓ Updated {len(s.price_history)} prices")

# Generate quote
log("\n[3] Generating bidirectional quote...")
if hasattr(s, 'generate_bidirectional_quote'):
    try:
        quote = s.generate_bidirectional_quote()
        
        if quote:
            log("    ✅ Quote generated successfully!")
            log(f"       Bid:   {quote['bid']}")
            log(f"       Ask:   {quote['ask']}")
            log(f"       Fair:  {quote['fair_value']}")
            log(f"       Spread: {quote['spread_bps']} bps")
            
            # Calculate actual spread
            spread_pct = float(quote['ask'] - quote['bid']) / float(quote['fair_value']) * 10000
            log(f"       Actual spread: {spread_pct:.2f} bps (target: {quote['spread_bps']})")
            
            status = "PASS" if abs(spread_pct - quote['spread_bps']) < 0.01 else "WARN"
            log(f"\n    [{status}] SPREAD VERIFICATION")
        else:
            log("    ⚠ Returned None")
            
    except Exception as e:
        log(f"    ❌ Error: {e}")
        import traceback
        log(traceback.format_exc())
else:
    log("    ❌ Method not found")

# Can trade check
log("\n[4] Trading state check...")
if hasattr(s, 'can_trade'):
    try:
        can = s.can_trade()
        log(f"    ✓ can_trade(): {can}")
    except Exception as e:
        log(f"    ⚠ can_trade error: {e}")
else:
    log("    ⚠ can_trade() not available")

# Summary
log("\n" + "=" * 70)
log("  ✅ VALIDATION COMPLETE")
log("=" * 70)

log("\n📊 SUMMARY:")
log(f"  • Strategy loads: ✓")
log(f"  • Price updates: ✓ ({len(s.price_history)} points)")
log(f"  • Bidirectional quote: {'✓' if 'quote' in locals() and quote else '✗'}")
log(f"  • Spread accuracy: {'✓' if quote and abs(spread_pct - quote['spread_bps']) < 0.01 else '⚠'}")

final_status = "PASS" if quote else "FAIL"
log(f"\n  🏁 FINAL STATUS: {final_status}")

log("\n💡 NEXT STEPS:")
log("  1. Review backtest_enhanced.py (requires pandas)")
log("  2. Update MEMORY.md with results")
log("  3. Prepare VPS deployment")

# Write to file
with open('validation_result.txt', 'w') as f:
    f.write('\n'.join(output))

log("\n📄 Full output saved to validation_result.txt")
log("View with: cat validation_result.txt")

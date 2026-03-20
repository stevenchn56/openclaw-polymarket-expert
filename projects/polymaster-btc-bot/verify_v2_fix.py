#!/usr/bin/env python3
"""Verify v2.0 fix works correctly"""

from decimal import Decimal
import sys
sys.path.insert(0, '/Users/stevenwang/.openclaw/workspace/projects/polymaster-btc-bot')

from strategies.btc_window_5m import BTCWindowStrategy

print("Testing generate_bidirectional_quote...")

s = BTCWindowStrategy(lookback_minutes=5)

# Feed some prices
for price in [Decimal("45000"), Decimal("45100"), Decimal("45050")]:
    s.update_price(price)

# Try to generate quote
if hasattr(s, 'generate_bidirectional_quote'):
    print("✓ Method exists")
    quote = s.generate_bidirectional_quote()
    if quote:
        print(f"✅ SUCCESS!")
        print(f"   Bid: {quote['bid']}")
        print(f"   Ask: {quote['ask']}")
        print(f"   Spread: {quote['spread_bps']} bps")
        
        # Test backtest with this quote
        spread = float(quote['ask'] - quote['bid']) / float(quote['fair_value']) * 10000
        print(f"\n💡 Actual spread: {spread:.2f} bps (target: {quote['spread_bps']})")
        
        # Write result to file for easier viewing
        with open('v2_test_result.txt', 'w') as f:
            f.write(f"Bid: {quote['bid']}\n")
            f.write(f"Ask: {quote['ask']}\n")
            f.write(f"Fair: {quote['fair_value']}\n")
            f.write(f"Spread: {quote['spread_bps']} bps\n")
        print("\n📄 Result saved to v2_test_result.txt")
    else:
        print("✗ Returned None")
else:
    print("✗ Method not found")

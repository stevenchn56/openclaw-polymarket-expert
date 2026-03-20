#!/usr/bin/env python3
"""Final strategy test - handles None returns properly"""

import sys
from pathlib import Path
from decimal import Decimal
import random
from datetime import datetime, timedelta

P = Path(__file__).parent.absolute()
sys.path.insert(0, str(P))

print("=" * 60)
print("  FINAL STRATEGY TEST v2.0")
print("=" * 60)

# ============================================
# STEP 1: Import and Initialize
# ============================================
print("\n[1/4] Loading Strategy...")
print("-" * 60)

try:
    from strategies.btc_window_5m import BTCWindowStrategy
    
    s = BTCWindowStrategy(lookback_minutes=5)
    print("✅ Strategy loaded successfully!")
    
    # Check what methods actually exist
    methods = [m for m in dir(s) if not m.startswith('_') and callable(getattr(s, m))]
    print(f"   Available methods ({len(methods)}): {', '.join(sorted(methods)[:10])}")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================
# STEP 2: Generate Test Data
# ============================================
print("\n[2/4] Generating Price Data...")
print("-" * 60)

def gen_prices(start=45000, count=50, vol=0.02):
    prices = [Decimal(str(start))]
    for _ in range(count - 1):
        change = Decimal(str(random.gauss(0, start * vol)))
        new_p = max(start * 0.8, prices[-1] + change)
        prices.append(new_p)
    return prices

prices = gen_prices(45000, 50, 0.015)
print(f"✓ Generated {len(prices)} price points")
print(f"  Range: ${float(min(prices)):,.2f} - ${float(max(prices)):,.2f}")
print(f"  First: ${float(prices[0]):,.2f}, Last: ${float(prices[-1]):,.2f}")

# ============================================
# STEP 3: Process Candles (Correctly!)
# ============================================
print("\n[3/4] Processing Candles...")
print("-" * 60)

for i, price in enumerate(prices[:10]):  # Just first 10 for demo
    # Update price - this usually returns None for strategies
    result = s.update_price(price)
    
    # Strategies typically don't return values from update_price
    # We check state separately
    
    print(f"  Candle {i+1:2d}: ${float(price):>10,.2f} ✓ Updated")

# Try to get quote AFTER updates
if hasattr(s, 'get_latest_quote'):
    print("\n  Calling get_latest_quote()...")
    try:
        quote = s.get_latest_quote()
        print(f"  ✓ Got quote: {type(quote).__name__}")
        if quote:
            print(f"    {quote}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
elif hasattr(s, 'current_quote'):
    print("\n  Calling current_quote()...")
    try:
        quote = s.current_quote()
        print(f"  ✓ Got quote: {quote}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
else:
    print("\n  ⚠ No quote method found - strategy may work differently")

# ============================================
# STEP 4: Verify Can Trade Method
# ============================================
print("\n[4/4] Checking Trading State...")
print("-" * 60)

if hasattr(s, 'can_trade'):
    print("  can_trade() method exists")
    try:
        can = s.can_trade()
        print(f"  ✓ Can trade: {can}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
else:
    print("  ⚠ can_trade() method NOT found")

# Summary
print("\n" + "=" * 60)
print("  ✅ TEST COMPLETED")
print("=" * 60)
print("\n💡 Key Insights:")
print("  • Strategy loads correctly")
print("  • update_price() accepts Decimal prices")
print("  • Quote methods depend on implementation")
print("  • Next step: Check actual quote generation logic")
print("\n🎯 Recommendation:")
print("  The strategy probably calculates quotes internally.")
print("  Look for generate_bidirectional_quote() or similar.")
print("=" * 60)

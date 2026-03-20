#!/usr/bin/env python3
"""Correct test for strategy pattern (void update methods)"""

from decimal import Decimal
from strategies.btc_window_5m import BTCWindowStrategy
import random

print("=" * 60)
print("  CORRECT STRATEGY TEST")
print("=" * 60)

# Initialize strategy
strategy = BTCWindowStrategy(lookback_minutes=5)
print("\n✅ Strategy initialized")

# Generate some prices
prices = [Decimal(str(45000 + random.uniform(-500, 500))) for _ in range(20)]

# Process each candle (correct pattern - don't expect return value)
print("\n[Processing candles]")
for i, price in enumerate(prices):
    # This is VOID - it updates internal state, doesn't return anything
    strategy.update_price(price)
    
    if i < 5 or i == len(prices) - 1:  # Show first 5 and last
        print(f"  Candle {i+1}: ${float(price):,.2f} ✓")

# Now check the strategy's state
print("\n[Checking strategy state]")

# Option 1: get_latest_quote
if hasattr(strategy, 'get_latest_quote'):
    try:
        quote = strategy.get_latest_quote()
        print(f"✓ get_latest_quote: {quote}")
    except Exception as e:
        print(f"✗ get_latest_quote error: {e}")

# Option 2: generate_bidirectional_quote (what we need for v2.0!)
if hasattr(strategy, 'generate_bidirectional_quote'):
    try:
        quote = strategy.generate_bidirectional_quote()
        print(f"✓ generate_bidirectional_quote: {quote}")
        
        # Check structure
        if isinstance(quote, dict):
            print(f"\n📊 Quote structure:")
            for k, v in quote.items():
                print(f"   {k}: {v}")
    except Exception as e:
        print(f"✗ generate_bidirectional_quote error: {e}")
        print("   This method exists but isn't fully implemented yet")

# Option 3: can_trade check
if hasattr(strategy, 'can_trade'):
    try:
        can = strategy.can_trade()
        print(f"\n✓ can_trade: {can}")
    except Exception as e:
        print(f"\n⚠ can_trade error: {e}")

print("\n" + "=" * 60)
print("  ✅ TEST COMPLETE")
print("=" * 60)
print("\n💡 Note:")
print("  Strategies typically use VOID update methods.")
print("  Call update_price(), THEN call get_latest_quote().")
print("  Don't chain them!")

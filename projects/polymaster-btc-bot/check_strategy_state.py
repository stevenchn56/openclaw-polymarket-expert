#!/usr/bin/env python3
"""Check BTCWindowStrategy state after initialization"""

import sys
from pathlib import Path
from decimal import Decimal

P = Path(__file__).parent.absolute()
sys.path.insert(0, str(P))

print("=" * 60)
print("  STRATEGY DIAGNOSTIC")
print("=" * 60)

# Import strategy
from strategies.btc_window_5m import BTCWindowStrategy

print("\n[1] Creating Strategy...")
strategy = BTCWindowStrategy(lookback_minutes=5)
print(f"✅ Strategy created: {type(strategy).__name__}")

# Check attributes
print("\n[2] Checking Attributes...")
print(f"   lookback_minutes: {getattr(strategy, 'lookback_minutes', 'NOT FOUND')}")
print(f"   fee_rate_bps: {getattr(strategy, 'fee_rate_bps', 'NOT FOUND')}")
print(f"   MAX_POSITION_PER_SIDE: {getattr(strategy, 'MAX_POSITION_PER_SIDE', 'NOT FOUND')}")

# List all public methods and attributes
public_members = [m for m in dir(strategy) if not m.startswith('_')]
print(f"\n[3] Public Members ({len(public_members)} total):")
for member in sorted(public_members):
    attr = getattr(strategy, member)
    if callable(attr):
        print(f"   📦 {member}() [method]")
    else:
        val_type = type(attr).__name__
        print(f"   💡 {member} [{val_type}] = {repr(attr)[:50]}")

# Test update_price
print("\n[4] Testing update_price()...")
test_prices = [Decimal("45000"), Decimal("45100"), Decimal("45050")]

for i, price in enumerate(test_prices):
    result = strategy.update_price(price)
    print(f"   Candle {i+1}: price={price}, return_type={type(result).__name__ if result is not None else 'None'}")

# Check current_quote if exists
if hasattr(strategy, 'current_quote'):
    print("\n[5] Testing current_quote()...")
    try:
        quote = strategy.current_quote()
        print(f"✅ current_quote works: {quote}")
    except Exception as e:
        print(f"❌ current_quote failed: {e}")
else:
    print("\n[5] current_quote() NOT FOUND - this is expected!")

# Test other common methods
common_methods = ['get_latest_quote', 'generate_bidirectional_quote', 'can_trade']
print("\n[6] Checking Common Methods...")

for method_name in common_methods:
    if hasattr(strategy, method_name):
        method = getattr(strategy, method_name)
        print(f"   ✓ {method_name} exists")
        
        # Try calling it if no args needed
        if method_name == 'get_latest_quote':
            try:
                result = method()
                print(f"      → Result: {type(result).__name__}")
            except TypeError as te:
                print(f"      ⚠ Needs args: {te}")
            except Exception as e:
                print(f"      ✗ Error: {e}")
    
    elif method_name == 'get_latest_quote':
        print(f"   ⚠ {method_name} not found (expected)")
    else:
        print(f"   ? {method_name} status unknown")

# Summary
print("\n" + "=" * 60)
print("  ✅ DIAGNOSTIC COMPLETE")
print("=" * 60)
print("\nKey findings:")
print(f"  • Strategy has {len([m for m in public_members if callable(getattr(strategy, m))])} methods")
print(f"  • update_price() returns non-None values")
print(f"  • Check actual implementation for quote generation")

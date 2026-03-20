#!/usr/bin/env python3
"""Quick test to see what update_price returns"""

from decimal import Decimal
from strategies.btc_window_5m import BTCWindowStrategy

# Create strategy
s = BTCWindowStrategy(lookback_minutes=5)
print(f"Created: {type(s).__name__}")

# Test update
result = s.update_price(Decimal("45000"))
print(f"update_price returned: {result} (type: {type(result).__name__ if result else 'None'})")

# List methods with "price" in name
methods = [m for m in dir(s) if 'price' in m.lower()]
print(f"\nMethods with 'price': {methods}")

# Try calling them
if hasattr(s, 'calculate_volatility'):
    try:
        vol = s.calculate_volatility()
        print(f"✓ calculate_volatility() works: {vol}")
    except Exception as e:
        print(f"✗ calculate_volatility failed: {e}")

if hasattr(s, 'get_latest_quote'):
    try:
        quote = s.get_latest_quote()
        print(f"✓ get_latest_quote() works: {quote}")
    except Exception as e:
        print(f"✗ get_latest_quote failed: {e}")

if hasattr(s, 'generate_bidirectional_quote'):
    try:
        quote = s.generate_bidirectional_quote()
        print(f"✓ generate_bidirectional_quote() works: {quote}")
    except Exception as e:
        print(f"✗ generate_bidirectional_quote failed: {e}")

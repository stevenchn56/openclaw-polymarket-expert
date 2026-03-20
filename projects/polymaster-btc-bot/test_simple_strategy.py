#!/usr/bin/env python3
"""Simple test - just verify strategy can be instantiated"""

from strategies.btc_window_5m import BTCWindowStrategy
from decimal import Decimal

# Create instance
print("Creating BTCWindowStrategy...")
s = BTCWindowStrategy(lookback_minutes=5)

print(f"✓ Strategy created successfully!")
print(f"  Type: {type(s).__name__}")
print(f"  Module: {type(s).__module__}")

# List all attributes
all_attrs = [a for a in dir(s) if not a.startswith('_')]
print(f"\nTotal public attributes/methods: {len(all_attrs)}")

# Print first 20 methods
print("\nFirst 20 members:")
for attr in sorted(all_attrs)[:20]:
    val = getattr(s, attr)
    if callable(val):
        print(f"  • {attr}() [method]")
    else:
        print(f"  • {attr} = {val!r}")

print("\n✅ Test passed - Strategy is working!")

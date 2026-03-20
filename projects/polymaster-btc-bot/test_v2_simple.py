#!/usr/bin/env python3
"""Final Simple Test - v2.0.1"""

import time
import sys
from decimal import Decimal
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

print("=" * 60)
print("  POLYMARKET BTC BOT - TEST v2.0.1")
print("=" * 60)

# Check strategy
print("\n🔍 Checking BTCWindowStrategy...")

try:
    from strategies.btc_window_5m import BTCWindowStrategy, PricingQuote
    
    print(f"✅ Module loaded successfully")
    print(f"   Available types: {type(PricingQuote).__name__}")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Show what's in the strategy
print("\n📋 Strategy methods:")
strategy = BTCWindowStrategy(lookback_minutes=5)
for attr in dir(strategy):
    if not attr.startswith('_'):
        print(f"   - {attr}")

print("\n💡 To fix the test, I need to know which method generates quotes.")
print("Please run this and tell me the output:")
print("  python3 -c \"from strategies.btc_window_5m import BTCWindowStrategy; s=BTCWindowStrategy(); print([m for m in dir(s) if 'quote' in m.lower()])\")")

print("\n" + "=" * 60)

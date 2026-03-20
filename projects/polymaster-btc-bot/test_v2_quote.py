#!/usr/bin/env python3
"""Test v2.0 Bidirectional Quote Implementation"""

import sys
from pathlib import Path
from decimal import Decimal
import random

P = Path(__file__).parent.absolute()
sys.path.insert(0, str(P))

print("=" * 60)
print("  POLYMARKET BTC BOT - V2.0 QUOTE TEST")
print("=" * 60)

# Import strategy and pricer
from strategies.btc_window_5m import BTCWindowStrategy
from pricing.black_scholes_v2 import BlackScholesPricer

print("\n[1] Initializing Strategy...")
strategy = BTCWindowStrategy(lookback_minutes=5)
print(f"✓ BTCWindowStrategy created")
print(f"  Lookback: {strategy.lookback_minutes} min")
print(f"  Spread: {strategy.spread_bps} bps")
print(f"  Has pricer: {strategy.pricer is not None}")

# Test with actual prices
print("\n[2] Feeding Price Data...")
base_price = Decimal("45000")
prices = [base_price + Decimal(str(random.gauss(0, 100))) for _ in range(20)]

for i, price in enumerate(prices):
    strategy.update_price(price)
    
    if i < 3 or i == len(prices) - 1:
        print(f"  Candle {i+1}: ${float(price):,.2f} ✓")

print(f"\n✓ Loaded {len([p for p in prices])} price points")

# Check current state
print("\n[3] Checking Quote State...")
print(f"  current_quote attribute: {strategy.current_quote}")
print(f"  last_price: {strategy.last_price}")
print(f"  price_history length: {len(strategy.price_history)}")

# Try to trigger quote generation
print("\n[4] Attempting Quote Generation...")

# Method 1: Try generate_bidirectional_quote if exists
if hasattr(strategy, 'generate_bidirectional_quote'):
    print("  → Calling generate_bidirectional_quote()...")
    try:
        quote = strategy.generate_bidirectional_quote()
        print(f"  ✅ SUCCESS: {quote}")
        
        if isinstance(quote, dict):
            print(f"\n     Structure: {list(quote.keys())}")
            if 'bid' in quote:
                print(f"     Bid: {quote['bid']}")
            if 'ask' in quote:
                print(f"     Ask: {quote['ask']}")
                
    except Exception as e:
        print(f"  ⚠ Error: {e}")

# Method 2: Check if can_trade allows trading
if hasattr(strategy, 'can_trade'):
    try:
        can = strategy.can_trade()
        print(f"\n  can_trade(): {can}")
    except Exception as e:
        print(f"\n  ⚠ can_trade error: {e}")

# Summary
print("\n" + "=" * 60)
print("  DIAGNOSIS COMPLETE")
print("=" * 60)
print("\n📊 Current Status:")
print(f"  • Strategy has {len(strategy.price_history)} prices in history")
print(f"  • current_quote = {strategy.current_quote}")
print(f"  • generate_bidirectional_quote() {'exists' if hasattr(strategy, 'generate_bidirectional_quote') else 'MISSING'}")

if not hasattr(strategy, 'generate_bidirectional_quote'):
    print("\n⚠️  MISSING FEATURE:")
    print("   The v2.0 bidirectional quote generation logic is not implemented!")
    print("\n💡 Next Steps:")
    print("   1. Implement generate_bidirectional_quote() method")
    print("   2. Use BlackScholesPricer to calculate fair value")
    print("   3. Apply spread_bps to create bid/ask quotes")
else:
    print("\n✅ All features present - ready for backtest!")

#!/usr/bin/env python3
"""Quick test to verify v2.0.1 bidirectional system works"""

import sys
sys.path.insert(0, '.')

from strategies.btc_window_5m import BTCWindowStrategy, PriceDataPoint
from decimal import Decimal

print("=" * 60)
print("  QUICK VERIFICATION - Bidirectional Market Making v2.0.1")
print("=" * 60)

# Test scenario: High confidence prediction (0.80 probability)
strategy = BTCWindowStrategy(fee_rate_bps=10)
mock_prices = [Decimal("0.80"), Decimal("0.82"), Decimal("0.79"), Decimal("0.81"), Decimal("0.80")]
historical_data = [PriceDataPoint(close=p) for p in mock_prices]

print("\n🎯 Scenario: High confidence YES prediction (~80%)")
print("-" * 60)

quote = strategy.generate_bidirectional_quote(historical_data)

print(f"\n✅ Fair Value (YES): {quote['fair_value']}")
print(f"✅ Confidence:       {quote['confidence']:.1%}")
print(f"✅ Spread:           {quote['strategy_params']['spread_bps']}bps")
print(f"✅ Size Multiplier:  {quote['strategy_params']['size_multiplier']}x")

print("\n💹 Quote Structure:")
print(f"   YES Side:")
print(f"      Price: {quote['quotes']['yes']['price']}")
print(f"      Size:  ${quote['quotes']['yes']['size']}")
print(f"   NO Side:")
print(f"      Price: {quote['quotes']['no']['price']}")
print(f"      Size:  ${quote['quotes']['no']['size']}")

# Verify price relationship
total_price = quote['quotes']['yes']['price'] + quote['quotes']['no']['price']
print(f"\n📊 Validation:")
print(f"   YES + NO = {total_price:.4f} (should be ≈1.0)")
assert abs(float(total_price) - 1.0) < 0.02, "Price relationship invalid!"
print(f"   ✅ PASS: Binary constraint satisfied")

# Dynamic spread check
expected_spread = 15 if float(quote['confidence']) >= 0.85 else 20
actual_spread = quote['strategy_params']['spread_bps']
print(f"\n🔧 Spread Logic:")
print(f"   Expected: {expected_spread}bps (high conf)")
print(f"   Actual: {actual_spread}bps")
assert actual_spread <= expected_spread, f"Spread too wide! {actual_spread} > {expected_spread}"
print(f"   ✅ PASS: Appropriate spread applied")

print("\n" + "=" * 60)
print("✅ ALL CHECKS PASSED - System ready!")
print("=" * 60)

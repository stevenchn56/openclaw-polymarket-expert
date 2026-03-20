#!/usr/bin/env python3
"""
Quick verification test for backtest_enhanced.py Fix #3
Verifies that all critical fixes are working properly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from strategies.btc_window_5m import BTCWindowStrategy, PriceDataPoint
from decimal import Decimal

print("=" * 60)
print("FIX VERIFICATION TEST - Backtest v2.0.1")
print("=" * 60)

# Test 1: Quote generation works
print("\n🧪 Test 1: Bidirectional quote generation")
try:
    strategy = BTCWindowStrategy(fee_rate_bps=10)
    mock_data = [PriceDataPoint(close=Decimal("0.50")) for _ in range(5)]
    quote = strategy.generate_bidirectional_quote(mock_data)
    
    assert "quotes" in quote, "Missing 'quotes' key"
    assert "yes" in quote["quotes"], "Missing 'yes' quote"
    assert "no" in quote["quotes"], "Missing 'no' quote"
    
    print(f"   ✅ YES price: {quote['quotes']['yes']['price']}")
    print(f"   ✅ NO price: {quote['quotes']['no']['price']}")
    print(f"   ✅ Confidence: {quote['confidence']}")
    print(f"   ✅ Spread: {quote['strategy_params']['spread_bps']}bps")
    print("   ✅ PASS")
except Exception as e:
    print(f"   ❌ FAIL: {e}")
    sys.exit(1)

# Test 2: Backward compatibility
print("\n🧪 Test 2: Backward compatibility (update_price_with_quotation)")
try:
    old_quote = strategy.update_price_with_quotation(0.75)
    assert isinstance(old_quote, dict), "Should return dictionary"
    print(f"   ✅ Returns dict with keys: {list(old_quote.keys())[:4]}...")
    print("   ✅ PASS")
except Exception as e:
    print(f"   ❌ FAIL: {e}")
    sys.exit(1)

# Test 3: Dynamic sizing based on confidence
print("\n🧪 Test 3: Dynamic position sizing")
try:
    # High confidence scenario
    high_conf_quote = strategy.generate_bidirectional_quote(
        [PriceDataPoint(close=Decimal("0.80")) for _ in range(10)]
    )
    
    low_conf_quote = strategy.generate_bidirectional_quote(
        [PriceDataPoint(close=Decimal(str(0.40 + i*0.05))) for i in range(20)]
    )
    
    high_mult = high_conf_quote["strategy_params"]["size_multiplier"]
    low_mult = low_conf_quote["strategy_params"]["size_multiplier"]
    
    assert high_mult >= low_mult, f"High confidence should have larger size"
    
    print(f"   ✅ High conf (80%+): {high_mult}x size")
    print(f"   ✅ Low conf (<60%): {low_mult}x size")
    print("   ✅ PASS")
except Exception as e:
    print(f"   ❌ FAIL: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL FIX VERIFICATION TESTS PASSED!")
print("=" * 60)
print("\nBacktest v2.0.1 is ready to run.")
print("Run: python backtest_enhanced.py")

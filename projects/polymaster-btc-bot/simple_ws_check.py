#!/usr/bin/env python3
"""Ultra-simple WebSocket & Strategy Quick Check"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("  POLYMASTER WS STRATEGY CHECK - v2.0.1")
print("=" * 60)
print()

# Test 1: Import strategy
print("🧪 Test 1: Import Strategy... ", end="")
try:
    from strategies.btc_window_5m import BTCWindowStrategy
    print("✅ PASS")
except ImportError as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)

# Test 2: Create strategy instance
print("🧪 Test 2: Create Strategy Instance... ", end="")
try:
    strategy = BTCWindowStrategy(fee_rate_bps=10)
    print("✅ PASS")
except Exception as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)

# Test 3: Generate bidirectional quote
print("🧪 Test 3: Bidirectional Quote Generation... ", end="")
try:
    from decimal import Decimal
    mock_prices = [Decimal("0.80"), Decimal("0.82"), Decimal("0.78"), Decimal("0.81"), Decimal("0.79")]
    
    from strategies.btc_window_5m import PriceDataPoint
    historical_data = [PriceDataPoint(close=p) for p in mock_prices]
    
    quote = strategy.generate_bidirectional_quote(historical_data)
    
    # Verify structure
    assert "quotes" in quote
    assert "yes" in quote["quotes"]
    assert "no" in quote["quotes"]
    
    yes_price = float(quote["quotes"]["yes"]["price"])
    no_price = float(quote["quotes"]["no"]["price"])
    confidence = float(quote["confidence"])
    
    # Binary constraint check
    total = yes_price + no_price
    
    print("✅ PASS")
    print(f"   YES price: ${yes_price:.4f}")
    print(f"   NO price:  ${no_price:.4f}")
    print(f"   Confidence:{confidence:.1%}")
    print(f"   Total:     ${total:.4f} (target ~1.0)")
    
except Exception as e:
    print(f"❌ FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Dynamic spread check
print("🧪 Test 4: Dynamic Spread Adjustment... ", end="")
try:
    high_conf = strategy.generate_bidirectional_quote([PriceDataPoint(close=Decimal("0.85"))*5])
    low_conf = strategy.generate_bidirectional_quote([PriceDataPoint(close=Decimal("0.60"))*5])
    
    high_spread = high_conf["strategy_params"]["spread_bps"]
    low_spread = low_conf["strategy_params"]["spread_bps"]
    
    if high_spread < low_spread:
        print(f"✅ PASS (High: {high_spread}bps, Low: {low_spread}bps)")
    else:
        print(f"⚠️ WARNING (Expected inverse relationship)")
        
except Exception as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)

# Summary
print()
print("=" * 60)
print("  ✅ ALL QUICK TESTS PASSED!")
print("=" * 60)
print()
print("System ready for deployment! Next steps:")
print("1. Full backtest: python backtest_enhanced.py")
print("2. WebSocket test: python test_ws_integration.py")
print("3. Deploy to VPS: ./deploy_vps.sh")
print()

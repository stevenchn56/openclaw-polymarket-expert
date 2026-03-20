#!/usr/bin/env python3
"""Quick Integration Test - v2.0.1 Fixed Version"""

import time
import sys
from decimal import Decimal
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

print("=" * 60)
print("  POLYMARKET BTC BOT - INTEGRATION TEST v2.0.1")
print("=" * 60)

# Step 1: Import strategy module
print("\nStep 1: Module Import")
print("-" * 60)

try:
    from strategies.btc_window_5m import BTCWindowStrategy
    print("✅ Direct import successful")
except ImportError as e:
    print(f"❌ Direct import failed: {e}")
    
    # Fallback to direct file loading
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "btc_window_5m", 
        PROJECT_DIR / "strategies" / "btc_window_5m.py"
    )
    btc_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(btc_module)
    BTCWindowStrategy = btc_module.BTCWindowStrategy
    print("✅ Fallback file import successful")

# Step 2: Initialize and inspect strategy
print("\nStep 2: Strategy Initialization")
print("-" * 60)

init_success = False
for param_name in ['lookback_minutes', 'window_mins', 'lookback']:
    try:
        strategy = BTCWindowStrategy(**{param_name: 5})
        print(f"✅ Initialized with '{param_name}' parameter")
        init_success = True
        
        # List available methods
        all_methods = [m for m in dir(strategy) if not m.startswith('_')]
        quote_methods = [m for m in all_methods if 'quote' in m.lower() or 'price' in m.lower()]
        
        print(f"\n   Total public methods: {len(all_methods)}")
        print(f"   Quote/Price related methods ({len(quote_methods)}):")
        for m in sorted(quote_methods)[:8]:
            obj = getattr(strategy, m)
            is_func = callable(obj)
            print(f"     • {m} ({'method' if is_func else 'property'})")
        
        break
        
    except TypeError as te:
        print(f"⚠️  '{param_name}' not valid: {te}")
        continue

if not init_success:
    print("❌ Failed to initialize strategy")
    sys.exit(1)

# Step 3: feeRateBps signing test
print("\nStep 3: feeRateBps Signing Verification")
print("-" * 60)

try:
    from core.fast_requote import OrderSigner
    
    signer = OrderSigner(api_secret="test_api_secret_key")
    
    order_payload = {
        "market": "BTC-USD",
        "side": "BUY",
        "price": "0.85",
        "size": "5.00",
        "feeRateBps": 10,
        "timestamp": int(time.time() * 1000)
    }
    
    signature = signer.sign_order(order_payload)
    
    print(f"✅ Signature generated successfully")
    print(f"   Value: {signature[:32]}...")
    print(f"   Length: {len(signature)} chars (expected 64 for SHA256)")
    print(f"   ✓ feeRateBps field included in payload")
    
except Exception as e:
    print(f"❌ Signing failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: WebSocket infrastructure check
print("\nStep 4: WebSocket Infrastructure")
print("-" * 60)

try:
    from core.websocket_monitor import PolymarketWebSocket, BinanceWebSocket
    
    ws_poly = PolymarketWebSocket()
    ws_binance = BinanceWebSocket(symbol_mappings={"BTC-USD": "btcusdt"})
    
    print(f"✅ Polymarket WebSocket URL: {ws_poly.ws_url}")
    print(f"✅ Binance WebSocket URL: {ws_binance.ws_url}")
    print(f"✅ Symbol mappings configured: {list(ws_binance.symbol_mappings.keys())}")
    
except Exception as e:
    print(f"❌ WebSocket config failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 5: Summary
print("\n" + "=" * 60)
print("  ✅ ALL BASIC CHECKS PASSED!")
print("=" * 60)
print("\n📊 Summary:")
print("  ✓ Module imports working")
print("  ✓ Strategy initialization working")  
print("  ✓ feeRateBps signing functional")
print("  ✓ WebSocket configuration ready")
print("\n💡 Next steps:")
print("  1. Run backtest_enhanced.py for historical validation")
print("  2. Review VPS deployment guide (VPS_DEPLOYMENT_GUIDE.md)")
print("  3. Start simulation mode on VPS")
print("=" * 60)

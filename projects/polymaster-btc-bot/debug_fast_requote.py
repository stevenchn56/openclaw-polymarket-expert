#!/usr/bin/env python3
"""Debug Fast Requote Engine error"""

import sys
from pathlib import Path
from decimal import Decimal

PROJECT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

print("=" * 60)
print("  DEBUGGING: Fast Requote Error")
print("=" * 60)

# Step 1: Import
print("\n[1] Import module...")
try:
    from core.fast_requote import OrderSigner, FastRequoteEngine
    print("✅ Imported")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 2: Check __init__ params
print("\n[2] Check FastRequoteEngine.__init__ signature...")
try:
    import inspect
    sig = inspect.signature(FastRequoteEngine.__init__)
    params = list(sig.parameters.keys())
    print(f"   Parameters: {params}")
    
    # Try creating without spread_bps first
    engine = FastRequoteEngine(market="BTC-USD", fee_rate_bps=10)
    print("✅ Created with fee_rate_bps")
except TypeError as te:
    print(f"❌ Init error: {te}")
    print("   Trying alternative parameters...")
    try:
        engine = FastRequoteEngine(market="BTC-USD", lookback_minutes=5)
        print("✅ Created with lookback_minutes")
    except Exception as e2:
        print(f"❌ Still failed: {e2}")
        exit(1)
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 3: Test signer
print("\n[3] Test OrderSigner...")
try:
    signer = OrderSigner(api_secret="test_secret")
    payload = {
        "market": "BTC-USD",
        "side": "BUY",
        "price": "0.85",
        "size": "5.00",
        "feeRateBps": 10,
        "timestamp": 1234567890
    }
    sig = signer.sign_order(payload)
    print(f"✅ Signed: {sig[:32]}... (len={len(sig)})")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 4: Test methods
print("\n[4] Test available methods...")
methods = [m for m in dir(engine) if not m.startswith('_')]
print(f"   Available: {len(methods)} methods")

for m in ['update_price', 'current_quote', 'get_latest_quote']:
    if hasattr(engine, m):
        print(f"   ✓ {m}")
    else:
        print(f"   ✗ {m} NOT FOUND")

# Step 5: Try price update
print("\n[5] Try update_price_with_quotation...")
try:
    result = engine.update_price_with_quotation(
        price=Decimal("1.25"),
        confidence=Decimal("0.85"),
        timestamp=1234567890
    )
    print(f"✅ Updated: {result}")
except AttributeError as ae:
    print(f"❌ Method not found: {ae}")
    print("   Checking actual method names...")
    all_methods = [m for m in dir(engine) if not m.startswith('_') and callable(getattr(engine, m))]
    print(f"   Callable methods:")
    for m in sorted(all_methods):
        print(f"     • {m}")
    exit(1)
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 60)
print("  ✅ ALL CHECKS PASSED!")
print("=" * 60)

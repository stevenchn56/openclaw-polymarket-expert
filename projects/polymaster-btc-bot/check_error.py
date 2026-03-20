#!/usr/bin/env python3
import sys, os
from pathlib import Path
from decimal import Decimal
import traceback

P = Path(__file__).parent.absolute()
sys.path.insert(0, str(P))

print("=" * 60)
print("ERROR DEBUG - FAST REQUOTE ENGINE")
print("=" * 60)

try:
    from core.fast_requote import OrderSigner, FastRequoteEngine
    print("✓ IMPORT OK")
except ImportError as e:
    print(f"✗ IMPORT FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)

# Try different init signatures
signatures_to_try = [
    {},
    {"market": "BTC-USD"},
    {"market": "BTC-USD", "fee_rate_bps": 10},
    {"market": "BTC-USD", "lookback_minutes": 5},
]

for sig in signatures_to_try:
    try:
        if not sig:
            engine = FastRequoteEngine()
        else:
            engine = FastRequoteEngine(**sig)
        print(f"✓ CREATED with {sig}")
        break
    except Exception as ex:
        print(f"✗ Failed with {sig}: {ex}")
else:
    print("✗ CANNOT CREATE INSTANCE")
    sys.exit(1)

# List all public methods
methods = sorted([m for m in dir(engine) if not m.startswith('_')])
print(f"\nAvailable methods ({len(methods)}):")
for m in methods[:20]:
    obj = getattr(engine, m)
    is_callable = callable(obj)
    print(f"  {'●' if is_callable else '○'} {m}")

# Check for specific methods we need
needed = ['update_price', 'update_price_with_quotation', 'current_quote']
print(f"\nChecking required methods:")
for method_name in needed:
    exists = hasattr(engine, method_name)
    print(f"  {'✓' if exists else '✗'} {method_name}")

if not any(hasattr(engine, m) for m in needed):
    print("\n✗ NO FOUND METHODS!")
    print("This might be why the test failed.")
    sys.exit(1)

# Test signer
print(f"\nTesting OrderSigner...")
try:
    signer = OrderSigner(api_secret="test_secret_123")
    payload = {
        "market": "BTC-USD", 
        "side": "BUY", 
        "price": "0.85", 
        "size": "5.00", 
        "feeRateBps": 10, 
        "timestamp": 1234567890
    }
    sig = signer.sign_order(payload)
    print(f"✓ Signed: {sig[:32]}... ({len(sig)} chars)")
except Exception as ex:
    print(f"✗ Sign failed: {ex}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("DEBUG COMPLETE")
print("=" * 60)

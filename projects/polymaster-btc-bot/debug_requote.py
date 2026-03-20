#!/usr/bin/env python3
"""Minimal FastRequote debug"""

import sys
from pathlib import Path
from decimal import Decimal

P = Path(__file__).parent.absolute()
sys.path.insert(0, str(P))

print("=" * 60)
print("DEBUG: FastRequote Engine")
print("=" * 60)

# Try to import and inspect
try:
    from core.fast_requote import OrderSigner, FastRequoteEngine
    print("✓ Imports OK")
except Exception as e:
    print(f"✗ Import: {e}")
    sys.exit(1)

# Check class signature
import inspect
sig = inspect.signature(FastRequoteEngine.__init__)
params = list(sig.parameters.keys())
print(f"\nFastRequoteEngine.__init__ params: {params}")

# Try creating instance
for test_params in [
    {"market": "BTC-USD"},
    {"market": "BTC-USD", "fee_rate_bps": 10},
    {"market": "BTC-USD", "lookback_minutes": 5},
]:
    try:
        engine = FastRequoteEngine(**test_params)
        print(f"✓ Created: {list(test_params.keys())}")
        break
    except Exception as ex:
        print(f"✗ {list(test_params.keys())}: {ex}")
else:
    print("✗ Cannot create instance")
    sys.exit(1)

# List all methods
all_methods = sorted([m for m in dir(engine) if not m.startswith('_')])
print(f"\nAll methods ({len(all_methods)}):")
for m in all_methods[:15]:
    obj = getattr(engine, m)
    kind = "func" if callable(obj) else "prop"
    print(f"  {kind:4s} {m}")

# Test signer
print("\nOrderSigner test:")
signer = OrderSigner(api_secret="test")
payload = {
    "market": "BTC-USD", "side": "BUY",
    "price": "0.85", "size": "5.00",
    "feeRateBps": 10, "timestamp": 1234567890
}
sig = signer.sign_order(payload)
print(f"✓ Signed OK: {sig[:32]}...")

# Final status
print("\n" + "=" * 60)
if 'update_price' in all_methods or 'current_quote' in all_methods:
    print("✓ Core methods available - READY")
else:
    print("⚠ Missing critical methods")
print("=" * 60)

#!/usr/bin/env python3
import sys
from pathlib import Path
from decimal import Decimal

P = Path(__file__).parent.absolute()
sys.path.insert(0, str(P))

try:
    from core.fast_requote import OrderSigner, FastRequoteEngine
    print("OK: imports work")
except Exception as e:
    print(f"FAIL import: {e}")
    exit(1)

# Check what FastRequoteEngine needs
import inspect
sig = inspect.signature(FastRequoteEngine.__init__)
print(f"__init__ params: {list(sig.parameters.keys())}")

# Create instance - try different parameters
for params in [
    {"market": "BTC-USD"},
    {"market": "BTC-USD", "fee_rate_bps": 10},
    {"market": "BTC-USD", "lookback_minutes": 5},
]:
    try:
        engine = FastRequoteEngine(**params)
        print(f"OK: created with {list(params.keys())}")
        break
    except TypeError as te:
        print(f"SKIP: {list(params.keys())} -> {te}")
        continue
else:
    print("FAIL: couldn't create instance")
    exit(1)

# List available methods
methods = [m for m in dir(engine) if not m.startswith('_')]
print(f"Methods ({len(methods)}): {', '.join(sorted(methods)[:8])}")

# Test signer
signer = OrderSigner(api_secret="test")
payload = {"market": "BTC-USD", "side": "BUY", "price": "0.85", "size": "5.00", "feeRateBps": 10, "timestamp": 1234567890}
sig = signer.sign_order(payload)
print(f"OK: signed ({len(sig)} chars)")

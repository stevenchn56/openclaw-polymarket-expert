#!/usr/bin/env python3
import sys
from decimal import Decimal
sys.path.insert(0, '.')

try:
    from strategies.btc_window_5m import BTCWindowStrategy as Btc
    s = Btc()
    
    # Try to call the method
    result = s.update_price_with_quotation(Decimal('0.85'))
    print("SUCCESS! Result type:", type(result).__name__)
    if isinstance(result, dict):
        print("Keys:", list(result.keys()))
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

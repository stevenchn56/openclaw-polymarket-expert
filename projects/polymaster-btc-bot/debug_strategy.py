#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from strategies.btc_window_5m import BTCWindowStrategy as Btc

s = Btc()
print("=== All Public Attributes ===")
for attr in dir(s):
    if not attr.startswith('_'):
        val = getattr(s, attr)
        if not callable(val):
            print(f"{attr}: {val}")

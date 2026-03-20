#!/usr/bin/env python3
"""Minimal Test - just check if modules work"""

import time

# Add paths
import sys
from pathlib import Path
PROJECT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

print("Testing minimal imports...")

# Try direct file import
try:
    import strategies.btc_window_5m as btc
    print(f"✓ strategies loaded: {type(btc)}")
    
    # Check class
    if hasattr(btc, 'BTCWindowStrategy'):
        strategy = btc.BTCWindowStrategy(lookback_minutes=5)
        print(f"✓ Strategy instance created")
        
        # List methods
        methods = [m for m in dir(strategy) if not m.startswith('_') and callable(getattr(strategy, m))]
        print(f"✓ Available methods ({len(methods)}):")
        for m in sorted(methods)[:10]:
            print(f"     • {m}")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

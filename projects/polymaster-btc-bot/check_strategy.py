#!/usr/bin/env python3
"""Check strategy structure"""

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()
print(f"Project dir: {PROJECT_DIR}")
print(f"CWD: {Path.cwd()}")

sys.path.insert(0, str(PROJECT_DIR))
print(f"\nAdded to sys.path: {PROJECT_DIR}")

# Now try importing
try:
    # Import as file, not module
    import importlib.util
    spec = importlib.util.spec_from_file_location("btc_window_5m", PROJECT_DIR / "strategies" / "btc_window_5m.py")
    btc_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(btc_module)
    
    print("\n✅ Module loaded successfully!")
    print("\nAvailable classes/functions:")
    for name in dir(btc_module):
        if not name.startswith('_'):
            obj = getattr(btc_module, name)
            if callable(obj):
                print(f"  - {name} ({type(obj).__name__})")
    
    # Check BTCWindowStrategy
    if hasattr(btc_module, 'BTCWindowStrategy'):
        StrategyClass = getattr(btc_module, 'BTCWindowStrategy')
        print(f"\n🔍 Strategy class methods:")
        
        instance = StrategyClass(lookback_minutes=5)
        
        public_methods = [m for m in dir(instance) if not m.startswith('_')]
        for method in sorted(public_methods):
            print(f"  - {method}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

#!/usr/bin/env python3
"""Check if backtest_enhanced.py exists and is valid"""

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()
backtest_path = PROJECT_DIR / "backtest_enhanced.py"

print("=" * 60)
print("BACKTEST ENHANCED.PY - STATUS CHECK")
print("=" * 60)

# Check file existence
if not backtest_path.exists():
    print(f"❌ File NOT FOUND: {backtest_path}")
    
    # List available alternatives
    all_py = list(PROJECT_DIR.glob("*backtest*.py"))
    if all_py:
        print(f"\nFound {len(all_py)} similar files:")
        for f in all_py:
            size = f.stat().st_size
            date = f.stat().st_mtime
            from datetime import datetime
            dt = datetime.fromtimestamp(date).strftime("%Y-%m-%d %H:%M")
            print(f"  • {f.name} ({size:,} bytes, last modified: {dt})")
    else:
        print("\nNo backtest files found!")
        
        # Show what IS available
        py_files = sorted(list(PROJECT_DIR.glob("*.py")))[:15]
        if py_files:
            print(f"\nAvailable .py files (showing first 15):")
            for f in py_files:
                print(f"  - {f.name}")
    exit(1)

# File exists - check status
print(f"✅ File exists")
print(f"   Path: {backtest_path}")

# Get file stats
stats = backtest_path.stat()
size_bytes = stats.st_size
size_kb = size_bytes / 1024
size_mb = size_bytes / (1024 * 1024)

lines = 0
try:
    with open(backtest_path, 'r') as f:
        lines = sum(1 for _ in f)
except Exception as e:
    print(f"⚠ Cannot read lines: {e}")

print(f"   Size: {size_bytes:,} bytes ({size_kb:.1f} KB, {size_mb:.2f} MB)")
print(f"   Lines: {lines:,}")
print(f"   Last modified: {datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M')}")

# Check Python syntax
print(f"\n🔍 Syntax check...")
try:
    import ast
    with open(backtest_path, 'r') as f:
        source = f.read()
    ast.parse(source)
    print(f"✅ Python syntax valid")
except SyntaxError as se:
    print(f"❌ Syntax error: {se}")
    exit(1)

# Check imports
print(f"\n📦 Import dependencies...")
missing_imports = []
required_modules = ['pandas', 'numpy', 'requests', 'matplotlib']

for module in required_modules:
    try:
        __import__(module)
        print(f"  ✓ {module}")
    except ImportError:
        print(f"  ✗ {module} MISSING")
        missing_imports.append(module)

if missing_imports:
    print(f"\n⚠ Missing modules: {', '.join(missing_imports)}")
    print(f"Install with: pip3 install {' '.join(missing_imports)}")

# Summary
print(f"\n" + "=" * 60)
if len(missing_imports) == 0:
    print("  ✅ READY TO RUN BACKTEST")
else:
    print(f"  ⚠ NEEDS {len(missing_imports)} MODULE(S) BEFORE RUNNING")
print("=" * 60)

print(f"\n💡 To run: python3 backtest_enhanced.py")

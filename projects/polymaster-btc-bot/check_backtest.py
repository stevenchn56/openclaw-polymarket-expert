#!/usr/bin/env python3
"""Quick check of backtest script structure"""

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()
backtest_path = PROJECT_DIR / "backtest_enhanced.py"

print("=" * 60)
print("  BACKTEST SCRIPT STRUCTURE CHECK")
print("=" * 60)
print(f"Path: {backtest_path}")
print(f"Exists: {backtest_path.exists()}")

if not backtest_path.exists():
    print("\n❌ File not found!")
    # List what IS available
    files = list(PROJECT_DIR.glob("backtest*.py"))
    if files:
        print(f"\nFound similar files:")
        for f in files:
            print(f"  - {f.name} ({f.stat().st_size} bytes)")
    else:
        print("\nNo backtest files found.")
        all_py = list(PROJECT_DIR.glob("*.py"))
        print(f"\nAvailable .py files in project dir ({len(all_py)}):")
        for f in all_py[:15]:
            print(f"  - {f.name}")
    exit(1)

# Read file info
size_bytes = backtest_path.stat().st_size
with open(backtest_path, 'r') as f:
    lines = f.readlines()

print(f"Size: {size_bytes:,} bytes")
print(f"Lines: {len(lines)}")

# Check key sections
print("\n📋 Script Structure:")
print("-" * 60)

in_class = False
current_indent = 0
sections = []

for i, line in enumerate(lines[:200], 1):  # First 200 lines
    stripped = line.strip()
    
    # Skip empty/comment lines
    if not stripped or stripped.startswith('#'):
        continue
    
    # Count indentation
    indent = len(line) - len(line.lstrip())
    
    # Class definition
    if stripped.startswith('class '):
        class_name = stripped.split('(')[0].replace('class ', '')
        print(f"Line {i:4d}: class {class_name}")
        in_class = True
        current_indent = indent
        continue
    
    # Top-level function
    if stripped.startswith('def ') and indent <= 0:
        func_name = stripped.split('(')[0].replace('def ', '')
        print(f"Line {i:4d}: def {func_name}(...)")
        in_class = False
        continue
    
    # Main block
    if '__main__' in stripped or 'if __name__' in stripped:
        print(f"Line {i:4d}: ___main___ block starts")
        continue
    
    # Print first few functions/classes
    if len(sections) < 10:
        sections.append((i, line[:80].rstrip()))

print(f"\nFirst {min(10, len(lines))} code lines:")
for ln, content in sections[:10]:
    print(f"  Line {ln:4d}: {content}")

# Check imports
print("\n🔧 Import Statements:")
print("-" * 60)
imports_found = []
for i, line in enumerate(lines[:100], 1):
    if line.strip().startswith(('import ', 'from ')):
        imports_found.append((i, line.strip()))
        
for ln, imp in imports_found:
    print(f"  Line {ln:4d}: {imp}")

print(f"\nTotal imports: {len(imports_found)}")

# Summary
print("\n" + "=" * 60)
print("  ✅ Backtest script analysis complete")
print("=" * 60)
print(f"\n💡 Next steps:")
print(f"   1. Run full test: python3 {backtest_path.name}")
print(f"   2. Check output carefully for any errors")
print(f"   3. Review results directory after completion")
print("=" * 60)

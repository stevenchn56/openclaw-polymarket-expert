#!/usr/bin/env python3
from pathlib import Path

memory_file = Path.home() / ".openclaw" / "workspace" / "MEMORY.md"
print(f"File exists: {memory_file.exists()}")
print(f"Full path: {memory_file.absolute()}")

if memory_file.exists():
    with open(memory_file, 'r') as f:
        lines = f.readlines()
    print(f"\nTotal lines: {len(lines)}")
    print("\nFirst 40 lines:")
    print("-"*70)
    for i, line in enumerate(lines[:40], 1):
        print(f"{i:3d}: {line}", end='')

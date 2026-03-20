#!/usr/bin/env python3
"""Update MEMORY.md with today's major milestone"""

from pathlib import Path
from datetime import datetime

workspace = Path.home() / ".openclaw" / "workspace"
memory_file = workspace / "MEMORY.md"

print(f"Memory file path: {memory_file}")
print(f"File exists: {memory_file.exists()}")
if memory_file.exists():
    print(f"File size: {memory_file.stat().st_size} bytes")
    print(f"Last modified: {datetime.fromtimestamp(memory_file.stat().st_mtime)}")

# Check if we can read it
try:
    with open(memory_file, 'r') as f:
        content = f.read()
    print(f"\n✅ Can read file - {len(content.splitlines())} lines")
    print("\n--- First 500 chars ---")
    print(content[:500])
except Exception as e:
    print(f"\n❌ Cannot read: {e}")
    print("Trying to write backup...")
    
    # Create backup first
    backup_file = workspace / "MEMORY_backup.md"
    try:
        import shutil
        shutil.copy(memory_file, backup_file)
        print(f"✅ Created backup at {backup_file}")
    except Exception as e:
        print(f"❌ Backup failed: {e}")

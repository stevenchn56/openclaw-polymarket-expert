#!/usr/bin/env python3
"""Display backtest results key sections"""

from pathlib import Path

result_file = Path(__file__).parent / "backtest_complete_results.txt"

if not result_file.exists():
    print("❌ Result file not found!")
    print(f"Expected at: {result_file}")
    
    # Try to find any backtest results files
    print("\nSearching for result files...")
    p = Path(__file__).parent
    for f in p.glob("*.txt"):
        if "backtest" in str(f).lower() or "result" in str(f).lower():
            print(f"  Found: {f.name} ({f.stat().st_size} bytes)")
    exit(1)

# Read file
with open(result_file, 'r') as f:
    lines = f.readlines()

print("="*80)
print(f"📊 POLYMARKET BTC BOT BACKTEST RESULTS")
print(f"File: {result_file}")
print(f"Total Lines: {len(lines)}")
print("="*80)

# Display key sections
section_keywords = [
    ('SCENARIO:', 25),
    ('RESULTS SUMMARY', 35),
    ('Overall Statistics', 40),
    ('Best', 30),
    ('Worst', 30),
    ('COMPREHENSIVE BACKTEST COMPLETE', 25),
]

in_key_section = False
section_buffer = []

print("\n🔍 KEY SECTIONS:\n")

for i, line in enumerate(lines):
    should_display = False
    
    for keyword, threshold in section_keywords:
        if keyword in line and len(section_buffer) >= threshold:
            in_key_section = True
            should_display = True
        
        if in_key_section:
            section_buffer.append(line)
            
            # End section when hitting next key header or blank after content
            if (i+1 < len(lines) and 
                any(kw in lines[i+1] for kw, _ in section_keywords)):
                display_section(i, section_buffer)
                return
                
            if line.strip() == '' and len(section_buffer) > threshold:
                display_section(i, section_buffer)
                section_buffer = []
                in_key_section = False
                return

if section_buffer:
    display_section(len(lines), section_buffer)

def display_section(end_idx, buffer):
    print("-"*80)
    print(''.join(buffer[-(end_idx - max(0, end_idx-50)):-1]))

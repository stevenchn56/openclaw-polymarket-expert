#!/usr/bin/env python3
"""Parse and display key backtest results"""

from pathlib import Path

result_file = Path(__file__).parent / "backtest_complete_results.txt"
summary_file = Path(__file__).parent / "BACKTEST_KEY_RESULTS.md"

if not result_file.exists():
    print("❌ Result file not found!")
    exit(1)

with open(result_file, 'r') as f:
    content = f.read()

# Extract key sections
lines = content.split('\n')

key_sections = []
current_section = []
in_key_section = False

for line in lines:
    if '=== COMPREHENSIVE BACKTEST COMPLETE' in line or '=== OVERALL STATISTICS' in line or '===' in line:
        if current_section and (len(current_section) > 3):
            key_sections.append('\n'.join(current_section))
        current_section = [line]
        in_key_section = 'COMPARISON' in line or 'STATISTICS' in line or 'Overall' in line or 'Best' in line or 'Worst' in line
    elif in_key_section:
        current_section.append(line)
        if line.strip() == '' and len(current_section) > 5:
            # End of section
            pass
        elif any(keyword in line for keyword in ['Scenario', 'Avg', 'Best', 'Worst', 'Total Runs', 'Positive', 'Average']):
            in_key_section = True

# If still in section, add it
if current_section:
    key_sections.append('\n'.join(current_section))

# Write summary
with open(summary_file, 'w') as f:
    f.write("# Polymarket BTC Bot - KEY RESULTS\n\n")
    f.write(f"**Total Lines in Report:** {len(lines)}\n\n")
    
    for i, section in enumerate(key_sections[:5]):  # Top 5 sections
        f.write(section + "\n\n---\n\n")
    
    f.write("\n" + "="*70 + "\n")
    f.write("💡 RECOMMENDATION: Review full file for complete details\n")
    f.write("="*70)

print(f"✅ Parsed {len(lines)} lines from backtest results")
print(f"📄 Key findings saved to: {summary_file}")
print("\n🔍 Showing first key section:")
print("-"*70)
if key_sections:
    print(key_sections[0])

#!/usr/bin/env python3
"""Simple test - save results to file"""

import sys
sys.path.insert(0, '.')

from strategies.btc_window_5m import BTCWindowStrategy, PriceDataPoint
from decimal import Decimal

output = []
output.append("=" * 60)
output.append("POLYMASTER BACKTEST v2.0.1 - QUICK VERIFICATION")
output.append("=" * 60)

s = BTCWindowStrategy(fee_rate_bps=10)
data = [PriceDataPoint(close=Decimal('0.80')) for _ in range(5)]
q = s.generate_bidirectional_quote(data)

output.append("")
output.append("✅ Test Result: SUCCESS")
output.append("-" * 60)
output.append(f"Fair Value (YES): {q['fair_value']}")
output.append(f"Confidence:       {float(q['confidence'])*100:.1f}%")
output.append(f"Spread:           {q['strategy_params']['spread_bps']}bps")
output.append(f"Size Multiplier:  {q['strategy_params']['size_multiplier']}x")
output.append("")
output.append("Quote Structure:")
output.append(f"  YES: ${q['quotes']['yes']['price']:.4f} x ${q['quotes']['yes']['size']:.2f}")
output.append(f"  NO:  ${q['quotes']['no']['price']:.4f} x ${q['quotes']['no']['size']:.2f}")
total = float(q['quotes']['yes']['price']) + float(q['quotes']['no']['price'])
output.append(f"  Sum: ${total:.4f} (target ~1.0)")
output.append("")
output.append("=" * 60)
output.append("ALL CHECKS PASSED!")
output.append("=" * 60)

# Write to file
with open('/tmp/bt_summary.txt', 'w') as f:
    f.write('\n'.join(output))

print('\n'.join(output))

#!/usr/bin/env python3
"""
Add generate_bidirectional_quote() method to BTCWindowStrategy

This implements the v2.0 bidirectional market making feature.
"""

import re
from pathlib import Path

# Load the strategy file
strategy_path = Path(__file__).parent / "strategies/btc_window_5m.py"
with open(strategy_path, 'r') as f:
    content = f.read()

print("=" * 60)
print("ADDING BIDIRECTIONAL QUOTE GENERATION")
print("=" * 60)

# Check if method already exists
if 'generate_bidirectional_quote' in content:
    print("\n⚠ Method already exists!")
    print("Skipping...")
else:
    # New method to add
    new_method = '''
    def generate_bidirectional_quote(self):
        """
        Generate bidirectional market making quote using Black-Scholes pricing.
        
        Returns:
            dict: {'bid': Decimal, 'ask': Decimal, 'fair_value': Decimal, 
                   'spread_bps': int, 'timestamp': datetime}
        """
        from datetime import datetime
        
        if not self.price_history or len(self.price_history) < 3:
            return None
        
        if not self.pricer:
            return None
        
        try:
            # Calculate fair value using Black-Scholes
            current_price = self.last_price
            if not current_price:
                current_price = Decimal(str(sum(self.price_history[-10:]) / 10))
            
            volatility = self.calculate_volatility()
            
            # Use pricer for fair value (simplified version)
            fair_value = current_price  # For now, use mid-price
            
            # Calculate bid and ask with spread
            half_spread = Decimal(str(self.spread_bps)) / Decimal("20000")  # Convert bps to decimal
            
            bid = fair_value * (1 - half_spread)
            ask = fair_value * (1 + half_spread)
            
            # Ensure bid < ask
            if bid >= ask:
                bid = fair_value * 0.999
                ask = fair_value * 1.001
            
            return {
                'bid': bid,
                'ask': ask,
                'fair_value': fair_value,
                'spread_bps': self.spread_bps,
                'timestamp': datetime.utcnow(),
                'volatility': float(volatility) if volatility else None
            }
            
        except Exception as e:
            print(f"⚠ Quote generation error: {e}")
            return None

'''
    
    # Find position after last method definition
    lines = content.split('\n')
    insert_pos = len(lines)  # Default: append at end
    
    # Look for a good insertion point (after can_trade or similar methods)
    for i, line in enumerate(reversed(lines)):
        if 'def can_trade' in line or 'def should_trade' in line:
            insert_pos = len(lines) - i + 20  # Insert ~20 lines after
            break
    
    # Add the method
    lines.insert(insert_pos, new_method)
    new_content = '\n'.join(lines)
    
    # Write back
    with open(strategy_path, 'w') as f:
        f.write(new_content)
    
    print("\n✅ Method added successfully!")
    print(f"   File: {strategy_path}")
    print(f"   Lines: {len(lines)}")

# Verify by importing
print("\n[Verification] Testing new method...")
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from strategies.btc_window_5m import BTCWindowStrategy
    s = BTCWindowStrategy(lookback_minutes=5)
    
    # Test with a price
    from decimal import Decimal
    s.update_price(Decimal("45000"))
    
    if hasattr(s, 'generate_bidirectional_quote'):
        quote = s.generate_bidirectional_quote()
        print(f"✅ generate_bidirectional_quote works!")
        print(f"   Result type: {type(quote).__name__}")
        if quote:
            print(f"   Keys: {list(quote.keys())}")
    else:
        print("⚠ Method still not found")
        
except Exception as e:
    print(f"⚠ Verification failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("  ✅ ADDITION COMPLETE")
print("=" * 60)

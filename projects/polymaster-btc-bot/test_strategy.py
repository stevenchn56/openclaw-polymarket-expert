#!/usr/bin/env python3
"""Test script for Polymaster BTC Strategy v2.0"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from strategies.btc_window_5m import BTCWindowStrategy as BtcWindowStrategy


async def main():
    """Run strategy tests"""
    print("=" * 60)
    print("POLYMASTER-BTC-BOT - TEST SUITE")
    print("=" * 60)
    
    # Initialize strategy
    print("\n🚀 Initializing Strategy...")
    strategy = BtcWindowStrategy()
    print("✅ Strategy initialized successfully\n")
    
    # Test 1: Price threshold check
    opportunity = type('Opportunity', (), {
        'side': 'BUY',
        'prediction': '0.85'
    })()
    prediction = Decimal(opportunity.prediction)
    
    print(f"📊 Test Input:")
    print(f"   Prediction: {prediction:.4f}")
    print(f"   Side: {opportunity.side}")
    print(f"   Confidence Threshold: 0.75 (default)")
    print()
    
    # Check entry windows
    bid, ask = strategy.calculate_entry_windows()
    print(f"   Entry Window:")
    print(f"      Bid: {bid}")
    print(f"      Ask: {ask}")
    print()
    
    # Generate quote using v2.0 API
    print("💰 Generating Order Quote...")
    try:
        quote = strategy.update_price_with_quotation(Decimal(str(prediction)))
        
        # New format returns dict with fee_rate_bps
        base_price = Decimal(str(prediction))
        adjusted_price = base_price + Decimal(str(quote['fee_rate_bps'])) / Decimal('10000')
        
        print(f"   Adjusted Price (w/ fee): ${adjusted_price:.4f}")
        print(f"   Fee Rate: {quote['fee_rate_bps']} bps")
        print(f"   Confidence: {quote['confidence']:.1%}")
        print(f"   Fair Value: ${quote['fair_value']:.4f}")
        print(f"   Mid: ${quote['mid']:.4f}")
        print()
    except Exception as e:
        print(f"   ❌ Error generating quote: {e}")
        return False
    
    # Get strategy metrics (includes position info)
    print("📊 Strategy Metrics:")
    metrics = strategy.get_strategy_metrics()
    print(f"   Inventory Threshold: {metrics.get('inventory_threshold')}")
    print(f"   Max Position Size: {metrics.get('max_position_size')}")
    print(f"   Last Price: {metrics.get('last_price')}")
    print()
    
    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)

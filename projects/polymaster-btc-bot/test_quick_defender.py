#!/usr/bin/env python3
"""Quick test to verify MEV defender initializes correctly"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*80)
print("🧪 QUICK MEV DEFENDER TEST")
print("="*80)

try:
    # Test basic import
    from order_attack_defender import OrderAttackDefender
    print("✅ Successfully imported OrderAttackDefender")
    
    # Test initialization
    print("\nInitializing defender with mock credentials...")
    defender = OrderAttackDefender(
        api_key="test_api_key",
        private_key="test_private_key",
        my_address="0xTestAddress1234567890abcdef1234567890",
        monitoring_interval_seconds=2.0,
        blacklist_duration_hours=1,
        emergency_cooldown_minutes=1
    )
    
    print(f"✅ Defender created!")
    print(f"   My address: {defender.my_address}")
    print(f"   Monitoring interval: {defender.monitoring_interval}s")
    
    # Check initial status
    status = defender.get_status()
    print(f"\nInitial status:")
    print(f"   Active: {status.active}")
    print(f"   Mode: {status.current_mode}")
    print(f"   Known threats: {status.known_threats_count}")
    
    print("\n" + "="*80)
    print("🎉 ALL CHECKS PASSED!")
    print("="*80)
    print("\nNext steps:")
    print("1. Review your .env file for real API keys")
    print("2. Run full simulation: python main.py --simulate-only --trades=5")
    print("3. If OK, proceed to small live trades tomorrow")
    print("="*80)
    
except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

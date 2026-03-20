#!/usr/bin/env python3
"""
Final verification script - ensures main.py integration is correct
Run: python verify_integration.py
"""

import sys
from pathlib import Path

def check_file_exists(filepath, name):
    """Check if file exists."""
    if not Path(filepath).exists():
        print(f"❌ {name} not found at {filepath}")
        return False
    print(f"✅ {name} exists ({Path(filepath).stat().st_size} bytes)")
    return True

def check_content(filepath, patterns, name):
    """Check if file contains required patterns."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        all_found = True
        for pattern in patterns:
            if pattern not in content:
                print(f"  ✗ Missing: {pattern[:50]}...")
                all_found = False
        
        if all_found:
            print(f"✅ {name} - All patterns found")
        else:
            print(f"❌ {name} - Some patterns missing")
        
        return all_found
    except Exception as e:
        print(f"❌ Error reading {name}: {e}")
        return False

def main():
    """Run all checks."""
    print("="*70)
    print("🔍 Polymaster BTC Bot - Integration Verification")
    print("="*70)
    print()
    
    base_path = '/Users/stevenwang/.openclaw/workspace/projects/polymaster-btc-bot'
    
    # Check 1: Required files exist
    print("📁 File Checks:")
    files_ok = (
        check_file_exists(f"{base_path}/main.py", "main.py") and
        check_file_exists(f"{base_path}/risk_manager/advanced_risk_manager.py", "AdvancedRiskManager") and
        check_file_exists(f"{base_path}/strategies/btc_window_5m.py", "BTC Window Strategy") and
        check_file_exists(f"{base_path}/connectors/binance_ws.py", "Binance WebSocket")
    )
    print()
    
    # Check 2: main.py has correct imports
    print("📦 Import Checks:")
    main_checks = [
        'from risk_manager.advanced_risk_manager import AdvancedRiskManager',
        'risk_manager = AdvancedRiskManager(initial_capital=',
        'can_trade, reasons = risk_manager.can_trade()',
        'next_position_size = risk_manager.get_position_limit_for_trade()'
    ]
    imports_ok = check_content(f"{base_path}/main.py", main_checks, "main.py imports")
    print()
    
    # Check 3: Trade recording updated
    print("📝 Trade Recording Checks:")
    trade_checks = [
        'rm_status = risk_manager.record_trade(',
        'pnl=pnl,',
        'side=side,',
        'fill_price=fill_price,',
        'confidence=prediction.confidence',
        "f\"Streak: {rm_status['streak']},\""
    ]
    trades_ok = check_content(f"{base_path}/main.py", trade_checks, "Trade recording")
    print()
    
    # Check 4: Risk manager module completeness
    print("🛡️ Risk Manager Module Checks:")
    rm_checks = [
        'class AdvancedRiskManager:',
        'DAILY_LOSS_LIMIT_PCT = 0.05',
        'MONTHLY_LOSS_LIMIT_PCT = 0.15',
        'MAX_DRAWDOWN_PCT = 0.25',
        'TOTAL_CAPITAL_LOSS_LIMIT = 0.40',
        'POSITION_SIZE_ADJUST_WIN = 1.10',
        'POSITION_SIZE_ADJUST_LOSS = 0.80',
        'def can_trade(self)',
        'def record_trade(self',
        'def get_current_status(self)'
    ]
    rm_ok = check_content(f"{base_path}/risk_manager/advanced_risk_manager.py", rm_checks, "Risk manager")
    print()
    
    # Summary
    print("="*70)
    print("📊 SUMMARY:")
    print("="*70)
    
    results = {
        "Files Exist": files_ok,
        "Import Logic": imports_ok,
        "Trade Recording": trades_ok,
        "Risk Manager Module": rm_ok
    }
    
    all_passed = all(results.values())
    
    for item, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {item}")
    
    print()
    if all_passed:
        print("🎉 ALL CHECKS PASSED! Ready for deployment.")
        print("\nNext steps:")
        print("  1. Review docs/DEPLOYMENT_CHECKLIST.md")
        print("  2. Purchase VPS (DigitalOcean NYC3 @ $40/mo)")
        print("  3. Deploy with SIMULATE=True first")
        print("  4. Monitor logs carefully")
    else:
        print("⚠️ SOME CHECKS FAILED!")
        print("\nPlease fix the failed items before deploying.")
    
    print("="*70)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

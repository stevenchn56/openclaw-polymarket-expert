#!/usr/bin/env python3
"""
Quick script to update main.py for AdvancedRiskManager integration
Run: python update_main.py
"""

import re

def fix_main_py():
    filepath = '/Users/stevenwang/.openclaw/workspace/projects/polymaster-btc-bot/main.py'
    
    with open(filepath, 'r') as f:
        original = f.read()
    
    content = original
    
    # 1. Fix imports - replace AutoPauseManager with AdvancedRiskManager
    if 'from risk_manager.auto_pause import AutoPauseManager' in content:
        content = content.replace(
            'from risk_manager.auto_pause import AutoPauseManager',
            'from risk_manager.advanced_risk_manager import AdvancedRiskManager'
        )
        print("✓ Fixed imports")
    
    # 2. Fix instantiation - add proper initialization
    if 'auto_pause = AutoPauseManager()' in content:
        content = content.replace(
            'auto_pause = AutoPauseManager()',
            'risk_manager = AdvancedRiskManager(initial_capital=float(os.getenv("TRADING_CAPITAL", "50.0")))'
        )
        print("✓ Fixed instantiation")
    
    # 3. Fix can_trade check
    old_check = '''if auto_pause.is_paused():
            logger.warning(f"Trading paused: {auto_pause.pause_reason}")
            await asyncio.sleep(60)  # Wait before retry
            continue
        
        next_position_size = POSITION_SIZE_USD'''
    
    new_check = '''# Check if trading allowed (advanced risk manager)
        can_trade, reasons = risk_manager.can_trade()
        if not can_trade:
            logger.warning(f"⚠️ Trading blocked: {' | '.join(reasons)}")
            await asyncio.sleep(60)  # Wait before retry
            continue
        
        next_position_size = risk_manager.get_position_limit_for_trade()'''
    
    if old_check in content:
        content = content.replace(old_check, new_check)
        print("✓ Fixed trading check logic")
    
    # 4. Fix trade recording
    old_record = '''# Record trade result for statistics (placeholder)
            if fill_success:
                pnl = calculate_pnl(fill_price, prediction.confidence, side)
                logger.info(f"✅ Trade executed: {side} @ ${fill_price:.4f}, PnL: ${pnl:+.2f}")
                # TODO: Add to position tracker'''
    
    new_record = '''# Record trade result for advanced risk management
            if fill_success:
                pnl = calculate_pnl(fill_price, prediction.confidence, side)
                
                # Update risk manager with this trade result
                rm_status = risk_manager.record_trade(
                    pnl=pnl,
                    side=side,
                    fill_price=fill_price,
                    confidence=prediction.confidence
                )
                
                logger.info(f"✅ Trade #{risk_manager.total_trades}: {side} @ ${fill_price:.4f}, "
                           f"PnL: ${pnl:+.2f}, "
                           f"Streak: {rm_status['streak']}, "
                           f"Win rate: {rm_status['win_rate']:.1f}%")
                
                # Track position
                position_tracker.add_position(side, next_position_size, fill_price)'''
    
    if old_record in content:
        content = content.replace(old_record, new_record)
        print("✓ Fixed trade recording logic")
    
    # Write back
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"\n✅ Successfully updated {filepath}")
    print(f"Made {len(original.split(chr(10))) - len(content.split(chr(10))) + 4} changes")

if __name__ == "__main__":
    try:
        fix_main_py()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

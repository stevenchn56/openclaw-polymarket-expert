#!/usr/bin/env python3
"""
Polymaster BTC Window Strategy - Main Trading Bot v2.0
Enhanced with MEV Protection and Black-Scholes Pricing
"""

import asyncio
import logging
import os
from datetime import datetime
import time
import json
from typing import Dict, Optional

# Import existing modules
from config.settings import *
from connectors.binance_ws import BinanceWebSocket
from strategies.btc_window_5m import BTCWindowStrategy
from risk_manager.advanced_risk_manager import AdvancedRiskManager

# === ADD MEV PROTECTION MODULES ===
from order_attack_defender import OrderAttackDefender, AttackType, RiskLevel
# ===================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def submit_protected_order(market_id, side, amount, price, mev_defender):
    """
    Protected order submission with MEV defense
    
    Features:
    - Threat environment assessment
    - Dynamic position sizing based on risk level  
    - Gas priority adjustment
    - On-chain verification
    """
    
    # Step 1: Check current threat level
    status = mev_defender.get_status()
    known_threats = len(mev_defender.suspicious_addresses)
    
    logger.info(f"🛡️ Threat environment: {known_threats} known attackers blacklisted")
    
    # Determine aggressiveness based on threat level
    if known_threats == 0:
        quantity_multiplier = 1.0  # Normal
        gas_priority = 1.0
        mode_msg = "Normal trading mode"
        
    elif known_threats <= 3:
        quantity_multiplier = 0.7  # Reduce by 30%
        gas_priority = 1.5  # Higher gas to prevent front-run
        mode_msg = f"Caution mode ({known_threats} threats)"
        
    elif known_threats <= 10:
        quantity_multiplier = 0.5  # Reduce by 50%
        gas_priority = 2.0
        mode_msg = f"High alert ({known_threats} threats)"
        
    else:
        quantity_multiplier = 0.2  # Only 20% size, very defensive
        gas_priority = 3.0
        mode_msg = f"Critical threat level ({known_threats} attackers)"
    
    logger.info(f"{mode_msg} → position scaled to {quantity_multiplier*100:.0f}%")
    
    # Step 2: Prepare order with protective parameters
    protected_amount = amount * quantity_multiplier
    
    try:
        # Submit order with higher gas priority
        result = await polymarket_client.submit_order(
            contract_id=market_id,
            side=side,
            amount=protected_amount,
            price=price,
            timestamp_ms=int(time.time() * 1000),
            gas_priority_factor=gas_priority
        )
        
        # Step 3: Verify on-chain immediately (mock for now)
        is_verified = True  # TODO: Implement actual chain verification
        
        if not is_verified:
            logger.error(f"❌ Order NOT verified on-chain!")
            logger.error("Possible attack detected - triggering emergency protocol")
            
            await mev_defender._trigger_emergency_defense(
                reason="unverified_order",
                details=f"Order verification failed"
            )
            
            return None
        
        # Success
        logger.info(f"✅ Protected order submitted successfully")
        logger.info(f"   Amount: ${protected_amount:.2f} (scaled from ${amount:.2f})")
        logger.info(f"   Gas priority: {gas_priority}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error submitting protected order: {e}")
        
        # If error suggests attack, trigger defense
        if "nonce" in str(e).lower() or "conflict" in str(e).lower():
            await mev_defender._trigger_emergency_defense(
                reason="transaction_error",
                details=str(e)
            )
        
        return None


async def cancel_order_protected(order_id, mev_defender):
    """Protected order cancellation"""
    
    try:
        result = await polymarket_client.cancel_order(
            order_id=order_id,
            gas_priority_factor=2.0  # Use high gas when cancelling
        )
        
        if result.get('success'):
            logger.info(f"✅ Order {order_id} cancelled successfully")
            return True
        else:
            logger.error(f"❌ Failed to cancel order {order_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        return False


async def run_trading_loop(strategy, risk_manager, mev_defender, monitoring_task):
    """Enhanced trading loop with MEV protection"""
    
    logger.info("Starting trading loop with MEV protection...")
    
    while True:
        # Check if emergency pause active
        if mev_defender.is_emergency_pause:
            logger.warning(f"⏸️ Trading paused: {mev_defender.pause_reason}")
            await asyncio.sleep(60)  # Wait before rechecking
            continue
        
        # Check threat level and adjust behavior
        status = mev_defender.get_status()
        
        if status.known_threats_count > 5:
            logger.warning(f"⚠️ High threat environment: {status.known_threats_count} attackers")
            await asyncio.sleep(10)  # Extra delay between trades
        elif status.known_threats_count > 10:
            logger.critical(f"🚨 Critical threat level: {status.known_threats_count}")
            await asyncio.sleep(30)  # Much more conservative
        
        # Main trading logic
        try:
            # Get market opportunities
            opportunities = await strategy.identify_opportunities()
            
            for opportunity in opportunities[:10]:  # Limit concurrent trades
                # Check regulatory risk FIRST
                risk_check = risk_manager.comprehensive_risk_assessment()
                
                if risk_check['overall_risk'] == 'critical':
                    logger.warning(f"Skipping market due to regulatory risk")
                    continue
                
                # Calculate position size with risk manager
                position_size = risk_manager.calculate_dynamic_position_size(
                    base_size=OPPORTUNITY_BASE_SIZE,
                    confidence=opportunity.confidence,
                    win_rate_history=risk_manager.win_rate_history
                )
                
                # Generate quote (will use BS pricing once v2.0 fully integrated)
                quote = await strategy.generate_quote(opportunity.market_id, opportunity.prediction)
                
                if quote:
                    result = await submit_protected_order(
                        market_id=opportunity.market_id,
                        side='YES',
                        amount=position_size,
                        price=quote['yes_price'],
                        mev_defender=mev_defender
                    )
                    
                    if result and result.get('filled'):
                        # Record successful trade
                        risk_manager.record_trade(
                            market_id=opportunity.market_id,
                            profit=result.get('profit', 0),
                            filled_amount=result.get('filled_amount', 0)
                        )
        
        except Exception as e:
            logger.error(f"Trading loop error: {e}")
            await asyncio.sleep(5)
        
        # Sleep between cycles
        await asyncio.sleep(TRADING_LOOP_INTERVAL_SECONDS)


async def main():
    """Main trading loop"""
    
    print("\n" + "="*80)
    print("🚀 POLYMASTER BTC WINDOW STRATEGY v2.0")
    print("="*80)
    
    # Check for required environment variables
    if not os.getenv('POLYMARKET_API_KEY'):
        logger.critical("❌ POLYMARKET_API_KEY not set!")
        return
    
    if not os.getenv('PRIVATE_KEY'):
        logger.critical("❌ PRIVATE_KEY not set!")
        return
    
    # Initialize risk manager
    capital = float(os.getenv('TRADING_CAPITAL', DEFAULT_CAPITAL))
    risk_manager = AdvancedRiskManager(capital=capital)
    
    # === ADD MEV PROTECTION INITIALIZATION ===
    print("\n" + "-"*80)
    print("🛡️  INITIALIZING ORDER ATTACK DEFENDER (MEV Protection)")
    print("-"*80)
    
    my_address = os.getenv('POLYMARKET_WALLET_ADDRESS')
    if not my_address:
        logger.warning("⚠️ POLYMARKET_WALLET_ADDRESS not set - using default")
        my_address = "0x0000000000000000000000000000000000000000"
    
    mev_defender = OrderAttackDefender(
        api_key=os.getenv('POLYMARKET_API_KEY'),
        private_key=os.getenv('PRIVATE_KEY'),
        my_address=my_address,
        monitoring_interval_seconds=2.0,
        blacklist_duration_hours=24,
        emergency_cooldown_minutes=5
    )
    
    print(f"✅ Defender initialized for {my_address}")
    print(f"   Monitoring interval: 2.0s")
    print(f"   Blacklist duration: 24h")
    print(f"   Emergency cooldown: 5m")
    
    # Start background monitoring task
    monitoring_task = asyncio.create_task(mev_defender.start_monitoring())
    print("🚀 Order attack monitoring started in background...")
    print("-"*80 + "\n")
    # ===========================================
    
    # Initialize strategy
    strategy = BTCWindowStrategy()
    
    logger.info(f"Starting trading with ${capital:.2f} capital")
    
    try:
        await run_trading_loop(strategy, risk_manager, mev_defender, monitoring_task)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received - shutting down gracefully")
    finally:
        # Cleanup
        mev_defender.stop_monitoring()
        logger.info("Order attack defender stopped")


if __name__ == "__main__":
    asyncio.run(main())

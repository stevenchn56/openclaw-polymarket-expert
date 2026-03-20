# 🛡️ Risk Manager Module - Integration Guide

**Date**: Thursday, March 19, 2026  
**Version**: v1.0  
**Status**: ✅ COMPLETE & TESTED

---

## 🎯 Quick Start (5 Minutes)

### 1️⃣ Import the Module

```python
from core.risk_manager import RiskManager
from decimal import Decimal

# Create instance with default conservative settings
risk_mgr = RiskManager()

# Or customize parameters
custom_config = {
    'max_daily_drawdown_pct': 0.04,
    'max_position_btc': Decimal('3.0'),
}
risk_mgr = RiskManager(config=custom_config)
```

---

### 2️⃣ Validate Trades Before Execution

```python
# Your strategy generates a trade idea
current_price = Decimal('45000')
entry_price = Decimal('45050')
confidence = 75.5  # Your strategy's confidence score
proposed_size = Decimal('3.0')  # BTC amount you want to trade
direction = 'LONG'

# Check if risk manager allows it
is_allowed, reason = risk_mgr.check_trade(
    current_price=current_price,
    entry_price=entry_price,
    confidence=confidence,
    proposed_size=proposed_size,
    direction=direction
)

if not is_allowed:
    print(f"❌ Trade REJECTED: {reason}")
    # Don't execute! Consider smaller size or wait for better conditions
else:
    print(f"✅ Trade allowed: {reason}")
```

---

### 3️⃣ Calculate Optimal Position Size

```python
# Let Risk Manager determine best position
optimal_size = risk_mgr.calculate_position_size(confidence_score=75)

print(f"Optimal position: {optimal_size:.2f} BTC")
# Output will be based on your configured tiers

# This uses BOTH confidence-based AND Kelly criterion
# Chooses the more conservative of the two automatically
```

---

### 4️⃣ Update Balance & Track Performance

```python
# Call this periodically (every few minutes or on price updates)
current_balance = Decimal('10000')  # Your account balance in USDC
positions_open = 2  # How many trades currently open

risk_mgr.update_position_info(
    balance=current_balance,
    positions_open=positions_open
)

# Record each completed trade result
def record_win():
    pnl = Decimal('0.02')  # +BTC profit
    risk_mgr.record_trade_outcome(pnl_btc=pnl, outcome='WIN')

def record_loss():
    pnl = Decimal('-0.03')  # -BTC loss
    risk_mgr.record_trade_outcome(pnl_btc=pnl, outcome='LOSS')
```

---

### 5️⃣ Monitor Status & Get Recommendations

```python
# Comprehensive metrics dashboard
metrics = risk_mgr.get_trading_metrics()
print(f"Current PnL: {metrics['total_pnl_btc']:+.4f} BTC")
print(f"Consecutive losses: {metrics['consecutive_losses']}")
print(f"Total trades today: {metrics['trades_today']}")
print(f"Drawdown: {metrics['current_dd_pct']:.1f}%")

# Actionable recommendations
recs = risk_mgr.get_recommendation()
for warning in recs['warnings']:
    print(f"⚠️ WARNING: {warning}")
for recommendation in recs['recommendations']:
    print(f"💡 SUGGESTION: {recommendation}")
```

---

## 📋 Complete Integration Example

Here's how to integrate Risk Manager into your main trading loop:

```python
from core.risk_manager import RiskManager
from strategies.btc_window_5m import BTCWindowStrategy
from pricing.black_scholes_v2 import BlackScholesPricer
from decimal import Decimal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingSystem:
    def __init__(self):
        # Initialize components
        self.strategy = BTCWindowStrategy(lookback_minutes=5, spread_bps=10)
        self.risk_mgr = RiskManager()
        
        # Load config
        from config.risk_configs import load_config
        config = load_config('MAINNET_CONSERVATIVE_V1')
        self.risk_mgr = RiskManager(config=config)
    
    def run_cycle(self, current_price: Decimal):
        """Main trading loop iteration"""
        
        # Step 1: Get strategy signal
        signal = self.strategy.should_trade(current_price)
        
        if not signal:
            return
        
        # Step 2: Generate quote
        try:
            quote = self.strategy.generate_bidirectional_quote()
        except Exception as e:
            logger.error(f"Failed to generate quote: {e}")
            return
        
        # Step 3: Extract trade parameters
        confidence = 85.0  # Replace with actual strategy confidence metric
        direction = 'BUY' if quote['bid'] else 'SELL'
        proposed_size = Decimal('3.0')  # Your strategy's suggested size
        
        # Step 4: VALIDATE WITH RISK MANAGER ⭐
        is_allowed, reason = self.risk_mgr.check_trade(
            current_price=current_price,
            entry_price=quote['fair_value'],
            confidence=confidence,
            proposed_size=proposed_size,
            direction=direction
        )
        
        if not is_allowed:
            logger.info(f"Trade blocked by risk manager: {reason}")
            return
        
        # Step 5: Calculate optimal position
        optimal_size = self.risk_mgr.calculate_position_size(confidence)
        logger.info(f"Recommended position: {optimal_size:.3f} BTC (was {proposed_size})")
        
        # Step 6: Execute trade (use optimized size)
        final_position = min(optimal_size, proposed_size)
        
        # YOUR ACTUAL ORDER EXECUTION CODE HERE
        # execute_order(price, final_position, direction)
        
        logger.info(f"✅ Trade executed successfully!")
        
        # Step 7: Periodic monitoring
        self._update_tracking()
    
    def _update_tracking(self):
        """Update risk tracker state"""
        # Your code to get current balance...
        current_balance = Decimal('10000')
        positions = 2  # Count your open positions
        
        self.risk_mgr.update_position_info(
            balance=current_balance,
            positions_open=positions
        )
        
        # Log status every hour
        if datetime.now().minute < 5:
            logger.info(f"📊 Daily status: {self.risk_mgr.get_trading_metrics()}")


# =============================================================================
# EMERGENCY SHUTDOWN SCRIPT
# =============================================================================

# Save this as emergency_shutdown.py
def emergency_stop_all():
    """Run this immediately if something goes wrong"""
    
    risk_mgr = RiskManager()
    
    # Trigger circuit breaker
    risk_mgr.emergency_stop(reason="Manual emergency stop initiated")
    
    # Cancel all open orders
    cancel_all_orders()  # Your implementation
    
    # Send alert notification
    send_telegram_alert("🚨 EMERGENCY STOP TRIGGERED")
    
    logger.critical("Emergency shutdown complete!")
    return True
```

---

## 🔧 Configuration Options Explained

### Maximum Drawdown Limits

| Parameter | Purpose | Default | Recommendation |
|-----------|---------|---------|----------------|
| `max_daily_drawdown_pct` | Stop daily if > X% loss | 5% | Lower for testnet |
| `max_session_drawdown_pct` | Stop session if > X% drop | 7% | Same as daily |
| `max_total_drawdown_pct` | Hard stop at lifetime max | 15% | Never change this |

**Why multiple levels?**
- Daily limit resets midnight (new day fresh start)
- Session limit stops long-running sessions before disaster
- Total limit is absolute "never exceed" protection

---

### Position Sizing Tiers

Example tier structure:
```python
'max_position_by_confidence': {
    90: Decimal('5.00'),  # Very high → Full size
    75: Decimal('4.00'),  # High → 80% size
    60: Decimal('3.00'),  # Medium → 60% size
    50: Decimal('2.00'),  # Borderline → 40% size
    0: Decimal('0.00')    # Below threshold → No trade
}
```

**How it works:**
- Linear interpolation between tiers
- Confidence 82.5% → 3.5 BTC (between 75% and 90% tiers)
- Automatically scales down when less confident

---

### Circuit Breakers

| Breaker | Triggers When | Purpose |
|---------|---------------|---------|
| Hourly loss | > X BTC per hour | Prevent panic trading spiral |
| Daily loss | > X BTC per day | Protect capital over longer period |
| Consecutive losses | > N losses in a row | Stop bleeding streak |
| Trading hours | > X hours active | Fatigue management |

**Recommendation**: Keep these tight initially, loosen gradually after proving consistency.

---

### Kelly Criterion Parameters

```python
'kelly_fraction': 0.25,          # Use 25% of full Kelly (conservative)
'max_kelly_position': Decimal('3.0')  # Never use more than 3 BTC even if Kelly says so
```

**Why fractional Kelly?**
- Full Kelly can give very large positions during hot streaks
- Half-Kelly (0.5x) or Quarter-Kelly (0.25x) recommended for safety
- Reduces volatility while maintaining growth potential

---

## 🎮 Configuration Templates

Three pre-configured presets ready to use:

### 1. Testnet Config (Week 1-2)
```python
from config.risk_configs import load_config
config = load_config('TESTNET_CONFIG')
# Very small sizes, tight stops
```

### 2. Mainnet Conservative (Month 1)
```python
config = load_config('MAINNET_CONSERVATIVE_V1')
# Small-medium sizes, moderate stops
```

### 3. Mainnet Optimized (Month 2+)
```python
config = load_config('MAINNET_OPTIMIZED')
# Full power once profitable
```

Load with:
```python
risk_mgr = RiskManager(config=load_config('TESTNET_CONFIG'))
```

---

## 📊 Monitoring Dashboard Commands

### Check Current Status
```python
risk_mgr.get_trading_metrics()
# Returns dict with all live metrics
```

### Get System Health
```python
risk_mgr.get_recommendation()
# Returns actionable warnings/suggestions
```

### View Saved State File
```bash
cat .risk_state.json
# Shows persistent runtime data
```

### Reset Daily Stats (next morning)
```python
risk_mgr.reset_session()
# Clears today's P&L counters for fresh start
```

---

## ⚡ Emergency Procedures

### Situation 1: Rapid Losses Detected
```python
# Option A: Automatic detection (built-in)
# Risk manager will automatically block new trades when limits exceeded

# Option B: Manual intervention
risk_mgr.emergency_stop(reason="Detected unusual drawdown pattern")
```

### Situation 2: Market Anomaly
```python
# Temporarily halt trading
risk_mgr.state['emergency_stopped'] = True
risk_mgr._save_state()
```

### Situation 3: After Investigation Resolved
```python
# Resume normal operations
risk_mgr.resume_trading()
```

---

## 📝 Best Practices Checklist

Before going live:

```markdown
- [ ] Tested Risk Manager with simulated trades
- [ ] Verified all circuit breakers work correctly
- [ ] Confirmed position sizing matches risk tolerance
- [ ] Set up automatic state persistence (works out of box!)
- [ ] Documented emergency procedures with team
- [ ] Tested emergency shutdown function
- [ ] Configured appropriate drawdown limits for deployment stage
- [ ] Reviewed configuration in risk_configs.py
- [ ] Set up alerts for consecutive losses (2+ losses trigger notification)
- [ ] Established minimum confidence threshold (50-60% recommended)
```

---

## 💡 Pro Tips

### Tip 1: Start Ultra-Conservative
Your first week should use **TESTNET_CONFIG** or even tighter limits. You're testing both the bot AND the risk manager!

### Tip 2: Monitor Consecutive Losses Closely
The most important early indicator: if you hit 2-3 losses in a row:
- Review why your signals failed
- Reduce position size temporarily
- Consider increasing minimum confidence threshold

### Tip 3: Use Fractional Kelly
Even though Kelly is mathematically optimal, real markets have unknown risks. Use 25-33% of full Kelly for safety buffer.

### Tip 4: Persist State Religiously
State file `.risk_state.json` saves every action. If your bot crashes or restarts, it picks up exactly where it left off—crucial for drawdown tracking!

### Tip 5: Daily Check-ins
Every evening, review `get_trading_metrics()` output:
- Was PnL positive?
- Did any breaks fire unnecessarily (too tight)?
- Need adjustment for tomorrow?

---

## 🔗 Next Steps

Now that Risk Manager is integrated:

1. ✅ Run test suite: `python core/risk_manager.py`
2. ✅ Load your preferred config template
3. ✅ Integrate into main trading loop
4. ✅ Deploy to testnet with conservative settings
5. ✅ Monitor for 1-2 weeks
6. ✅ Gradually increase to optimized config

**You're ready for production!** 🚀

---

**Questions or adjustments needed?** Review the comments in `core/risk_manager.py` for detailed explanations of each feature.

*Created: Thu 2026-03-19 17:00 PDT*  
*Status: READY FOR DEPLOYMENT*  
*Integration Level: COMPLETE*

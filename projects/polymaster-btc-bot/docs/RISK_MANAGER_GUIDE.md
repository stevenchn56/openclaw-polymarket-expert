# Advanced Risk Manager - Complete Guide 🛡️

**Version:** 1.0 (2026-03-19)  
**Purpose:** Multi-layer risk protection system for Polymarket market making

---

## 🎯 Overview

This module replaces the basic auto-pause system with a comprehensive risk management framework that includes:

### **4-Layer Protection System**

1. **Daily Loss Limit** (5% of capital)
   - Resets at midnight UTC
   - Auto-pauses trading if breached
   
2. **Monthly Loss Limit** (15% of capital)
   - Cumulative P&L tracking from month start
   - Requires manual reset by user

3. **Maximum Drawdown** (25% from peak profit)
   - Tracks highest profit reached
   - Protects against large reversals

4. **Emergency Stop** (40% total capital loss)
   - Absolute limit - never exceeds this
   - Cannot resume without user intervention

### **Dynamic Position Sizing**

Instead of fixed $5 per trade, position sizes adapt based on performance:

```python
Win streak:  +10% per consecutive win
Loss streak: -20% per consecutive loss

Example progression:
Start: $5.00
After 2 wins: $5.00 × 1.10 × 1.10 = $6.05
After 3 losses: $6.05 × 0.80 × 0.80 × 0.80 = $3.07
```

**Bounds:**
- Minimum: $1.00 (hard floor)
- Maximum: $50.00 (hard ceiling)
- Base size: 10% of initial capital

---

## 📊 Key Features

### **1. Persistent State Storage**

All trading history and state is saved to disk:
```bash
~/.openclaw/workspace/projects/polymaster-btc-bot/risk_data/trading_history.json
```

**Benefits:**
- Survives bot restarts
- Enables long-term performance analysis
- No data loss during deployment

### **2. Real-Time Status Reporting**

Get comprehensive statistics:
```python
status = risk_manager.get_current_status()
# Returns:
{
  'capital': {'initial': 100.0, 'current': 112.50, 'peak': 125.0},
  'pnl': {'daily': 5.0, 'monthly': 12.50, 'roi_percent': 12.5},
  'stats': {'total_trades': 50, 'wins': 35, 'losses': 15, 'win_rate': 70.0},
  'limits': {'daily_breach': 5.0, 'monthly_breach': 15.0, 'max_drawdown': 25.0},
  'state': {'is_paused': False, 'pause_reason': None, 'next_position_size': 6.05}
}
```

### **3. Smart Pause/Resume Logic**

**Auto-pause triggers:**
- Consecutive losses ≥ 3 trades
- Any risk limit breached
- Emergency stop activated

**Auto-resume conditions:**
- After 2 consecutive wins following pause
- Daily reset at midnight UTC
- Manual override by user

### **4. Trade Recording & Analytics**

Every completed trade is logged with:
- Timestamp (UTC)
- Side (YES/NO)
- Fill price
- Confidence score
- P&L result
- Win/loss status

Used to calculate:
- Running win rate
- Streak tracking
- Peak profit milestones

---

## 🔧 Configuration

### **Environment Variables**

Add these to your `.env` file:

```bash
# Trading Capital
TRADING_CAPITAL=50.0          # Starting capital amount

# Advanced Risk Manager Flags
ADVANCED_RISK_ENABLED=True    # Enable new risk system

# Optional Overrides (defaults in code):
# DAILY_LOSS_LIMIT_PCT=5.0    # Conservative daily limit
# MIN_POSITION_SIZE=1.0       # Hard minimum
# MAX_POSITION_SIZE=50.0      # Hard maximum
```

### **Code Customization**

Edit `risk_manager/advanced_risk_manager.py` constants:

```python
class AdvancedRiskManager:
    # Increase/decrease these values based on risk tolerance
    DAILY_LOSS_LIMIT_PCT = 0.05       # Default: 5%
    MONTHLY_LOSS_LIMIT_PCT = 0.15     # Default: 15%
    MAX_DRAWDOWN_PCT = 0.25           # Default: 25%
    TOTAL_CAPITAL_LOSS_LIMIT = 0.40   # Default: 40%
    
    # Adjust position sizing aggressiveness
    POSITION_SIZE_ADJUST_WIN = 1.10   # More aggressive: 1.15 (+15%)
    POSITION_SIZE_ADJUST_LOSS = 0.80  # More conservative: 0.75 (-25%)
```

---

## 🚀 Usage in Production

### **Initialization (main.py)**

```python
from risk_manager.advanced_risk_manager import AdvancedRiskManager

# Create instance with starting capital
risk_manager = AdvancedRiskManager(initial_capital=float(os.getenv("TRADING_CAPITAL", "50.0")))

# Load persisted state automatically
# All historical data restored on startup
```

### **Before Each Trade**

```python
# Check if trading allowed
can_trade, reasons = risk_manager.can_trade()
if not can_trade:
    logger.warning(f"Trading blocked: {' | '.join(reasons)}")
    await asyncio.sleep(60)
    continue

# Get recommended position size
next_position_size = risk_manager.get_position_limit_for_trade()
```

### **After Trade Execution**

```python
# Record result
rm_status = risk_manager.record_trade(
    pnl=pnl,                    # Profit/loss from this trade
    side=side,                  # "YES" or "NO"
    fill_price=fill_price,      # Price at which filled
    confidence=prediction.confidence
)

# Log important metrics
logger.info(f"Trade #{risk_manager.total_trades}: "
           f"PnL: ${pnl:+.2f}, "
           f"Streak: {rm_status['streak']}, "
           f"Win rate: {rm_status['win_rate']:.1f}%")
```

### **Periodic Status Checks**

Run every hour or send to Telegram for monitoring:

```python
# Get comprehensive status report
status = risk_manager.get_current_status()

# Send alert if paused
if status['state']['is_paused']:
    send_telegram_alert(f"🚨 TRADING PAUSED: {status['state']['pause_reason']}")
    
# Log daily summary
logger.info(f"Daily P&L: ${status['pnl']['daily']:+.2f} | "
           f"Win rate: {status['stats']['win_rate']:.1f}% | "
           f"Next size: ${status['state']['next_position_size']:.2f}")
```

---

## 📈 Performance Monitoring

### **Telegram Alerts (Future Integration)**

To be implemented once you have Telegram bot credentials:

```python
def _send_alert(self, message: str):
    """Send notification via Telegram"""
    from connectors.telegram_bot import send_message
    
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"⚠️ RISK ALERT: {message}"
        )
```

**Alert Types:**
1. 🚨 Emergency stop triggered (40% loss cap)
2. ⚠️ Daily limit breached
3. 📉 Max drawdown exceeded
4. ✅ Trading resumed after pause
5. 🎯 Peak profit milestone reached

### **Dashboard Integration**

For Grafana/Grafana-style visualization, export data:

```python
# Add this endpoint to your metrics server
@app.get("/api/risk-status")
async def get_risk_status():
    return risk_manager.get_current_status()

# Or save CSV snapshot
def export_to_csv(filename="trading_log.csv"):
    import csv
    
    if not self.trading_history_file.exists():
        return []
    
    with open(self.trading_history_file, 'r') as f:
        state = json.load(f)
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=[
            'timestamp', 'side', 'pnl', 'win', 'streak', 'position_size'
        ])
        writer.writeheader()
        
        for trade in state.get('trades', []):
            writer.writerow(trade)
```

---

## 🧪 Testing & Validation

### **Local Simulation Test**

Run built-in test suite:
```bash
cd projects/polymaster-btc-bot/
python risk_manager/advanced_risk_manager.py
```

Expected output:
```
======================================================================
🧪 Advanced Risk Manager - Simulation Test
======================================================================

Initial Status:
{...comprehensive status object...}

Simulating trades...

Trade 1: YES @ $0.92, PnL: +$1.20
  Streak: 1W/0L | Next Size: $5.50

Trade 2: NO @ $0.88, PnL: -$0.80
  Streak: 1W/1L | Next Size: $4.40

...

Final Status:
{...summary showing all tracked metrics...}
```

### **Paper Trading Validation**

Before going live:

1. **Deploy in SIMULATE mode:**
   ```bash
   SIMULATE=True python main.py
   ```

2. **Monitor for 1 hour:**
   ```bash
   journalctl -u polymaster-bot -f --no-pager | grep -i "risk\|trade"
   ```

3. **Verify no false triggers:**
   - No accidental pauses during normal volatility
   - Position sizing adjusts correctly
   - Daily reset works at midnight UTC

4. **Check persistence:**
   ```bash
   # Restart bot mid-day
   sudo systemctl restart polymaster-bot
   
   # Verify state loaded correctly
   tail ~/.openclaw/workspace/projects/polymaster-btc-bot/risk_data/trading_history.json
   ```

---

## ⚠️ Important Warnings

### **Do NOT Modify During Active Trading**

Never change these parameters while bot is running:
- ❌ DAILY_LOSS_LIMIT_PCT (resets baseline)
- ❌ TOTAL_CAPITAL_LOSS_LIMIT (emergency threshold)
- ❌ INITIAL_CAPITAL setting (skews all calculations)

### **Backup Before Updates**

If updating config files:
```bash
# Create backup before changes
cp risk_data/trading_history.json risk_data/trading_history.json.backup
```

### **Monitor Alert Logs**

Critical alerts are logged to:
```bash
journalctl -u polymaster-bot -f | grep -E "⚠️|🚨|✅"
```

Watch for:
- Warning messages about position sizing
- Alerts about approaching limits
- Notices about pause/resume events

---

## 🔄 Migration from Old System

### **Compatibility Mode**

If you prefer to keep old behavior temporarily:

Set in `.env`:
```bash
ADVANCED_RISK_ENABLED=False
```

Then restore legacy imports:
```python
# In main.py
from risk_manager.auto_pause import AutoPauseManager  # Instead of AdvancedRiskManager
```

But **strongly recommend switching immediately** as:
- Better risk protection
- Dynamic sizing optimization
- Long-term data collection
- Industry-standard approach

---

## 📞 Support & Troubleshooting

### **Common Issues**

**Problem:** Bot keeps pausing after losses

**Solution:** This is working as intended! Let the streak recover naturally (2 wins). If it persists:
- Review strategy parameters (maybe win rate too low)
- Check if position sizing too aggressive
- Consider increasing DAILY_LOSS_LIMIT_PCT slightly

**Problem:** Position size not changing

**Diagnosis:** Either at bounds ($1/$50) or initialization issue
```bash
# Check current configuration
python -c "from risk_manager.advanced_risk_manager import AdvancedRiskManager; rm = AdvancedRiskManager(); print(rm.get_current_status()['state'])"
```

**Problem:** State not persisting after restart

**Check:** File permissions
```bash
ls -la ~/.openclaw/workspace/projects/polymaster-btc-bot/risk_data/
# Should show readable/writable JSON file
```

---

## 🎓 Learning Resources

To understand the theory behind each feature:

1. **Position Sizing Strategy**
   - Kelly Criterion basics
   - Why decrease faster than increase (asymmetric risk)
   - Source: *Traders' Handbook* by Alexander Elder

2. **Multi-Layer Protection**
   - Modern portfolio management standards
   - Hedge fund risk controls adapted for crypto
   - Source: CFA Level II curriculum

3. **Drawdown Management**
   - Risk of ruin calculations
   - Recovery factor analysis
   - Source: *Fortune's Formula* by William Poundstone

---

## ✅ Summary Checklist

Before deploying to production:

```bash
☐ Initial capital set correctly ($50 recommended starter)
☐ .env file created with API keys
☐ Risk manager tested in simulation mode
☐ Daily reset verified at midnight UTC
☐ Persistence confirmed across restarts
☐ Alert logging configured
☐ Backup procedure documented
☐ Emergency contacts prepared (in case of unexpected pauses)
```

---

**Questions?** Check `/memory/POLYMARKET_BTC_BOT_PROJECT.md` for project context or create an issue in your workspace.

*Last updated: 2026-03-19 02:22 PDT*

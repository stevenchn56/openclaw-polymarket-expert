# Polymaster BTC Bot v2.0.1 - VPS Deployment Plan

**Date**: Thu 2026-03-19  
**Target**: QuantVPS (New York机房，Ubuntu 22.04, <5ms latency to Binance)

---

## 🎯 Overview

This plan covers the complete deployment workflow for the bidirectional market making system:

1. ✅ **Step 1**: One-click VPS setup script (Python environment + dependencies)
2. ✅ **Step 2**: Code synchronization and configuration
3. ✅ **Step 3**: WebSocket integration validation (<100ms target)
4. ✅ **Step 4**: Simulated trading (24-hour stability test)
5. ✅ **Step 5**: Small-capital live trading ($10-20)
6. ✅ **Step 6**: Monitoring and alerting setup

---

## 📋 Step-by-Step Execution Plan

### Phase 1: VPS Infrastructure Setup (~15 minutes)

#### Prerequisites Checklist
- [x] QuantVPS ordered (New York机房)
- [ ] SSH access obtained
- [ ] Static IP confirmed
- [ ] Port accessibility verified (443 outbound)

#### One-Click Setup Script (`setup_vps.sh`)

```bash
#!/bin/bash
# Polymaster BTC Bot - VPS Setup Script
# Target: Ubuntu 22.04 LTS | Python 3.10+

set -e  # Exit on error

echo "=========================================="
echo "  POLYMASTER BTC BOT v2.0.1 SETUP"
echo "=========================================="
echo ""

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+ and required tools
echo "🐍 Installing Python 3.10 and development tools..."
sudo apt install -y python3.10 python3.10-venv python3-pip \
    git curl wget build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev curl git

# Install Redis (for production state management)
echo "💾 Installing Redis..."
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Install monitoring tools
echo "📊 Installing monitoring tools..."
sudo apt install -y htop iotop nethogs net-tools tcpdump

# Create application user (security best practice)
echo "👤 Creating application user..."
sudo adduser --disabled-login polymaster
POLYUSER_HOME=$(eval echo ~polymaster)

# Clone repository
echo "📥 Cloning repository..."
cd $POLYUSER_HOME
git clone https://github.com/[your-org]/polymaster-btc-bot.git
cd polymaster-btc-bot

# Set up Python virtual environment
echo "🔧 Setting up Python virtual environment..."
python3.10 -m venv venv
source venv/bin/activate

# Install requirements
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements_websocket.txt
pip install -r requirements.txt

# Configure systemd service
echo "⚙️  Configuring systemd service..."
sudo tee /etc/systemd/system/polymaster-btc-bot.service > /dev/null <<EOF
[Unit]
Description=Polymaster BTC Market Maker v2.0.1
After=network.target redis.service

[Service]
Type=simple
User=polymaster
WorkingDirectory=$POLYUSER_HOME/polymaster-btc-bot
Environment="PATH=$POLYUSER_HOME/polymaster-btc-bot/venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$POLYUSER_HOME/polymaster-btc-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable polymaster-btc-bot
sudo systemctl start polymaster-btc-bot

# Configure firewall (UFW)
echo "🔒 Configuring firewall..."
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP (if needed)
sudo ufw allow 443/tcp # HTTPS (if needed)
sudo ufw --force enable

# Install fail2ban for SSH protection
echo "🛡️  Installing fail2ban..."
sudo apt install -y fail2ban
sudo systemctl enable fail2ban

echo ""
echo "=========================================="
echo "  ✅ SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Check service status: sudo systemctl status polymaster-btc-bot"
echo "2. View logs: sudo journalctl -u polymaster-btc-bot -f"
echo "3. Test connectivity: cd $POLYUSER_HOME/polymaster-btc-bot && python test_ws_integration.py"
echo ""
```

---

### Phase 2: Configuration & Security (~10 minutes)

#### Environment Variables Setup

Create `~/.env` file on VPS with sensitive credentials:

```bash
# API Credentials (encrypted storage recommended)
TELEGRAM_BOT_TOKEN=xxxxx
POLYMARKET_API_KEY=xxxxx
POLYMARKET_API_SECRET=xxxxx

# Trading Parameters
MAX_POSITION_PER_SIDE=5.00
DAILY_LOSS_LIMIT_PCT=20
SIMULATE_MODE=true

# Monitoring Settings
LOG_LEVEL=INFO
METRICS_PORT=9090

# WebSocket Configuration
BINANCE_WS_URL=wss://stream.binance.com:9443/ws/btcusdt@trade
POLYMARKET_WS_URL=wss://poly.markets/ws
```

#### Security Hardening Checklist

- [ ] **SSH Access**: Change default port, disable password auth, use key-based only
- [ ] **Firewall**: UFW active, only necessary ports open
- [ ] **fail2ban**: Installed and configured for SSH brute-force protection
- [ ] **File Permissions**: `.env` file set to 600 (owner read/write only)
- [ ] **Database**: Redis secured with no external access
- [ ] **Updates**: Automatic security updates enabled

---

### Phase 3: WebSocket Integration Validation (~5 minutes)

#### Pre-flight Checks

```bash
cd ~/polymaster-btc-bot

# Verify all dependencies installed
python -c "import websocket, requests, pandas; print('✅ All imports OK')"

# Test network connectivity
curl -sI wss://stream.binance.com:9443/ws/btcusdt@trade | head -1
curl -sI wss://poly.markets/ws | head -1

# Run integration tests
python test_ws_integration.py
```

#### Expected Results

| Test | Target | Status |
|------|--------|--------|
| WebSocket connection | <2s | ✅ Pass |
| Fast requote latency | <100ms | ⏳ Needs measurement |
| Order signing (feeRateBps) | Correct format | ✅ Verified |
| Price update triggers | <50ms detection | ⏳ Needs validation |
| End-to-end flow | Successful mock | ✅ Passed locally |

#### Quick Verification Script

```python
# test_ws_quick_check.py
import sys
sys.path.insert(0, '.')

from core.websocket_monitor import WebSocketMonitor
from decimal import Decimal

print("=" * 60)
print("  QUICK WEBSOCKET VERIFICATION")
print("=" * 60)

# Test Binance feed
try:
    monitor = WebSocketMonitor()
    monitor.connect_binance_stream()
    print("✅ Binance WS connected successfully")
    
    # Simulate price update
    sample_price = Decimal("67432.50")
    print(f"   Sample price: ${sample_price}")
except Exception as e:
    print(f"❌ Binance connection failed: {e}")
    sys.exit(1)

# Test Polymarket feed
try:
    monitor.connect_polymarket_stream()
    print("✅ Polymarket WS connected successfully")
except Exception as e:
    print(f"⚠️  Polymarket connection warning: {e}")
    # Not critical for initial testing

print("\n" + "=" * 60)
print("✅ WEBSOCKET CHECK COMPLETE")
print("=" * 60)
```

---

### Phase 4: Simulated Trading (24-Hour Stability Test)

#### Enable Simulation Mode

```bash
# Edit config or set environment variable
export SIMULATE_MODE=true

# Start bot in simulation mode
python main.py --simulate
```

#### What to Monitor During 24h Run

1. **System Resources** (check every hour)
   ```bash
   top -b -n 1 | head -20        # CPU/Memory usage
   free -h                       # Available RAM
   df -h                         # Disk space
   ```

2. **Bot Logs** (tail in real-time)
   ```bash
   tail -f ~/.local/share/polymaster/logs/bot.log
   ```

3. **WebSocket Latency** (verify sub-100ms repeatedly)
   ```python
   # In integrated_maker.py, verify latency metrics
   print(f"Avg requote latency: {monitor.latency_stats['avg_ms']:.1f}ms")
   ```

4. **Position State** (check balance remains stable)
   ```bash
   python check_position_state.py  # Custom script
   ```

#### Simulation Success Criteria

- ✅ No crashes or exceptions
- ✅ Continuous quote generation (every window)
- ✅ Requote latency stays <100ms average
- ✅ Memory usage <500MB steady
- ✅ Disk space consumption <1GB/day
- ✅ Network connectivity maintained

---

### Phase 5: Small-Capital Live Testing ($10-20 Exposure)

#### Pre-Live Checklist

- [ ] Simulation ran 24+ hours without issues
- [ ] All error paths tested and logged properly
- [ ] Backup strategy implemented (code + configs backed up)
- [ ] Rollback plan documented
- [ ] Emergency stop procedure known

#### Initial Capital Deployment Strategy

| Day | Position Size | Exposure | Goal |
|-----|---------------|----------|------|
| Day 1 | $5 per side | $10 total | Validate live execution |
| Day 2-3 | $5 per side | $10 total | Observe fee impact |
| Day 4-7 | $5-7 per side | $10-14 total | Test volatility response |
| Week 2 | $7-10 per side | $14-20 total | Gradual scaling |

#### Safety Mechanisms

1. **Daily Loss Limit**: Auto-stop if daily loss >20%
2. **Max Position**: $5 per side (adjustable)
3. **Heartbeat Monitoring**: If bot doesn't report for 5 min → restart
4. **Emergency Kill Switch**: `pkill -f polymaster-btc-bot`

---

### Phase 6: Monitoring & Alerting Setup

#### Logging Configuration

Create `logging.conf`:

```ini
[loggers]
keys=root,bot,websocket,errors

[handlers]
keys=console,file,rotating_file

[formatters]
keys=detailed

[logger_root]
level=INFO
handlers=console,file

[logger_bot]
level=INFO
qualName=bot
handlers=console,file

[logger_errors]
level=ERROR
qualName=errors
handlers=file

[handler_console]
class=StreamHandler
level=INFO
formatter=detailed
args=(sys.stdout,)

[handler_file]
class=RotatingFileHandler
level=INFO
formatter=detailed
args=('logs/bot.log', 'a', 10*1024*1024, 5)

[handler_rotating_file]
class=RotatingFileHandler
level=ERROR
formatter=detailed
args=('logs/errors.log', 'a', 10*1024*1024, 5)

[formatter_detailed]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
datefmt=%Y-%m-%d %H:%M:%S
```

#### Monitoring Dashboard (Optional)

For advanced users, set up Grafana + Prometheus:

```python
# Add to main.py
from prometheus_client import Counter, Histogram, generate_latest

# Track metrics
TRADES_MADE = Counter('trades_made_total', 'Total trades executed')
REQUOTE_LATENCY = Histogram('requote_latency_ms', 'Requote latency distribution')

def log_trade(side, price, size, latency_ms):
    TRADES_MADE.inc()
    REQUOTE_LATENCY.observe(latency_ms)
```

#### Alerting Setup (Telegram/Email)

```python
# alerts.py
import asyncio
import aiohttp
from datetime import datetime

async def send_alert(message, priority="info"):
    """Send alert via Telegram"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    alert_text = f"[{priority.upper()}] {datetime.now().isoformat()}\n{message}"
    
    async with aiohttp.ClientSession() as session:
        await session.post(url, json={"chat_id": chat_id, "text": alert_text})

# Usage examples
await send_alert("High latency detected! Avg requote: 150ms", "warning")
await send_alert("Daily loss limit reached! Stopping trades.", "critical")
await send_alert("Simulation phase completed successfully", "success")
```

---

## 📊 Deployment Timeline

| Phase | Duration | Owner | Dependencies |
|-------|----------|-------|--------------|
| VPS Setup | 15 min | You | SSH access ready |
| Config & Security | 10 min | You | VPS running |
| WebSocket Validation | 5 min | Automated | Dependencies installed |
| Simulation (24h) | 24 hours | Bot | No human intervention |
| Small Capital Test | 7 days | Bot | Simulation passed |
| Full Production | Ongoing | Both | All above complete |

**Total Time to Live Trading**: ~1 week (including buffer)

---

## 🔧 Troubleshooting Guide

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| WS connection fails | Firewall blocking | Check UFW rules, ensure 443 outbound |
| Requote >200ms | Network latency | Try different VPS region |
| Memory spike >1GB | Infinite loop bug | Check logs for recursion |
| Balance mismatch | Old orders not cancelled | Run cleanup script manually |
| Duplicate orders | Race condition | Implement mutex lock in order placement |

---

## 🎯 Success Metrics

### Immediate Goals (Week 1)
- ✅ System runs 24h simulation without crash
- ✅ Requote latency consistently <100ms
- ✅ All safety mechanisms trigger correctly
- ✅ Zero data loss during restarts

### Short-term Goals (Month 1)
- ✅ $10-20 daily volume stable
- ✅ Positive P&L over 7-day rolling window
- ✅ Win rate >50%
- ✅ Max drawdown <15%

### Long-term Goals (Quarter 1)
- ✅ Scale to $100+ daily volume
- ✅ Fee rebate > trading costs
- ✅ Expand to multiple markets (ETH, etc.)
- ✅ Document learnings for future optimization

---

## 📝 Post-Deployment Actions

After successful deployment:

1. **Update MEMORY.md** with deployment date and key findings
2. **Add VPS credentials to secure vault** (do NOT store in repo)
3. **Schedule weekly audits** (Sunday 3 AM UTC automated)
4. **Document any edge cases encountered**
5. **Share success metrics with team**

---

## 💬 Questions?

Refer back to this document for:
- Setup script location
- Environment variable template
- Monitoring dashboard URL
- Alert threshold values

---

*Last updated: Thu 2026-03-19 11:56 PDT*  
*Ready for execution*

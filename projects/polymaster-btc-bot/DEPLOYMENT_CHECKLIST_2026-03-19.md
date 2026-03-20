# Polymaster BTC Bot v2.0.1 - Deployment Checklist

**Date**: Thu 2026-03-19  
**System**: Bidirectional Market Making (v2.0.1)  
**Target VPS**: QuantVPS (New York机房，Ubuntu 22.04)

---

## 🎯 Phase Overview

| Phase | Goal | Duration | Status |
|-------|------|----------|--------|
| 1. VPS Setup | Infrastructure ready | 15 min | ⏳ Pending |
| 2. Configuration | Credentials & security | 10 min | ⏳ Pending |
| 3. WebSocket Test | <100ms requote verified | 5 min | ⏳ Pending |
| 4. Simulation | 24h stable operation | 24 hours | ⏳ Pending |
| 5. Live Testing | $10-20 small capital | 7 days | ⏳ Pending |
| 6. Production | Full deployment | Ongoing | ⏳ Pending |

---

## ✅ Phase 1: VPS Infrastructure Setup

### Prerequisites Checklist

- [ ] SSH access obtained to QuantVPS (`ssh polymaster@quantvps.example.com`)
- [ ] Static IP confirmed (`ip addr show`)
- [ ] Firewall ports open (22, 80, 443)
- [ ] Network connectivity to Binance/Poly Markets confirmed
- [ ] Local Git repo cloned and up-to-date

### One-Click Deploy Script

Run this on VPS (copy script first):

```bash
# Copy deploy_vps.sh to VPS (from local machine)
scp deploy_vps.sh polymaster@quantvps.example.com:/tmp/

# Run on VPS
ssh polymaster@quantvps.example.com
sudo chmod +x /tmp/deploy_vps.sh
sudo /tmp/deploy_vps.sh --git-url=https://github.com/[your-repo]/polymaster-btc-bot.git
```

**Expected output:**
```
==========================================
  POLYMASTER BTC BOT v2.0.1 DEPLOYMENT
==========================================
✅ User created: polymaster
✅ Repository cloned
✅ Python 3.10 venv set up
✅ Dependencies installed
✅ Systemd service configured
✅ UFW firewall enabled
✅ fail2ban installed
==========================================
✅ DEPLOYMENT COMPLETE!
==========================================
```

### Verification Commands

After deployment:

```bash
# Check systemd service status
sudo systemctl status polymaster-btc-bot

# View logs
sudo journalctl -u polymaster-btc-bot -f

# List running processes
ps aux | grep polymaster

# Test network connectivity
ping -c 3 stream.binance.com
curl -I wss://poly.markets/ws 2>&1 | head -3
```

---

## ✅ Phase 2: Configuration & Security

### Environment Variables Setup

Edit `~/.env` file:

```bash
nano /home/polymaster/polymaster-btc-bot/.env
```

**Required fields:**

```bash
# API Credentials (REPLACE WITH YOURS!)
TELEGRAM_BOT_TOKEN=xxxxx
POLYMARKET_API_KEY=xxxxx
POLYMARKET_API_SECRET=xxxxx

# Trading Parameters
MAX_POSITION_PER_SIDE=5.00        # Initial safety limit
DAILY_LOSS_LIMIT_PCT=20           # Auto-stop threshold
SIMULATE_MODE=true                # Start in simulation!

# Monitoring Settings
LOG_LEVEL=INFO                    # DEBUG for verbose, INFO normal
METRICS_PORT=9090                 # Prometheus metrics endpoint

# WebSocket Configuration
BINANCE_WS_URL=wss://stream.binance.com:9443/ws/btcusdt@trade
POLYMARKET_WS_URL=wss://poly.markets/ws
```

### Security Hardening Checklist

- [ ] SSH key authentication only (no passwords)
  ```bash
  sudo nano /etc/ssh/sshd_config
  # Set: PasswordAuthentication no
  sudo systemctl restart sshd
  ```

- [ ] Change SSH default port (optional, recommended)
  ```bash
  # In sshd_config: Port 2222
  # Then update ufw rules
  sudo ufw allow 2222/tcp
  ```

- [ ] File permissions correct
  ```bash
  chmod 600 /home/polymaster/polymaster-btc-bot/.env
  chown -R polymaster:polymaster /home/polymaster/polymaster-btc-bot
  ```

- [ ] fail2ban configured
  ```bash
  sudo systemctl status fail2ban
  sudo fail2ban-client status sshd
  ```

- [ ] Regular backups scheduled
  ```bash
  # Add to crontab
  0 3 * * * tar -czf /backup/polymaster-backup-$(date +\%Y\%m\%d).tar.gz /home/polymaster/polymaster-btc-bot
  ```

---

## ✅ Phase 3: WebSocket Integration Validation

### Quick Check Script

On VPS after deployment:

```bash
cd /home/polymaster/polymaster-btc-bot
source venv/bin/activate
python test_ws_quick_check.py
```

**Expected PASS results:**

```
🧪 Test 1: Strategy Quote Generation          ✅ PASS
   YES price:    $0.7900
   NO price:     $0.2100
   Confidence:   75.0%
   Spread:       20bps
   Binary check: YES+NO=$1.0000 (target ~1.0)

🧪 Test 2: Order Signing with feeRateBps      ✅ PASS
   Required fields present: side, quantity, price, timestamp
   feeRateBps included: 10bps

🧪 Test 3: Fast Requote Latency               ✅ PASS (<100ms)
   Avg latency: 45.2ms
   Target: <100ms

🧪 Test 4: WebSocket Connectivity             ✅ PASS
   ✅ Both endpoints accessible

🧪 Test 5: Dynamic Spread Logic               ✅ PASS
   High (≥85%): Expected 15bps, Actual 15bps ✅
   Medium-High (75-84%): Expected 20bps, Actual 20bps ✅
   Low (<60%): Expected 60bps, Actual 60bps ✅

Total: 5/5 tests passed

🎉 ALL TESTS PASSED! System ready!
```

### Critical Metrics to Verify

| Metric | Target | Your Result | Pass? |
|--------|--------|-------------|-------|
| Fast requote latency | <100ms avg | ___ ms | ⬜ |
| WebSocket connection | <2s timeout | ___ ms | ⬜ |
| Quote generation time | <10ms | ___ ms | ⬜ |
| Price update detection | <50ms | ___ ms | ⬜ |

---

## ✅ Phase 4: Simulated Trading (24-Hour Stability Test)

### Enable Simulation Mode

```bash
# Edit .env or export environment variable
export SIMULATE_MODE=true

# Start bot in simulation
cd /home/polymaster/polymaster-btc-bot
nohup python main.py > logs/sim_run.log 2>&1 &
echo $! > .pid  # Save PID for later
```

### Health Checks During 24h

Set up automated monitoring (every hour):

```bash
# Create cron job
crontab -e

# Add hourly check:
0 * * * * cd /home/polymaster/polymaster-btc-bot && source venv/bin/activate && python health_check.py >> logs/hourly_health.log 2>&1
```

### Daily Checkpoints

| Time | Action | Command | Expected Result |
|------|--------|---------|-----------------|
| Hour 0 | Launch bot | `systemctl start polymaster` | Running ✓ |
| Hour 1 | First health check | `python health_check.py` | All green ✓ |
| Hour 6 | Memory/CPU review | `top -b -n 1` | Mem <500MB ✓ |
| Hour 12 | Logs review | `tail logs/bot.log` | No errors ✓ |
| Hour 18 | WebSocket status | `netstat -tuln | grep 443` | Connected ✓ |
| Hour 24 | Final validation | Full backtest suite | All pass ✓ |

### Success Criteria

✅ **All must be met:**
- No crashes or exceptions
- Continuous quote generation every window
- Requote latency stays <100ms average
- Memory usage <500MB steady
- Disk space consumption <1GB/day
- Network connectivity maintained throughout

If any criterion fails → investigate before proceeding to live testing!

---

## ✅ Phase 5: Small-Capital Live Testing

### Pre-Live Readiness Check

- [ ] Simulation completed 24+ hours without issues
- [ ] All error paths tested and handled correctly
- [ ] Emergency stop procedure documented
- [ ] Rollback plan available
- [ ] Backup strategy implemented
- [ ] Daily loss limit configured (20%)

### Gradual Capital Deployment

| Day | Max Position/Side | Total Exposure | Notes |
|-----|-------------------|----------------|-------|
| Day 1 | $5 | $10 | Validate execution only |
| Day 2-3 | $5 | $10 | Monitor fee impact |
| Day 4-7 | $5-7 | $10-14 | Test volatility response |
| Week 2 | $7-10 | $14-20 | Scale cautiously |

### Safety Mechanisms Active

1. **Daily Loss Limit**: `$10 × 20% = $2` max daily loss → auto-stop
2. **Max Position**: `$5 per side` → no single order exceeds this
3. **Heartbeat**: If bot stops reporting for 5 min → alert triggered
4. **Emergency Kill Switch**: 
   ```bash
   sudo pkill -f polymaster-btc-bot
   ```

### Emergency Procedures

| Issue | Action | Command |
|-------|--------|---------|
| Unexplained losses | Stop immediately | `sudo systemctl stop polymaster-btc-bot` |
| Bot hangs/crashes | Restart | `sudo systemctl restart polymaster-btc-bot` |
| WebSocket disconnects | Wait 5min then restart | Same as above |
| Unexpected memory spike | Investigate logs | `tail -f logs/errors.log` |

---

## ✅ Phase 6: Production Deployment

### Post-Simulation Actions

- [ ] Review full 24h log file
- [ ] Identify and document any edge cases
- [ ] Update config based on findings
- [ ] Schedule weekly audits (Sunday 3 AM UTC)
- [ ] Add VPS to monitoring system (Grafana optional)

### Go-Live Checklist

- [ ] SIMULATE_MODE=false in .env
- [ ] Telegram alerts configured
- [ ] Monitoring dashboard active
- [ ] Daily audit cron job scheduled
- [ ] Backup verification complete
- [ ] Team notified of go-live

### Production Monitoring

```bash
# Real-time log viewing
sudo journalctl -u polymaster-btc-bot -f

# Health check (every 5 min via cron)
python health_check.py

# Telegram alerts (manual trigger)
python send_alert.py info "System running normally"
python send_alert.py warning "High latency detected"
python send_alert.py critical "Daily loss limit reached!"
```

---

## 📊 Deployment Timeline Summary

```
Day 1 (Thu)
├─ 11:56 AM - Plan creation ✅ DONE
├─ 12:00 PM - VPS setup (Phase 1) 15 min
├─ 12:15 PM - Config & security (Phase 2) 10 min
├─ 12:25 PM - WebSocket tests (Phase 3) 5 min
└─ 12:30 PM - Start simulation (Phase 4)

Day 2-28 (Fri-Sun)
├─ Continue simulation for 24h minimum
├─ Monitor via Telegram alerts
├─ Run periodic health checks
└─ Document any issues

Day 3+ (Mon+)
├─ Start live testing ($10 exposure)
├─ Scale gradually over 2 weeks
└─ Full production by end of Month 1
```

---

## 🔧 Troubleshooting Reference

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| WS connection fails | Firewall blocking 443 outbound | Check UFW rules, test from local |
| Requote >200ms | Network latency high | Try different VPS region, optimize code |
| Memory >500MB | Log files too large | Check disk, rotate logs |
| Balance mismatch | Old orders not cancelled | Run cleanup script manually |
| Duplicate orders | Race condition in placement | Implement mutex lock |
| Crash at startup | Missing dependency | Run `pip install -r requirements.txt` |

---

## 📝 Documentation Files Created Today

| File | Purpose | Location |
|------|---------|----------|
| `VPS_DEPLOYMENT_PLAN.md` | Complete deployment roadmap | `/projects/polymaster-btc-bot/` |
| `deploy_vps.sh` | One-click setup script | `/projects/polymaster-btc-bot/` |
| `test_ws_quick_check.py` | WebSocket validation | `/projects/polymaster-btc-bot/` |
| `setup_monitoring.sh` | Alert system configuration | `/projects/polymaster-btc-bot/` |
| `DEPLOYMENT_CHECKLIST_2026-03-19.md` | This checklist | `/projects/polymaster-btc-bot/` |

---

## 💬 Questions?

Refer to specific sections:
- **Setup issues**: See `VPS_DEPLOYMENT_PLAN.md`, Phase 1
- **Configuration help**: Check `.env` template in Phase 2
- **Testing problems**: Review `test_ws_quick_check.py` documentation
- **Monitoring needs**: Follow `setup_monitoring.sh` instructions
- **Emergency procedures**: Keep this checklist handy

---

*Last updated: Thu 2026-03-19 11:56 PDT*  
*Next review: After simulation completes*

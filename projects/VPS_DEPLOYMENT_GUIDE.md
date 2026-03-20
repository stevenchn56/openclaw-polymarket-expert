# VPS Deployment Checklist for Polymarket Bot 🚀

**NY Region Server | <5ms Latency Target | Security Hardened**

---

## 📋 Pre-Deployment Preparation

### 1️⃣ Select VPS Provider (Recommended)

| Provider | NY Location | Price/Month | Latency to Polymarket | Notes |
|----------|-------------|-------------|----------------------|-------|
| **DigitalOcean** | NYC3 | $40/mo | ~3ms | Easy setup, good docs |
| **Linode (Akamai)** | Newark | $48/mo | ~2ms | Excellent support |
| **Vultr** | New York | $45/mo | ~4ms | High-frequency trading friendly |
| **AWS EC2** | us-east-1 | $60+/mo | ~5ms | Enterprise-grade, more config |

**Recommendation**: DigitalOcean NYC3 - Best balance of cost/performance

### 2️⃣ Server Specifications

```yaml
OS: Ubuntu 22.04 LTS (Jammy Jellyfish)
CPU: 2 vCPUs minimum
RAM: 4GB RAM minimum
Storage: 80GB NVMe SSD
Network: 1Gbps unmetered bandwidth
Location: New York (NYC3/NYC1)
```

### 3️⃣ SSH Key Generation (Before Purchase)

```bash
# Generate ED25519 key pair (stronger than RSA 4096)
ssh-keygen -t ed25519 -f ~/.ssh/polymaster_vps_key -N ""

# Show public key for server setup
cat ~/.ssh/polymaster_vps_key.pub
```

---

## 🔐 Post-Deployment Setup Sequence

### Step A: Initial Connection & Root Access

```bash
# Connect as root (will be prompted for password on first login)
ssh root@your_server_ip

# Change root password (if not already set)
passwd
```

### Step B: Run Security Hardening Script

```bash
# Download the hardening script
wget https://raw.githubusercontent.com/stevenking/polymaster-bot/main/vps-security-harden.sh
chmod +x vps-security-harden.sh

# Execute as root
sudo ./vps-security-harden.sh
```

**What it does:**
- ✅ Creates `polymaster_bot` user (no root login)
- ✅ Changes SSH port to random high port (20000-60000)
- ✅ Configures UFW firewall (SSH only)
- ✅ Installs fail2ban (brute-force protection)
- ✅ Sets up daily backup automation
- ✅ Configures systemd service

### Step C: SSH Key Distribution

After running hardening script, you'll see a NEW public key like:

```
ED25519: AAAAC3... polymaster_bot@server
```

**Add this to your local machine's known hosts:**

```bash
# On YOUR LOCAL MACBOOK
mkdir -p ~/.ssh/polymaster_keys
cp /path/to/server/new_public_key ~/.ssh/polymaster_keys/vps_ed25519

# Test connection with new key
ssh -i ~/.ssh/polymaster_keys/vps_ed25519 -p [custom_port] polymaster_bot@[server_ip]
```

### Step D: Clone Trading Bot Repository

```bash
# After successful SSH login
cd ~
git clone https://github.com/stevenking/polymaster-bot.git
cd polymaster-btc-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step E: Configure Environment Variables

```bash
# Copy secure template
cp .env.example ~/.secrets/.env
nano ~/.secrets/.env
```

Fill in these critical values:

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `WALLET_PRIVATE_KEY` | Ethereum wallet private key | Your MetaMask/Ledger |
| `POLYGON_RPC_URL` | RPC endpoint | Alchemy/Infura free tier |
| `POLYSCAN_API_KEY` | Transaction explorer API | polygonscan.com/apis |
| `INITIAL_CAPITAL` | Starting capital | Start with $1000 |
| `TRADE_AMOUNT_USD` | Per-trade size | $5 max per trade |
| `DAILY_LOSS_LIMIT_PCT` | Auto-pause threshold | 20% default |

### Step F: Start Trading Bot

```bash
# Create systemd service
sudo nano /etc/systemd/system/polymaster-bot.service

# Paste service configuration (from README.md)
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable polymaster-bot
sudo systemctl start polymaster-bot

# Check status
sudo systemctl status polymaster-bot

# Monitor logs in real-time
journalctl -u polymaster-bot -f
```

---

## 🧪 Testing Phase (Critical!)

### 1. Simulated Trading (Paper Mode)

Before using real funds:

```bash
# Edit main.py temporarily
nano main.py

# Set SIMULATE=true at top of file
SIMULATE = True  # Don't actually place orders

# Run for 24 hours
python main.py
```

Watch for:
- ✅ Strategy correctly identifies T-10s signals
- ✅ Confidence scores match expectations (~85%)
- ✅ No crashes or memory leaks
- ✅ Logs show proper order formatting

### 2. Small Capital Test

If paper mode succeeds:

```bash
SIMULATE = False

# Fund account with minimum viable amount ($50)
python main.py
```

Run for 3 days monitoring:
- Win rate accuracy
- Fill probability vs reality
- Fee calculations
- Position balancing

### 3. Gradual Scale Up

```
Day 1-3: $50 total capital (test phase)
Day 4-7: $200 total capital (stabilize)
Week 2+: $1000+ (full production)
```

---

## 📊 Monitoring Dashboard

### System Health Checks

```bash
# CPU/RAM usage
htop

# Disk space
df -h

# Network connections
netstat -tuln | grep LISTEN

# Fail2ban status
sudo fail2ban-client status sshd

# Backup log
cat /var/log/polymaster_backups.log
```

### Bot-Specific Monitoring

```bash
# View recent trades
journalctl -u polymaster-bot --since "1 hour ago" | grep "💰 Generated Quote"

# Check position balance
grep "Current Balance:" /var/log/journal/*.log

# Daily statistics
grep "Session Statistics:" /var/log/journal/*.log
```

---

## 🚨 Emergency Procedures

### If Bot Crashes or Spins Out of Control

```bash
# IMMEDIATE ACTION: Stop trading bot
sudo systemctl stop polymaster-bot

# Check why it failed
sudo journalctl -u polymaster-bot -n 100 --no-pager

# Review pause conditions
cat ~/projects/polymaster-btc-bot/risk_manager/auto_pause.py | grep PAUSE_TRIGGER

# Restart after investigation
sudo systemctl start polymaster-bot
```

### If SSH Locked Out

**This happens when:**
- Wrong custom port configured
- Firewall blocks IP
- fail2ban over-blocks

**Recovery steps via VPS control panel:**
1. Access DigitalOcean/Linode web console
2. Reboot server
3. Mount rescue disk if needed
4. Reset SSH config: `rm /etc/ssh/sshd_config && apt reinstall openssh-server`
5. Restore from backup

### If Market Volatility Causes Max Losses

**Auto-pause should trigger at $200 daily loss (20% of $1000).**

Check status:
```bash
sudo systemctl status polymaster-bot
```

Resume manually after review:
```bash
# Reset daily stats (WARNING: clears loss counter)
cd ~/projects/polymaster-btc-bot
python3 -c "from risk_manager.auto_pause import AutoPauseManager; AutoPauseManager().reset_daily_stats()"

# Then restart
sudo systemctl restart polymaster-bot
```

---

## 🔄 Maintenance Schedule

### Daily (Automatic)

```cron
# Backups at 2 AM UTC
0 2 * * * /home/polymaster_bot/scripts/daily_backup.sh
```

### Weekly

```bash
# Sunday morning: Check health
openclaw cron run [healthcheck-id]

# Review weekly performance metrics
tail -n 1000 /var/log/journal/polymaster*.log | grep "Session Statistics"
```

### Monthly

```bash
# Update system packages
apt update && apt upgrade -y

# Rotate SSH keys (every 90 days recommended)
ssh-keygen -t ed25519 -f ~/.ssh/polymaster_vps_key_new

# Test fail2ban effectiveness
sudo fail2ban-client get sshd findtime
```

---

## 📞 Support Contacts

| Issue Type | Resolution Path | Timeframe |
|------------|----------------|-----------|
| SSH connectivity | Web console → reboot | Immediate |
| Service crash | `systemctl restart` | <5 min |
| Memory leak | `systemctl restart` + increase RAM | <10 min |
| Database corruption | Restore from backup | <30 min |
| Major bug fix | Pull latest code + restart | <15 min |

**Primary Contact:** Steven King (Telegram @8146993586)  
**Secondary:** GitHub Issues for code bugs

---

## ✅ Pre-Launch Validation Checklist

Before going live:

- [ ] SSH connection tested with new key
- [ ] UFW shows correct rules (`ufw status verbose`)
- [ ] Fail2ban active (`fail2ban-client status sshd`)
- [ ] Daily backup runs successfully (`ls -la ~/backup/`)
- [ ] All API keys verified working
- [ ] Paper mode ran for 24+ hours without errors
- [ ] Emergency stop procedure documented
- [ ] VPS billing/usage alerts configured

---

*Created: 2026-03-19 | Version: 1.0*  
*Last Updated: [Date of last maintenance]*

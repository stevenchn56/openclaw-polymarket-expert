#!/bin/bash

# ============================================================
# Polymarket Bot VPS Security Hardening Script
# Author: Steven King | Date: 2026-03-19
# Purpose: Secure a fresh Ubuntu/Debian server for production use
# ============================================================

set -e  # Exit on any error

echo "🔐 Starting VPS Security Hardening..."
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================
# Step 1: System Update & Cleanup
# ============================================================
log_info "Step 1: Updating system packages..."
apt update && apt upgrade -y
apt autoremove -y
apt autoclean -y
log_info "✅ System updated"

# ============================================================
# Step 2: Create Dedicated User (NO ROOT LOGIN)
# ============================================================
log_info "Step 2: Creating dedicated bot user..."
BOT_USER="polymarket_bot"
useradd -m -s /bin/bash $BOT_USER
echo "$BOT_USER ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
log_info "✅ User $BOT_USER created"

# ============================================================
# Step 3: SSH Hardening
# ============================================================
log_info "Step 3: Configuring SSH security..."

# Backup original config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Apply secure SSH configuration
cat > /tmp/sshd_hardened.conf << EOF
# Disable root login
PermitRootLogin no

# Change default port to non-standard
Port $(shuf -i 20000-60000 -n 1)

# Use only SSH key authentication
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys

# Disable empty passwords
PermitEmptyPasswords no

# Disable X11 forwarding
X11Forwarding no

# Use strong ciphers only
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com

# Enable strict mode
StrictModes yes

# Limit authentication attempts
MaxAuthTries 3
MaxSessions 10

# Login grace time
LoginGraceTime 60

# Logging level
LogLevel VERBOSE

# Client alive interval (disconnect idle connections after 5 min)
ClientAliveInterval 300
ClientAliveCountMax 2

# Only allow our specific user
AllowUsers $BOT_USER
EOF

mv /tmp/sshd_hardened.conf /etc/ssh/sshd_config

# Generate SSH key pair for the bot user if not exists
sudo -u $BOT_USER mkdir -p /home/$BOT_USER/.ssh
sudo -u $BOT_USER chmod 700 /home/$BOT_USER/.ssh
sudo -u $BOT_USER ssh-keygen -t ed25519 -f /home/$BOT_USER/.ssh/id_ed25519 -N "" -q

# Set permissions
chown -R $BOT_USER:$BOT_USER /home/$BOT_USER/.ssh
chmod 600 /home/$BOT_USER/.ssh/authorized_keys 2>/dev/null || true

systemctl restart sshd
log_info "✅ SSH hardened"
log_warn "⚠️  REMEMBER TO COPY THE NEW PUBLIC KEY before restarting SSH!"

# ============================================================
# Step 4: UFW Firewall Configuration
# ============================================================
log_info "Step 4: Configuring UFW firewall..."

# Install UFW if not present
if ! command -v ufw &> /dev/null; then
    apt install -y ufw
fi

# Reset firewall rules
ufw --force reset
ufw disable

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow ONLY SSH on custom port (update with actual port from above)
CUSTOM_SSH_PORT=$(grep "^Port " /etc/ssh/sshd_config | awk '{print $2}')
ufw allow $CUSTOM_SSH_PORT/tcp

# Log denied packets
ufw logging on

# Enable firewall
ufw --force enable

log_info "✅ UFW configured (allowing port $CUSTOM_SSH_PORT only)"

# Save UFW status for reference
ufw status verbose > /home/$BOT_USER/ufw_status.txt 2>/dev/null || true

# ============================================================
# Step 5: Fail2ban Installation
# ============================================================
log_info "Step 5: Installing fail2ban anti-brute-force protection..."

apt install -y fail2ban

# Configure fail2ban jail
mkdir -p /etc/fail2ban/jail.d

cat > /etc/fail2ban/jail.d/polymarket-hardening.conf << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
backend = systemd

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 86400  # Ban for 24 hours
findtime = 300   # Check last 5 minutes
EOF

systemctl enable fail2ban
systemctl restart fail2ban

log_info "✅ Fail2ban installed and configured"

# ============================================================
# Step 6: Environment Variables & Key Storage
# ============================================================
log_info "Step 6: Setting up secure key storage..."

# Create secure directory for sensitive files
mkdir -p /home/$BOT_USER/.secrets
chmod 700 /home/$BOT_USER/.secrets

# Store environment template securely
cat > /home/$BOT_USER/.secrets/.env.template << 'TEMPLATE'
# CRITICAL: Never commit this file! Copy to .env instead
WALLET_PRIVATE_KEY=your_private_key_here
POLYGON_RPC_URL=https://polygon-rpc.com
POLYSCAN_API_KEY=your_polygonscan_api_key
INITIAL_CAPITAL=1000.0
TRADE_AMOUNT_USD=5.00
DAILY_LOSS_LIMIT_PCT=20.0
PER_TRADE_MAX_LOSS_USD=5.0
TEMPLATE

chown -R $BOT_USER:$BOT_USER /home/$BOT_USER/.secrets
chmod 600 /home/$BOT_USER/.secrets/.env.template

log_info "✅ Secure directory created at ~/.secrets"

# ============================================================
# Step 7: Daily Backup Script
# ============================================================
log_info "Step 7: Creating automated backup script..."

cat > /home/$BOT_USER/scripts/daily_backup.sh << 'BACKUP_SCRIPT'
#!/bin/bash
# Daily backup of critical files
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup"
mkdir -p $BACKUP_DIR

# Backup secrets and configs
tar -czf $BACKUP_DIR/polymaster_backup_$DATE.tar.gz \
    /home/polymarket_bot/.secrets \
    /home/polymarket_bot/projects/polymarket-btc-bot/config.py \
    /home/polymarket_bot/projects/polymaster-btc-bot/main.py 2>/dev/null || true

# Keep only last 7 days of backups
find $BACKUP_DIR -name "polymaster_backup_*.tar.gz" -mtime +7 -delete

echo "[$(date)] Backup completed: polymarket_backup_$DATE.tar.gz" >> /var/log/polymarket_backups.log
BACKUP_SCRIPT

chmod +x /home/$BOT_USER/scripts/daily_backup.sh
chown -R $BOT_USER:$BOT_USER /home/$BOT_USER/scripts

# Add to cron for daily execution at 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /home/polymarket_bot/scripts/daily_backup.sh") | crontab -

log_info "✅ Daily backup scheduled (2:00 AM UTC)"

# ============================================================
# Step 8: Monitoring & Alerting Setup
# ============================================================
log_info "Step 8: Installing monitoring tools..."

# Install htop and sysstat for resource monitoring
apt install -y htop sysstat iotop

# Set up process autostart for trading bot
cat > /etc/systemd/system/polymarket-bot.service << 'SYSTEMD_SERVICE'
[Unit]
Description=Polymarket BTC Window Market Making Bot
After=network.target

[Service]
Type=simple
User=polymarket_bot
WorkingDirectory=/home/polymarket_bot/projects/polymaster-btc-bot
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/polymaster_bot/projects/polymaster-btc-bot/venv/bin/python main.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SYSTEMD_SERVICE

chmod 644 /etc/systemd/system/polymaster-bot.service
systemctl daemon-reload

log_info "✅ Systemd service configured"

# ============================================================
# Step 9: Disk Space & Resource Limits
# ============================================================
log_info "Step 9: Configuring resource limits..."

# Add ulimit settings to /etc/security/limits.d/polymaster.conf
cat > /etc/security/limits.d/polymaster.conf << 'LIMITS_CONFIG'
polymaster_bot soft nofile 65535
polymaster_bot hard nofile 65535
polymaster_bot soft nproc 4096
polymaster_bot hard nproc 4096
LIMITS_CONFIG

log_info "✅ Resource limits configured (65k file descriptors)"

# ============================================================
# SUMMARY & NEXT STEPS
# ============================================================
echo ""
echo "=============================================="
echo "🎉 VPS SECURITY HARDENING COMPLETE!"
echo "=============================================="
echo ""
echo "📋 Summary:"
echo "  ✅ System updated and cleaned"
echo "  ✅ Dedicated user created: $BOT_USER"
echo "  ✅ SSH hardened (root disabled, custom port)"
echo "  ✅ UFW firewall active (port $CUSTOM_SSH_PORT only)"
echo "  ✅ Fail2ban protecting against brute force"
echo "  ✅ Secure key storage: ~/.secrets/"
echo "  ✅ Daily backups scheduled (2 AM UTC)"
echo "  ✅ Systemd service configured"
echo "  ✅ Resource limits set"
echo ""
echo "🔧 Next Steps:"
echo ""
echo "1. SSH TO YOUR SERVER AS NEW USER:"
echo "   ssh -p $CUSTOM_SSH_PORT $BOT_USER@your_vps_ip"
echo ""
echo "2. DEPLOY TRADING BOT:"
echo "   git clone <repo-url> ~/projects/polymaster-btc-bot"
echo "   cd ~/projects/polymaster-btc-bot"
echo "   python3 -m venv venv && source venv/bin/activate"
echo "   pip install -r requirements.txt"
echo ""
echo "3. CONFIGURE ENVIRONMENT:"
echo "   cp .env.example .secrets/.env"
echo "   nano .secrets/.env  # Fill in your API keys"
echo ""
echo "4. START THE BOT:"
echo "   systemctl start polymaster-bot"
echo "   systemctl status polymaster-bot"
echo ""
echo "5. MONITOR LOGS:"
echo "   journalctl -u polymaster-bot -f"
echo ""
echo "🚨 CRITICAL WARNINGS:"
echo ""
echo "⚠️  BEFORE LEAVING THIS SHELL:"
echo "   - Copy your SSH public key (~/.ssh/id_ed25519.pub)"
echo "   - Test SSH connection from your local machine"
echo "   - DO NOT disconnect until verified working!"
echo ""
echo "📞 Need help? Check memory/2026-03-19.md or ask Steven."
echo ""

#!/bin/bash
# =============================================================================
# Polymaster BTC Bot v2.0.1 - One-Click VPS Deployment Script
# Target: Ubuntu 22.04 LTS | Python 3.10+ | QuantVPS (New York)
# =============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Catch errors in pipes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_USER="polymaster"
APP_DIR="/home/${APP_USER}/polymaster-btc-bot"
GIT_REPO="${GIT_REPO:-https://github.com/your-org/polymaster-btc-bot.git}"
BRANCH="${BRANCH:-main}"

# Print colored messages
print_status() { echo -e "${BLUE}⚙️  $*${NC}"; }
print_success() { echo -e "${GREEN}✅ $*${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $*${NC}"; }
print_error() { echo -e "${RED}❌ $*${NC}"; }

# =============================================================================
# Main Setup
# =============================================================================

echo ""
echo "=========================================="
echo "  POLYMASTER BTC BOT v2.0.1 DEPLOYMENT"
echo "=========================================="
echo ""
echo "Target: Ubuntu 22.04 LTS"
echo "User:   ${APP_USER}"
echo "Dir:    ${APP_DIR}"
echo ""

# Step 1: Create application user
print_status "Creating application user..."
if id "${APP_USER}" &>/dev/null; then
    print_warning "User '${APP_USER}' already exists, skipping..."
else
    sudo adduser --disabled-login --gecos "Polymaster Bot" "${APP_USER}" || {
        print_error "Failed to create user!"
        exit 1
    }
fi

# Step 2: Clone repository
print_status "Cloning repository from ${GIT_REPO}..."
sudo mkdir -p /home/${APP_USER}
sudo chown $(whoami):$(whoami) /home/${APP_USER}
cd /home/${APP_USER}

if [ ! -d "polymaster-btc-bot" ]; then
    git clone "${GIT_REPO}" polymaster-btc-bot || {
        print_error "Git clone failed!"
        exit 1
    }
    cd polymaster-btc-bot
    git checkout "${BRANCH}" 2>/dev/null || true
else
    cd polymaster-btc-bot
    print_warning "Repository already exists, pulling latest changes..."
    git pull origin "${BRANCH}" || true
fi

# Step 3: Set up Python virtual environment
print_status "Setting up Python 3.10 virtual environment..."
PYTHON_VERSION="python3.10"

if ! command -v "${PYTHON_VERSION}" &>/dev/null; then
    print_warning "${PYTHON_VERSION} not found, installing..."
    sudo apt update && sudo apt install -y "${PYTHON_VERSION}" "${PYTHON_VERSION}-venv" "${PYTHON_VERSION}-dev"
fi

rm -rf venv
"${PYTHON_VERSION}" -m venv venv || {
    print_error "Failed to create virtual environment!"
    exit 1
}

# Activate venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel || {
    print_error "Failed to upgrade pip!"
    exit 1
}

# Step 4: Install dependencies
print_status "Installing Python dependencies..."
if [ -f "requirements_websocket.txt" ]; then
    pip install -r requirements_websocket.txt || {
        print_error "Failed to install websocket dependencies!"
        exit 1
    }
fi

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt || {
        print_error "Failed to install core dependencies!"
        exit 1
    }
fi

print_success "Dependencies installed successfully!"

# Step 5: Create directories and config files
print_status "Creating directory structure..."
mkdir -p logs data backups
chmod 750 logs data backups

# Create .env template if not exists
if [ ! -f ".env" ]; then
    print_status "Creating .env template..."
    cat > .env <<EOF
# API Credentials (REPLACE THESE!)
TELEGRAM_BOT_TOKEN=your_token_here
POLYMARKET_API_KEY=your_api_key_here
POLYMARKET_API_SECRET=your_api_secret_here

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
EOF
    chmod 600 .env
    print_warning "⚠️  Please edit .env file with your actual credentials!"
fi

# Copy example config if env doesn't exist
if [ ! -f "config.json" ] && [ -f "config.example.json" ]; then
    cp config.example.json config.json
fi

# Step 6: Configure systemd service
print_status "Configuring systemd service..."
cat > /etc/systemd/system/polymaster-btc-bot.service <<EOF
[Unit]
Description=Polymaster BTC Market Maker v2.0.1
After=network.target

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin"
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable polymaster-btc-bot
print_success "Systemd service configured!"

# Step 7: Configure firewall (UFW)
print_status "Configuring firewall (UFW)..."
if command -v ufw &>/dev/null; then
    sudo ufw allow 22/tcp comment "SSH"
    sudo ufw allow 80/tcp comment "HTTP" || true
    sudo ufw allow 443/tcp comment "HTTPS" || true
    sudo ufw --force enable || print_warning "UFW configuration skipped"
else
    print_warning "UFW not found, skipping firewall setup"
fi

# Step 8: Install monitoring tools
print_status "Installing monitoring tools..."
sudo apt install -y htop iotop nethogs net-tools curl git || true

# Step 9: Install fail2ban for SSH protection
print_status "Installing fail2ban..."
if ! systemctl list-unit-files | grep -q fail2ban; then
    sudo apt install -y fail2ban || print_warning "fail2ban installation skipped"
    sudo systemctl enable fail2ban || true
fi

# =============================================================================
# Post-Installation Tasks
# =============================================================================

print_status "Completing post-installation tasks..."

# Set proper ownership
sudo chown -R ${APP_USER}:${APP_USER} "${APP_DIR}"
chmod -R 750 "${APP_DIR}"
chmod 600 "${APP_DIR}/.env" 2>/dev/null || true

# Test the application
print_status "Running quick verification test..."
su - ${APP_USER} -c "cd ${APP_DIR} && source venv/bin/activate && python -c 'import websocket, requests, pandas; print(\"✅ Dependencies OK\")'" || {
    print_warning "Verification test failed or skipped"
}

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "=========================================="
echo -e "${GREEN}  ✅ DEPLOYMENT COMPLETE!${NC}"
echo "=========================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. 📝 Edit ${APP_DIR}/.env with your actual credentials"
echo "2. 🔧 Configure trading parameters (MAX_POSITION_PER_SIDE, etc.)"
echo "3. 🚀 Start the bot:"
echo "   sudo systemctl start polymaster-btc-bot"
echo "4. 📊 Check status:"
echo "   sudo systemctl status polymaster-btc-bot"
echo "5. 📜 View logs:"
echo "   sudo journalctl -u polymaster-btc-bot -f"
echo ""
echo "🧪 Run integration tests:"
echo "   cd ${APP_DIR} && source venv/bin/activate && python test_ws_integration.py"
echo ""
echo "💡 Enable simulation mode first:"
echo "   In .env: SIMULATE_MODE=true"
echo ""
echo "=========================================="
echo ""

exit 0

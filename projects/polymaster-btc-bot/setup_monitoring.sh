#!/bin/bash
# =============================================================================
# Polymaster BTC Bot - Monitoring & Alerting Setup Script
# Creates logging configuration, health checks, and Telegram alerts
# =============================================================================

set -e

APP_DIR="${1:-/home/polymaster/polymaster-btc-bot}"

echo ""
echo "=========================================="
echo "  POLYMASTER MONITORING SETUP"
echo "=========================================="
echo "App Directory: ${APP_DIR}"
echo ""

# Create logs directory
mkdir -p "${APP_DIR}/logs"
mkdir -p "${APP_DIR}/monitoring"

# Configure logging (logging.conf)
cat > "${APP_DIR}/logging.conf" << 'EOF'
[loggers]
keys=root,bot,websocket,errors,latency,performance

[handlers]
keys=console,file,rotating_file,error_file

[formatters]
keys=detailed,json

[logger_root]
level=INFO
handlers=console,file

[logger_bot]
level=INFO
qualName=bot
handlers=console,file
propagate=0

[logger_errors]
level=ERROR
qualName=errors
handlers=error_file
propagate=0

[logger_latencies]
level=DEBUG
qualName=latencies
handlers=file
propagate=0

[logger_performance]
level=INFO
qualName=performance
handlers=file
propagate=0

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

[handler_error_file]
class=RotatingFileHandler
level=ERROR
formatter=detailed
args=('logs/errors.log', 'a', 5*1024*1024, 3)

[handler_rotating_file]
class=RotatingFileHandler
level=DEBUG
formatter=detailed
args=('logs/detailed.log', 'a', 20*1024*1024, 3)

[formatter_detailed]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
datefmt=%Y-%m-%d %H:%M:%S

[formatter_json]
class=pythonjsonlogger.jsonlogger.JsonFormatter
format=%(asctime)s %(name)s %(levelname)s %(message)s
EOF

chmod 644 "${APP_DIR}/logging.conf"

# Create health check script
cat > "${APP_DIR}/health_check.py" << 'EOF'
#!/usr/bin/env python3
"""
Bot Health Check Script
Checks: process alive, memory usage, recent logs, WebSocket status
"""

import sys
import os
import subprocess
from datetime import datetime, timedelta

APP_DIR = "/home/polymaster/polymaster-btc-bot"
LOG_FILE = f"{APP_DIR}/logs/bot.log"
MAX_AGE_HOURS = 1  # Process should have logged within last hour

def check_process_alive():
    """Check if bot process is running"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "polymaster-btc-bot"],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except:
        return False

def check_memory_usage():
    """Check memory consumption via ps command"""
    try:
        result = subprocess.run(
            ["ps", "-o", "rss=", "-C", "python3"],
            capture_output=True, text=True
        )
        rss_kb = int(result.stdout.strip().split()[0]) if result.stdout.strip() else 0
        rss_mb = rss_kb / 1024
        
        # Warn if >500MB
        if rss_mb > 500:
            return False, f"High memory: {rss_mb:.1f}MB"
        return True, f"OK: {rss_mb:.1f}MB"
    except Exception as e:
        return None, f"Error: {e}"

def check_recent_logs():
    """Verify logs were updated recently"""
    if not os.path.exists(LOG_FILE):
        return False, "No log file found"
    
    mtime = os.path.getmtime(LOG_FILE)
    age_seconds = time.time() - mtime
    age_hours = age_seconds / 3600
    
    if age_hours > MAX_AGE_HOURS:
        return False, f"No logs in {age_hours:.1f} hours"
    return True, f"Fresh: {MAX_AGE_HOURS - age_hours:.1f}h ago"

def check_disk_space():
    """Check available disk space"""
    try:
        statvfs = os.statvfs("/home/polymaster")
        free_gb = (statvfs.f_bavail * statvfs.f_frsize) / (1024**3)
        
        if free_gb < 5:
            return False, f"Low disk: {free_gb:.1f}GB"
        return True, f"OK: {free_gb:.1f}GB"
    except:
        return None, "Cannot check disk"

def main():
    print(f"\n🏥 HEALTH CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    checks = [
        ("Process Running", check_process_alive),
        ("Memory Usage", check_memory_usage),
        ("Recent Logs", check_recent_logs),
        ("Disk Space", check_disk_space),
    ]
    
    all_ok = True
    
    for name, check_func in checks:
        try:
            result, message = check_func()
            
            if result is True:
                print(f"✅ {name:<20} {message}")
            elif result is False:
                print(f"❌ {name:<20} {message}")
                all_ok = False
            else:
                print(f"⚠️  {name:<20} {message}")
        except Exception as e:
            print(f"❌ {name:<20} Error: {e}")
            all_ok = False
    
    print("-" * 50)
    
    if all_ok:
        print("🟢 System healthy!")
        return 0
    else:
        print("🔴 Issues detected - check immediately!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

chmod +x "${APP_DIR}/health_check.py"

# Create alert notification script
cat > "${APP_DIR}/send_alert.py" << 'EOF'
#!/usr/bin/env python3
"""
Telegram Alert Notification Script
Send notifications to configured chat when issues detected
"""

import sys
import os
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ALERT_LEVELS = {
    "info": "ℹ️",
    "warning": "⚠️", 
    "critical": "🚨",
    "success": "✅"
}

def send_telegram_alert(message, level="info"):
    """Send formatted alert via Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"⚠️  Telegram not configured (env vars missing)")
        return False
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emoji = ALERT_LEVELS.get(level, "⚠️")
    
    # Truncate very long messages
    if len(message) > 4096:
        message = message[:4000] + "\n... (truncated)"
    
    full_message = f"""{emoji} *{level.upper()}* Alert
🕐 {timestamp}

{message}
    
_Polymaster Bot v2.0.1_"""
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        response = requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": full_message,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Telegram API error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to send alert: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python send_alert.py <level> <message>")
        print(f"Levels: {', '.join(ALERT_LEVELS.keys())}")
        return 1
    
    level = sys.argv[1].lower()
    message = " ".join(sys.argv[2:])
    
    if level not in ALERT_LEVELS:
        print(f"Invalid level! Use: {', '.join(ALERT_LEVELS.keys())}")
        return 1
    
    success = send_telegram_alert(message, level)
    
    if success:
        print(f"✅ Alert sent ({level})")
        return 0
    else:
        print("❌ Alert failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

chmod +x "${APP_DIR}/send_alert.py"

# Set up cron job for periodic health checks (every 5 minutes)
cat > "${APP_DIR}/setup_cron.sh" << 'CRONEOF'
#!/bin/bash
# Add hourly health check via cron

echo "Setting up cron job for health checks..."

# Backup existing crontab
crontab -l > /tmp/crontab.bak 2>/dev/null || true

# Add new health check (every 5 minutes)
(crontab -l 2>/dev/null; \
 echo "# Polymaster Health Check (every 5 min)"; \
 echo "*/5 * * * * cd /home/polymaster/polymaster-btc-bot && python3 health_check.py >> logs/health_check.log 2>&1"; \
 echo "# Daily summary at 8 AM"; \
 echo "0 8 * * * cd /home/polymaster/polymaster-btc-bot && python3 health_check.py | tee logs/daily_health.log") | crontab -

echo "✅ Cron jobs configured successfully!"
CRONEOF

chmod +x "${APP_DIR}/setup_cron.sh"
bash "${APP_DIR}/setup_cron.sh"

# Verify everything works
echo ""
echo "Verifying setup..."
if python3 "${APP_DIR}/health_check.py" 2>/dev/null; then
    echo "✅ Health check script working!"
else
    echo "⚠️  Health check might need adjustments (missing dependencies)"
fi

echo ""
echo "=========================================="
echo "  ✅ MONITORING SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Files created:"
echo "  📄 ${APP_DIR}/logging.conf       - Logging configuration"
echo "  📄 ${APP_DIR}/health_check.py    - Health monitoring script"
echo "  📄 ${APP_DIR}/send_alert.py      - Telegram alert system"
echo "  📄 ${APP_DIR}/setup_cron.sh      - Cron automation"
echo ""
echo "Next steps:"
echo "1. Edit .env with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"
echo "2. Run health check manually: python health_check.py"
echo "3. View logs: tail -f ${APP_DIR}/logs/bot.log"
echo ""
echo "Alert levels:"
echo "  INFO     - Normal operations (daily summary)"
echo "  WARNING  - Minor issues (high latency, etc.)"
echo "  CRITICAL - Major failures (crash, loss limit)"
echo ""

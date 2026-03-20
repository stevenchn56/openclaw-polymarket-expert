"""Configuration settings for Polymaster BTC bot"""

import os
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class TradingSettings:
    """Trading-related configuration"""
    
    # Capital settings
    TRADING_CAPITAL: float = 50.0  # Total capital to trade
    DEFAULT_CAPITAL: float = 50.0  # Base capital if not specified
    
    # Position sizing
    POSITION_SIZE_BASE: float = 10.0  # Base position size in USD
    MIN_POSITION_SIZE: float = 1.0  # Minimum acceptable position size
    MAX_POSITION_SIZE: float = 50.0  # Maximum position size per trade
    
    # Trading frequency
    TRADES_PER_HOUR: int = 2
    TRADING_LOOP_INTERVAL_SECONDS: float = 30.0  # Check every 30 seconds


@dataclass 
class RiskManagementSettings:
    """Risk management configuration"""
    
    # Loss limits
    DAILY_LOSS_LIMIT_PCT: float = 0.05  # 5% daily loss limit
    MONTHLY_LOSS_LIMIT_PCT: float = 0.15  # 15% monthly loss limit
    MAX_DRAWDOWN_PCT: float = 0.25  # 25% max drawdown from peak
    TOTAL_CAPITAL_LOSS_LIMIT: float = 0.40  # 40% total capital loss = emergency stop
    
    # Position adjustment rules
    POSITION_SIZE_ADJUST_WIN: float = 1.10  # Increase by 10% after win
    POSITION_SIZE_ADJUST_LOSS: float = 0.80  # Decrease by 20% after loss
    
    # Consecutive loss handling
    CONSECUTIVE_PAUSE_THRESHOLD: int = 3  # Pause after 3 consecutive losses
    WIN_RECOVERY_THRESHOLD: int = 2  # Resume after 2 consecutive wins
    
    # Per-trade limits
    MAX_LOSS_PER_TRADE_USD: float = 5.0  # Immediate close if loss > $5


@dataclass
class MEVProtectionSettings:
    """MEV protection system configuration"""
    
    # Monitoring parameters
    MONITORING_INTERVAL_SECONDS: float = 2.0  # Check for threats every 2 seconds
    BLACKLIST_DURATION_HOURS: int = 24  # Blacklist attackers for 24 hours
    EMERGENCY_COOLDOWN_MINUTES: int = 5  # Wait before resuming after emergency
    
    # Threat detection thresholds
    GAS_WAR_THRESHOLD_PCT: float = 20.0  # 20% gas price spike triggers alert
    SPAM_CANCEL_THRESHOLD: int = 10  # 10+ cancels in 1 minute = spam attack
    NONCE_JUMP_THRESHOLD: int = 2  # Skip more than 2 nonces = suspicious
    
    # Position scaling based on threat level
    THREAT_SCALING: dict = None  # Populated below
    
    def __post_init__(self):
        self.THREAT_SCALING = {
            "normal": {"max_threats": 0, "position_multiplier": 1.0},
            "caution": {"max_threats": 3, "position_multiplier": 0.7},
            "high_alert": {"max_threats": 10, "position_multiplier": 0.5},
            "critical": {"max_threats": float('inf'), "position_multiplier": 0.2}
        }


@dataclass
class APISettings:
    """API and connection settings"""
    
    # Polymaster endpoints
    POLYMARKER_API_URL: str = "https://polymaster.ai"
    POLYMARKER_API_VERSION: str = "v1"
    
    # Binance WebSocket (for price feeds)
    BINANCE_WS_URL: str = "wss://stream.binance.com:9443/ws/btcusdt@trade"
    BINANCE_STREAM_SYMBOL: str = "BTCUSDT"
    
    # Connection timeouts
    REQUEST_TIMEOUT_SECONDS: int = 30
    WEBSOCKET_PING_INTERVAL: int = 30
    MAX_RECONNECT_ATTEMPTS: int = 5
    
    # Rate limiting
    RATE_LIMIT_REQUESTS_PER_SECOND: int = 5
    RATE_LIMIT_BURST_SIZE: int = 10


@dataclass
class LoggingSettings:
    """Logging configuration"""
    
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE: str = "logs/polymaster.log"
    LOG_MAX_BYTES: int = 10_000_000  # 10MB per file
    LOG_BACKUP_COUNT: int = 5  # Keep 5 backup files
    ENABLE_CONSOLE_LOG: bool = True
    ENABLE_FILE_LOG: bool = True


@dataclass
class Environment:
    """Environment-specific settings"""
    
    # Runtime flags
    SIMULATION_MODE: bool = False
    ENABLE_MEV_PROTECTION: bool = True
    DRY_RUN_MODE: bool = False  # Don't actually submit orders
    
    # Deployment mode
    DEPLOYMENT_ENV: str = "production"  # development, staging, production
    
    # Version info
    BOT_VERSION: str = "2.0"
    BUILD_DATE: str = "2026-03-19"


# Global configuration instance
def get_config():
    """Get the global configuration"""
    return Config()


class Config:
    """Main configuration container"""
    
    def __init__(self):
        self.trading = TradingSettings()
        self.risk = RiskManagementSettings()
        self.mev = MEVProtectionSettings()
        self.api = APISettings()
        self.logging = LoggingSettings()
        self.env = Environment()
        
        # Override with environment variables where applicable
        self._load_from_env()
    
    def _load_from_env(self):
        """Load runtime configuration from environment variables"""
        
        # Trading capital
        if 'TRADING_CAPITAL' in os.environ:
            try:
                self.trading.TRADING_CAPITAL = float(os.environ['TRADING_CAPITAL'])
            except ValueError:
                print(f"Warning: Invalid TRADING_CAPITAL value, using default")
        
        # Simulation mode
        if 'SIMULATION_MODE' in os.environ:
            val = os.environ['SIMULATION_MODE'].lower()
            self.env.SIMULATION_MODE = val in ('true', '1', 'yes')
        
        # MEV protection
        if 'ENABLE_MEV_PROTECTION' in os.environ:
            val = os.environ['ENABLE_MEV_PROTECTION'].lower()
            self.env.ENABLE_MEV_PROTECTION = val in ('true', '1', 'yes')
        
        # Log level
        if 'LOG_LEVEL' in os.environ:
            self.logging.LOG_LEVEL = os.environ['LOG_LEVEL'].upper()
    
    def validate_required(self):
        """Validate that required environment variables are set"""
        required = ['POLYMARKET_API_KEY', 'PRIVATE_KEY', 'POLYMARKET_WALLET_ADDRESS']
        missing = [var for var in required if var not in os.environ]
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Please set these in your .env file or shell environment."
            )
        
        return True


# Create singleton instance
config = Config()

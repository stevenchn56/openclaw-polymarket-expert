"""
Configuration templates for Risk Manager by deployment stage

Usage:
    python run_bot.py --config=mainnet_conservative_v1
"""

from decimal import Decimal  # Required for position sizes


# ==============================================================================
# TESTNET CONFIGURATION (First Week of Testnet)
# ==============================================================================

TESTNET_CONFIG = {
    "config_name": "TESTNET_CONFIG",
    "deployment_stage": "testnet",
    "description": "Ultra conservative setup for first week on testnet - learning phase",
    
    # Position Limits
    "max_position_btc": Decimal("1.0"),      # Maximum 1 BTC per trade
    "min_confidence_threshold": Decimal("60"),  # Only trade when >= 60% confident
    
    # Drawdown Limits (percentage)
    "max_daily_drawdown_pct": Decimal("3"),   # Stop if down 3% today
    "max_session_drawdown_pct": Decimal("5"), # Pause session if down 5% total
    "max_total_drawdown_pct": Decimal("10"),  # Permanent stop if lifetime down 10%
    
    # Loss Limits
    "max_loss_per_hour": Decimal("0.25"),     # Stop trading for an hour if lost 0.25 BTC
    "max_loss_per_day": Decimal("0.5"),       # Stop for rest of day if lost 0.5 BTC
    "max_consecutive_losses": 2,              # Stop after 2 consecutive losses
    
    # Time Controls
    "trading_hours_limit": 8,                 # Cap at 8 hours of trading/day
    
    # Kelly Criterion
    "kelly_fraction": Decimal("0.25"),        # Use 25% of full Kelly criterion
    
    # Fee Rate (basis points)
    "fee_rate_bps": 10,
    
    # Circuit Breaker Settings
    "emergency_stop_enabled": True,           # Allow emergency stop via API
}


# ==============================================================================
# MAINNET CONSERVATIVE v1 (Month 1 After Testnet Success)
# ==============================================================================

MAINNET_CONSERVATIVE_V1 = {
    "config_name": "MAINNET_CONSERVATIVE_V1",
    "deployment_stage": "mainnet",
    "description": "Conservative mainnet mode - Month 1 after proving strategy on testnet",
    
    # Position Limits (2x testnet)
    "max_position_btc": Decimal("2.0"),       # Max 2 BTC per trade
    "min_confidence_threshold": Decimal("60"),  # Same strict confidence threshold
    
    # Drawdown Limits (slightly more relaxed than testnet)
    "max_daily_drawdown_pct": Decimal("4"),   # Stop if down 4% today
    "max_session_drawdown_pct": Decimal("6"), # Pause session if down 6% total
    "max_total_drawdown_pct": Decimal("12"),  # Permanent stop if lifetime down 12%
    
    # Loss Limits (proportional to position size increase)
    "max_loss_per_hour": Decimal("0.40"),     # Stop trading for an hour if lost 0.4 BTC
    "max_loss_per_day": Decimal("0.8"),       # Stop for rest of day if lost 0.8 BTC
    "max_consecutive_losses": 3,              # Allow 3 consecutive losses now
    
    # Time Controls
    "trading_hours_limit": 10,                # Can trade up to 10 hours/day
    
    # Kelly Criterion
    "kelly_fraction": Decimal("0.25"),        # Still use 25% Kelly for safety
    
    # Fee Rate (basis points)
    "fee_rate_bps": 10,
    
    # Circuit Breaker Settings
    "emergency_stop_enabled": True,
}


# ==============================================================================
# MAINNET OPTIMIZED (Month 2+ After Proven Profitability)
# ==============================================================================

MAINNET_OPTIMIZED = {
    "config_name": "MAINNET_OPTIMIZED",
    "deployment_stage": "mainnet",
    "description": "Full power mode - Only after 4+ weeks of profitable mainnet trading",
    
    # Position Limits (Maximum allowed by exchange)
    "max_position_btc": Decimal("5.0"),       # Max 5 BTC per trade (exchange limit)
    "min_confidence_threshold": Decimal("50"),  # More lenient confidence threshold
    
    # Drawdown Limits (standard risk management)
    "max_daily_drawdown_pct": Decimal("5"),   # Industry standard 5% daily limit
    "max_session_drawdown_pct": Decimal("7"), # Session pause at 7% drawdown
    "max_total_drawdown_pct": Decimal("15"),  # Professional grade 15% hard stop
    
    # Loss Limits (higher tolerance)
    "max_loss_per_hour": Decimal("0.50"),     # $50K loss per hour is acceptable
    "max_loss_per_day": Decimal("1.0"),       # $100K loss per day maximum
    "max_consecutive_losses": 3,              # Maintain 3-loss circuit breaker
    
    # Time Controls
    "trading_hours_limit": 12,                # Can trade longer days if desired
    
    # Kelly Criterion
    "kelly_fraction": Decimal("0.33"),        # Increase to 33% Kelly (aggressive but still fractional)
    
    # Fee Rate (basis points)
    "fee_rate_bps": 10,
    
    # Circuit Breaker Settings
    "emergency_stop_enabled": True,
}


# ==============================================================================
# BACKTEST CONFIGURATION (Backtesting Mode)
# ==============================================================================

BACKTEST_CONFIG = {
    "config_name": "BACKTEST_CONFIG",
    "deployment_stage": "backtesting",
    "description": "Default configuration for backtesting scenarios",
    
    "max_position_btc": Decimal("3.0"),
    "min_confidence_threshold": Decimal("55"),
    
    "max_daily_drawdown_pct": Decimal("5"),
    "max_session_drawdown_pct": Decimal("8"),
    "max_total_drawdown_pct": Decimal("15"),
    
    "max_loss_per_hour": Decimal("0.30"),
    "max_loss_per_day": Decimal("0.6"),
    "max_consecutive_losses": 3,
    
    "trading_hours_limit": 10,
    
    "kelly_fraction": Decimal("0.25"),
    "fee_rate_bps": 10,
    
    "emergency_stop_enabled": True,
}


# ==============================================================================
# Config Loading Utility
# ==============================================================================

def load_config(config_name: str) -> dict:
    """
    Load a configuration template by name
    
    Args:
        config_name: Name of configuration (e.g., 'TESTNET_CONFIG')
        
    Returns:
        Configuration dictionary
        
    Raises:
        ValueError: If config_name not found
        
    Examples:
        >>> config = load_config('TESTNET_CONFIG')
        >>> print(config['max_position_btc'])
        Decimal('1.0')
        
        >>> config = load_config('MAINNET_OPTIMIZED')
        >>> print(config['max_daily_drawdown_pct'])
        Decimal('5')
    """
    configs = {
        'TESTNET_CONFIG': TESTNET_CONFIG,
        'MAINNET_CONSERVATIVE_V1': MAINNET_CONSERVATIVE_V1,
        'MAINNET_OPTIMIZED': MAINNET_OPTIMIZED,
        'BACKTEST_CONFIG': BACKTEST_CONFIG,
    }
    
    if config_name not in configs:
        raise ValueError(
            f"Unknown config: {config_name}. Available options: {list(configs.keys())}"
        )
    
    return configs[config_name].copy()  # Return a copy to prevent mutation


if __name__ == "__main__":
    print("Testing Risk Manager Config Templates...\n")
    
    # Test each config
    for config_name in ['TESTNET_CONFIG', 'MAINNET_CONSERVATIVE_V1', 
                        'MAINNET_OPTIMIZED', 'BACKTEST_CONFIG']:
        print(f"{'='*60}")
        print(f"📋 {config_name}")
        print('='*60)
        
        config = load_config(config_name)
        print(f"Description: {config['description']}")
        print(f"\nPosition Limits:")
        print(f"  Max Size: {config['max_position_btc']} BTC")
        print(f"  Min Confidence: {config['min_confidence_threshold']}%")
        
        print(f"\nDrawdown Limits:")
        print(f"  Daily: {config['max_daily_drawdown_pct']}%")
        print(f"  Session: {config['max_session_drawdown_pct']}%")
        print(f"  Total: {config['max_total_drawdown_pct']}%")
        
        print(f"\nLoss Limits:")
        print(f"  Per Hour: {config['max_loss_per_hour']} BTC")
        print(f"  Per Day: {config['max_loss_per_day']} BTC")
        print(f"  Consecutive Losses: {config['max_consecutive_losses']}")
        
        print(f"\nKelly Fraction: {config['kelly_fraction'] * 100}%")
        print(f"Fee Rate: {config['fee_rate_bps']} bps")
        print()

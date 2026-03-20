"""Advanced Risk Manager for Polymaster BTC trading bot"""

import os
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Optional
import json
import logging
import pathlib

logger = logging.getLogger(__name__)


@dataclass
class RiskStatus:
    """Current risk assessment status"""
    
    # Position limits
    can_trade: bool = True
    current_position_limit: Decimal = Decimal("10")
    position_multiplier: float = 1.0
    
    # Loss tracking
    daily_pnl: Decimal = Decimal("0")
    monthly_pnl: Decimal = Decimal("0")
    peak_value: Decimal = Decimal("50")
    current_peak_drawdown: Decimal = Decimal("0")
    
    # Consecutive trades
    consecutive_losses: int = 0
    consecutive_wins: int = 0
    
    # State
    is_paused: bool = False
    pause_reason: str = ""
    last_check_time: datetime = field(default_factory=datetime.now)
    
    # Timestamps for reset
    daily_reset_time: Optional[datetime] = None
    monthly_reset_time: Optional[datetime] = None


class AdvancedRiskManager:
    """
    Advanced Risk Management System
    
    Implements comprehensive risk controls including:
    - Position sizing with dynamic adjustment
    - Daily/monthly loss limits
    - Drawdown protection
    - Consecutive trade logic
    - State persistence
    """
    
    def __init__(self, initial_capital: float = 50.0):
        """
        Initialize the risk manager
        
        Args:
            initial_capital: Starting capital in USD
        """
        self.initial_capital = Decimal(str(initial_capital))
        self.current_value = self.initial_capital
        
        # Risk parameters
        self.daily_loss_limit_pct = Decimal("0.05")  # 5%
        self.monthly_loss_limit_pct = Decimal("0.15")  # 15%
        self.max_drawdown_pct = Decimal("0.25")  # 25%
        self.total_capital_loss_limit = Decimal("0.40")  # 40%
        
        # Position adjustment rules
        self.position_size_adjust_win = Decimal("1.10")  # +10%
        self.position_size_adjust_loss = Decimal("0.80")  # -20%
        
        # Trade thresholds
        self.consecutive_pause_threshold = 3  # Pause after 3 losses
        self.win_recovery_threshold = 2  # Resume after 2 wins
        
        # Per-trade limits
        self.max_loss_per_trade_usd = Decimal("5.00")
        
        # Base position size
        self.base_position_size = Decimal("10")
        self.min_position_size = Decimal("1")
        self.max_position_size = Decimal("50")
        
        # Current state
        self.risk_status = RiskStatus()
        self.risk_status.daily_reset_time = datetime.now(timezone.utc)
        self.risk_status.monthly_reset_time = datetime.now(timezone.utc)
        
        # File paths
        self.workspace_path = pathlib.Path(__file__).parent.parent
        self.state_file = self.workspace_path / "rds_data" / "trading_state.json"
        
        # Ensure directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"AdvancedRiskManager initialized with ${initial_capital} capital")
    
    def get_dynamic_position_size(self, threat_multiplier: float = 1.0) -> Decimal:
        """
        Calculate position size based on multiple factors
        
        Args:
            threat_multiplier: MEV threat scaling (0.2-1.0)
            
        Returns:
            Position size in USD
        """
        # Start with base size
        position = self.base_position_size
        
        # Apply MEV threat scaling
        position *= Decimal(str(threat_multiplier))
        
        # Apply win/loss adjustments
        if self.risk_status.consecutive_wins > 0:
            position *= self.position_size_adjust_win ** self.risk_status.consecutive_wins
        
        if self.risk_status.consecutive_losses > 0:
            position *= self.position_size_adjust_loss ** self.risk_status.consecutive_losses
        
        # Enforce limits
        position = max(self.min_position_size, min(position, self.max_position_size))
        
        return round(position, 2)
    
    def check_daily_limits(self) -> tuple[bool, str]:
        """
        Check if daily loss limit has been breached
        
        Returns:
            Tuple of (can_continue, reason)
        """
        daily_limit_usd = self.initial_capital * self.daily_loss_limit_pct
        
        if self.risk_status.daily_pnl < -daily_limit_usd:
            reason = f"Daily loss limit reached: {self.risk_status.daily_pnl}"
            return False, reason
        
        return True, ""
    
    def check_monthly_limits(self) -> tuple[bool, str]:
        """
        Check if monthly loss limit has been breached
        
        Returns:
            Tuple of (can_continue, reason)
        """
        monthly_limit_usd = self.initial_capital * self.monthly_loss_limit_pct
        
        if self.risk_status.monthly_pnl < -monthly_limit_usd:
            reason = f"Monthly loss limit reached: {self.risk_status.monthly_pnl}"
            return False, reason
        
        return True, ""
    
    def check_drawdown(self) -> tuple[bool, str]:
        """
        Check if drawdown exceeds maximum threshold
        
        Returns:
            Tuple of (can_continue, reason)
        """
        max_drawdown_usd = self.initial_capital * self.max_drawdown_pct
        
        if self.risk_status.current_peak_drawdown > max_drawdown_usd:
            reason = f"Max drawdown exceeded: {self.risk_status.current_peak_drawdown}"
            return False, reason
        
        return True, ""
    
    def can_trade(self) -> tuple[bool, str]:
        """
        Comprehensive trade permission check
        
        Returns:
            Tuple of (allowed, reason)
        """
        # Check if paused
        if self.risk_status.is_paused:
            return False, f"Trading paused: {self.risk_status.pause_reason}"
        
        # Check limits
        can_daily, reason = self.check_daily_limits()
        if not can_daily:
            return False, reason
        
        can_monthly, reason = self.check_monthly_limits()
        if not can_monthly:
            return False, reason
        
        can_dd, reason = self.check_drawdown()
        if not can_dd:
            return False, reason
        
        return True, ""
    
    def record_trade_result(
        self,
        profit_loss: Decimal,
        was_winner: bool
    ) -> None:
        """
        Record trade result and update state
        
        Args:
            profit_loss: P&L in USD
            was_winner: True if trade was profitable
        """
        # Update P&L tracking
        self.risk_status.daily_pnl += profit_loss
        self.risk_status.monthly_pnl += profit_loss
        
        # Update current value
        self.current_value += profit_loss
        
        # Track peak and drawdown
        if self.current_value > self.risk_status.peak_value:
            self.risk_status.peak_value = self.current_value
        
        drawdown = self.risk_status.peak_value - self.current_value
        self.risk_status.current_peak_drawdown = drawdown
        
        # Update consecutive trade counter
        if was_winner:
            self.risk_status.consecutive_wins += 1
            self.risk_status.consecutive_losses = 0
            
            # Check if we should resume from pause
            if (self.risk_status.consecutive_wins >= 
                self.win_recovery_threshold and 
                self.risk_status.is_paused):
                self.resume_trading("Recovered after 2 wins")
                
        else:
            self.risk_status.consecutive_losses += 1
            self.risk_status.consecutive_wins = 0
            
            # Check if we should pause
            if self.risk_status.consecutive_losses >= self.consecutive_pause_threshold:
                self.pause_trading(
                    f"{self.risk_status.consecutive_losses} consecutive losses"
                )
        
        # Reset daily P&L at midnight UTC
        if self._should_reset_daily():
            self.reset_daily_stats()
        
        # Persist state
        self.save_state()
    
    def _should_reset_daily(self) -> bool:
        """Check if daily stats should be reset (midnight UTC)"""
        now = datetime.now(timezone.utc)
        if not self.risk_status.daily_reset_time:
            return False
        
        # Reset if we've crossed midnight UTC
        return (now.date() > 
                self.risk_status.daily_reset_time.date())
    
    def reset_daily_stats(self) -> None:
        """Reset daily P&L tracking"""
        old_daily_pnl = self.risk_status.daily_pnl
        self.risk_status.daily_pnl = Decimal("0")
        self.risk_status.daily_reset_time = datetime.now(timezone.utc)
        
        logger.info(f"Daily stats reset (old PnL: ${old_daily_pnl:.2f})")
    
    def pause_trading(self, reason: str) -> None:
        """Pause trading due to risk event"""
        self.risk_status.is_paused = True
        self.risk_status.pause_reason = reason
        
        logger.warning(f"⚠️ TRADING PAUSED: {reason}")
    
    def resume_trading(self, reason: str = "Manual intervention") -> None:
        """Resume trading after pause"""
        self.risk_status.is_paused = False
        self.risk_status.pause_reason = reason
        
        logger.info(f"✅ Trading resumed: {reason}")
    
    def get_current_status(self) -> dict:
        """Get comprehensive status report"""
        return {
            'capital': float(self.initial_capital),
            'current_value': float(self.current_value),
            'daily_pnl': float(self.risk_status.daily_pnl),
            'monthly_pnl': float(self.risk_status.monthly_pnl),
            'max_drawdown': float(self.risk_status.current_peak_drawdown),
            'consecutive_wins': self.risk_status.consecutive_wins,
            'consecutive_losses': self.risk_status.consecutive_losses,
            'is_paused': self.risk_status.is_paused,
            'pause_reason': self.risk_status.pause_reason,
            'can_trade': self.can_trade()[0],
            'position_limit': float(self.get_dynamic_position_size()),
        }
    
    def save_state(self) -> None:
        """Persist current state to disk"""
        try:
            state = {
                'timestamp': datetime.now().isoformat(),
                'initial_capital': float(self.initial_capital),
                'current_value': float(self.current_value),
                'risk_status': {
                    'daily_pnl': float(self.risk_status.daily_pnl),
                    'monthly_pnl': float(self.risk_status.monthly_pnl),
                    'peak_value': float(self.risk_status.peak_value),
                    'current_peak_drawdown': float(self.risk_status.current_peak_drawdown),
                    'consecutive_losses': self.risk_status.consecutive_losses,
                    'consecutive_wins': self.risk_status.consecutive_wins,
                    'is_paused': self.risk_status.is_paused,
                    'pause_reason': self.risk_status.pause_reason,
                }
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.debug("State saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def load_state(self) -> bool:
        """Load state from disk if available"""
        try:
            if not self.state_file.exists():
                logger.info("No existing state file found")
                return False
            
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            # Restore state
            self.risk_status.daily_pnl = Decimal(str(state['risk_status']['daily_pnl']))
            self.risk_status.monthly_pnl = Decimal(str(state['risk_status']['monthly_pnl']))
            self.risk_status.peak_value = Decimal(str(state['risk_status']['peak_value']))
            self.risk_status.current_peak_drawdown = Decimal(str(state['risk_status']['current_peak_drawdown']))
            self.risk_status.consecutive_losses = state['risk_status']['consecutive_losses']
            self.risk_status.consecutive_wins = state['risk_status']['consecutive_wins']
            self.risk_status.is_paused = state['risk_status']['is_paused']
            self.risk_status.pause_reason = state['risk_status'].get('pause_reason', '')
            
            logger.info(f"State loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return False
    
    def emergency_stop(self) -> None:
        """Emergency stop - halt all trading immediately"""
        self.pause_trading("EMERGENCY STOP - Total capital loss limit")
        self.save_state()
        
        logger.critical("🚨 EMERGENCY TRADING HALTED")


# Example usage
if __name__ == "__main__":
    # Test the risk manager
    print("="*60)
    print("Testing AdvancedRiskManager")
    print("="*60)
    
    rm = AdvancedRiskManager(initial_capital=50.0)
    
    print("\nInitial Status:")
    print(json.dumps(rm.get_current_status(), indent=2))
    
    print("\nSimulating trades...")
    
    # Simulate some winning trades
    for i in range(3):
        rm.record_trade_result(Decimal("2.00"), was_winner=True)
        print(f"\nAfter win #{i+1}:")
        print(f"  Consecutive wins: {rm.risk_status.consecutive_wins}")
        print(f"  Position size: ${rm.get_dynamic_position_size():.2f}")
    
    # Simulate some losing trades
    for i in range(4):
        rm.record_trade_result(Decimal("-1.50"), was_winner=False)
        print(f"\nAfter loss #{i+1}:")
        print(f"  Consecutive losses: {rm.risk_status.consecutive_losses}")
        print(f"  Is paused: {rm.risk_status.is_paused}")
        print(f"  Pause reason: {rm.risk_status.pause_reason}")
    
    print("\nFinal Status:")
    print(json.dumps(rm.get_current_status(), indent=2))

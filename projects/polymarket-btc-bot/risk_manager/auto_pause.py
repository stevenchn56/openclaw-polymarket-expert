"""
Risk Management Module

Core components:
- Position tracker for YES/NO balance monitoring
- Auto-pause on daily loss limits
- Per-trade maximum loss enforcement
- Consecutive loss detection
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
import os


@dataclass
class TradeExecution:
    """Record of a single trade execution"""
    timestamp: datetime
    side: str              # "YES" or "NO"
    entry_price: float
    exit_price: Optional[float]
    size_usd: float
    pnl: Optional[float]   # None if still open
    fee_rate_bps: int
    win: Optional[bool]    # None if not closed


class AutoPauseManager:
    """
    Automatic trading pause system
    
    Triggers when any of these conditions are met:
    - Daily loss > 20% of initial capital
    - Per-trade loss > $5
    - 3 consecutive losses → 60 minute pause
    """
    
    DAILY_LOSS_LIMIT_PCT = 0.20
    PER_TRADE_MAX_LOSS_USD = 5.0
    CONSECUTIVE_LOSS_LIMIT = 3
    PAUSE_DURATION_MINUTES = 60
    
    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.trades: List[TradeExecution] = []
        self.is_paused = False
        self.pause_until: Optional[datetime] = None
        self.consecutive_losses = 0
        
        # Load from environment if available
        self._load_env_config()
    
    def _load_env_config(self):
        """Load configuration from environment variables"""
        try:
            daily_limit = float(os.getenv('DAILY_LOSS_LIMIT_PCT', '20.0'))
            self.DAILY_LOSS_LIMIT_PCT = daily_limit / 100.0
            
            per_trade = float(os.getenv('PER_TRADE_MAX_LOSS_USD', '5.0'))
            self.PER_TRADE_MAX_LOSS_USD = per_trade
            
            consecutive = int(os.getenv('MAX_CONSECUTIVE_LOSSES', '3'))
            self.CONSECUTIVE_LOSS_LIMIT = consecutive
            
            pause_min = int(os.getenv('PAUSE_RESTART_DELAY_MINUTES', '60'))
            self.PAUSE_DURATION_MINUTES = pause_min
            
        except ValueError as e:
            print(f"Warning: Invalid config values, using defaults: {e}")
    
    def record_trade(self, side: str, entry_price: float, exit_price: Optional[float], size_usd: float, fee_rate_bps: int) -> TradeExecution:
        """Record a new trade execution"""
        pnl = None
        is_win = None
        
        if exit_price is not None:
            # Calculate PnL based on side
            if side == "YES":
                # Long position: profit when price increases
                pnl = (exit_price - entry_price) * (size_usd / entry_price)
                is_win = pnl > 0
            else:
                # Short position: profit when price decreases
                pnl = (entry_price - exit_price) * (size_usd / exit_price)
                is_win = pnl > 0
        
        # Deduct fees
        fee = size_usd * (fee_rate_bps / 10000)
        if pnl is not None:
            pnl -= fee
        
        trade = TradeExecution(
            timestamp=datetime.now(timezone.utc),
            side=side,
            entry_price=entry_price,
            exit_price=exit_price,
            size_usd=size_usd,
            pnl=pnl,
            fee_rate_bps=fee_rate_bps,
            win=is_win
        )
        
        self.trades.append(trade)
        
        # Check consecutive losses
        if is_win is False:
            self.consecutive_losses += 1
        elif is_win is True:
            self.consecutive_losses = 0
        
        return trade
    
    def check_pause_conditions(self) -> dict:
        """
        Evaluate all pause conditions
        
        Returns:
            Dict with status information
        """
        result = {
            'paused': False,
            'reason': None,
            'pause_until': None
        }
        
        # Check if already paused
        if self.is_paused:
            now = datetime.now(timezone.utc)
            if self.pause_until and now >= self.pause_until:
                # Pause expired, resume
                self.is_paused = False
                self.pause_until = None
                return {'paused': False, 'resumed': True}
            return result
        
        # Check daily loss limit
        daily_pnl = sum(t.pnl for t in self.trades if t.pnl is not None)
        daily_loss_pct = abs(daily_pnl) / self.initial_capital if daily_pnl < 0 else 0
        
        if daily_loss_pct > self.DAILY_LOSS_LIMIT_PCT:
            self._trigger_pause("Daily loss limit exceeded")
            result['paused'] = True
            result['reason'] = f"Daily loss: ${daily_pnl:.2f} ({daily_loss_pct:.1f}%)"
            result['pause_until'] = self.pause_until.isoformat()
            return result
        
        # Check consecutive losses
        if self.consecutive_losses >= self.CONSECUTIVE_LOSS_LIMIT:
            self._trigger_pause(f"{self.consecutive_losses} consecutive losses")
            result['paused'] = True
            result['reason'] = f"Consecutive losses: {self.consecutive_losses}"
            result['pause_until'] = self.pause_until.isoformat()
            return result
        
        return result
    
    def _trigger_pause(self, reason: str):
        """Initiate automatic pause"""
        self.is_paused = True
        self.pause_until = datetime.now(timezone.utc) + timedelta(minutes=self.PAUSE_DURATION_MINUTES)
        
        print(f"\n⚠️ TRADING PAUSED: {reason}")
        print(f"   Resumes at: {self.pause_until.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"   Reason: {reason}\n")
    
    def check_per_trade_loss(self, entry_price: float, current_price: float, side: str, size_usd: float) -> bool:
        """
        Real-time check for per-trade maximum loss
        
        Returns:
            True if loss exceeds threshold, False otherwise
        """
        if side == "YES":
            current_value = current_price * (size_usd / entry_price)
        else:
            current_value = size_usd * (entry_price / current_price)
        
        unrealized_pnl = current_value - size_usd
        
        if unrealized_pnl < -self.PER_TRADE_MAX_LOSS_USD:
            print(f"⚠️ Per-trade loss limit reached: ${unrealized_pnl:.2f}")
            return True
        
        return False
    
    def get_daily_statistics(self) -> dict:
        """Calculate today's trading statistics"""
        today = datetime.now(timezone.utc).date()
        today_trades = [t for t in self.trades if t.timestamp.date() == today]
        
        if not today_trades:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate_pct': 0.0,
                'total_pnl_usd': 0.0,
                'avg_pnl_usd': 0.0,
                'max_drawdown_pct': 0.0
            }
        
        wins = [t for t in today_trades if t.win == True]
        losses = [t for t in today_trades if t.win == False]
        
        total_pnl = sum(t.pnl for t in today_trades if t.pnl is not None)
        avg_pnl = total_pnl / len(today_trades) if today_trades else 0
        
        # Calculate max drawdown
        equity_curve = [self.initial_capital]
        running_pnl = 0.0
        for t in today_trades:
            if t.pnl is not None:
                running_pnl += t.pnl
                equity_curve.append(self.initial_capital + running_pnl)
        
        peak = max(equity_curve)
        max_drawdown = min([(peak - eq) / peak for eq in equity_curve if peak > 0], default=0.0)
        
        return {
            'total_trades': len(today_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate_pct': round(len(wins) / len(today_trades) * 100, 2) if today_trades else 0.0,
            'total_pnl_usd': round(total_pnl, 2),
            'avg_pnl_usd': round(avg_pnl, 2),
            'max_drawdown_pct': round(max_drawdown * 100, 2)
        }
    
    def get_position_balance(self) -> dict:
        """Current YES/NO position balance"""
        yes_exposure = sum(t.size_usd for t in self.trades if t.side == "YES" and t.pnl is None)
        no_exposure = sum(t.size_usd for t in self.trades if t.side == "NO" and t.pnl is None)
        
        total_exposure = yes_exposure + no_exposure
        imbalance = 0.0
        
        if total_exposure > 0:
            imbalance = abs(yes_exposure - no_exposure) / total_exposure * 100
        
        return {
            'yes_exposure_usd': round(yes_exposure, 2),
            'no_exposure_usd': round(no_exposure, 2),
            'total_exposure_usd': round(total_exposure, 2),
            'imbalance_pct': round(imbalance, 2),
            'needs_rebalancing': imbalance > 30.0  # Need action if >30% imbalance
        }
    
    def reset_daily_stats(self):
        """Reset statistics for new day (call at midnight)"""
        self.trades.clear()
        self.consecutive_losses = 0


class RiskCalculator:
    """Advanced risk metrics calculator"""
    
    @staticmethod
    def calculate_sharpe_ratio(pnl_series: List[float], risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio from list of trade P&Ls"""
        if len(pnl_series) < 2:
            return 0.0
        
        returns = [pnl / sum(abs(pnl_series)) for pnl in pnl_series]
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualized (assuming trades happen over trading days)
        annualized_sharpe = (mean_return / std_return) * np.sqrt(252)
        
        return annualized_sharpe
    
    @staticmethod
    def calculate_max_drawdown(equity_curve: List[float]) -> float:
        """Calculate maximum drawdown percentage"""
        if not equity_curve:
            return 0.0
        
        peak = equity_curve[0]
        max_dd = 0.0
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            
            dd = (peak - equity) / peak
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    @staticmethod
    def calculate_var(pnl_series: List[float], confidence: float = 0.95) -> float:
        """Calculate Value at Risk (VaR) at given confidence level"""
        if not pnl_series:
            return 0.0
        
        var = np.percentile(pnl_series, (1 - confidence) * 100)
        return abs(var)

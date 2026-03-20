"""
Risk Manager Module - Capital Protection System
v1.0 - Core protection mechanisms for Polymaster BTC Bot

Features:
- Max Drawdown Limits (daily & session)
- Position Sizing based on Confidence Score
- Circuit Breaker Logic
- Kelly Criterion Calculator
- State Persistence for Crash Recovery
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
import os
import logging

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Comprehensive risk management system with multiple protection layers
    
    Usage:
        risk_mgr = RiskManager(config={...})
        is_allowed, reason = risk_mgr.check_trade(risk_params)
        
        if is_allowed:
            position_size = risk_mgr.calculate_position_size(confidence_score)
            final_config = risk_mgr.get_trading_config()
    
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize risk manager with configurable parameters
        
        Args:
            config: Dictionary containing risk limits and thresholds
                   Override defaults here or use default values below
        """
        
        # Default Configuration (Conservative Settings)
        self.defaults = {
            # Maximum Drawdown Limits (%)
            'max_daily_drawdown_pct': 0.05,        # 5% daily stop
            'max_session_drawdown_pct': 0.07,      # 7% session stop  
            'max_total_drawdown_pct': 0.15,        # 15% lifetime stop
            
            # Position Sizing Parameters
            'max_position_btc': Decimal('5.00'),   # Max per trade
            'min_confidence_for_trade': 50,        # Min % confidence required
            'max_position_by_confidence': {         # Tiered sizing by confidence
                90: Decimal('5.00'),  # Very high confidence → full size
                75: Decimal('4.00'),  # High confidence → 80% size
                60: Decimal('3.00'),  # Medium confidence → 60% size
                50: Decimal('2.00'),  # Borderline → 40% size
                0: Decimal('0.00')    # Below threshold → no trade
            },
            
            # Circuit Breakers
            'max_loss_per_hour': Decimal('0.50'),  # BTC max loss per hour
            'max_loss_per_day': Decimal('1.00'),   # BTC max loss per day
            'max_consecutive_losses': 3,           # Stop after N losses
            'trading_hours_limit': 8,              # Hours trading per day
            
            # Kelly Criterion Settings
            'kelly_fraction': 0.25,                # Use 25% of full Kelly (half-Kelly recommendation)
            'max_kelly_position': Decimal('3.00'), # Kelly never exceeds this
            
            # Session Tracking
            'session_id': None,
            'start_time': None,
        }
        
        # Apply config overrides
        self.config = {**self.defaults}
        if config:
            self.config.update(config)
            logger.info(f"RiskManager initialized with custom config")
        
        # Runtime State (persisted to file)
        self.state = {
            'session_id': str(datetime.now().timestamp()),
            'start_time': datetime.now(),
            'current_balance': None,
            'peak_balance': None,
            'daily_start_balance': None,
            'daily_high_water': None,
            'hourly_pnl': Decimal('0'),
            'today_pnl': Decimal('0'),
            'consecutive_losses': 0,
            'trades_today': 0,
            'total_trades': 0,
            'last_loss_time': None,
            'hours_traded': 0,
            'positions_open': 0,
        }
        
        # Persistence
        self.persistence_file = '/Users/stevenwang/.openclaw/workspace/projects/polymaster-btc-bot/.risk_state.json'
        
        # Load persisted state if exists
        self._load_state()
        
        logger.info(f"RiskManager initialized | Session ID: {self.state['session_id']}")
    
    # ======================================================================
    # TRADE VALIDATION - Should we allow this trade?
    # ======================================================================
    
    def check_trade(self, 
                    current_price: Decimal,
                    entry_price: Decimal,
                    confidence: float,
                    proposed_size: Decimal,
                    direction: str) -> tuple[bool, str]:
        """
        Validate whether a trade should be executed based on all risk rules
        
        Returns: (is_allowed, rejection_reason)
        """
        
        # Check circuit breakers first
        allowed, reason = self._check_circuit_breakers()
        if not allowed:
            return False, f"CIRCUIT BREAKER: {reason}"
        
        # Check maximum drawdown
        allowed, reason = self._check_max_drawdown()
        if not allowed:
            return False, f"DRAWDOWN LIMIT: {reason}"
        
        # Validate position size
        allowed, reason = self._validate_position_size(proposed_size, confidence)
        if not allowed:
            return False, f"POSITION SIZE: {reason}"
        
        # Check minimum confidence
        if confidence < self.config['min_confidence_for_trade']:
            return False, f"INSUFFICIENT CONFIDENCE ({confidence:.1f}% < min {self.config['min_confidence_for_trade']}%)"
        
        # All checks passed
        return True, "TRADE ALLOWED"
    
    # ======================================================================
    # POSITION SIZE CALCULATION
    # ======================================================================
    
    def calculate_position_size(self, 
                                confidence: float,
                                kelly_fraction: Optional[float] = None) -> Decimal:
        """
        Calculate optimal position size based on confidence and/or Kelly criterion
        
        Args:
            confidence: Strategy confidence score (0-100%)
            kelly_fraction: Override Kelly fraction (default from config)
        
        Returns:
            Optimal BTC amount to trade
        """
        
        # Method 1: Confidence-based sizing (conservative approach)
        confidence_size = self._calculate_by_confidence(confidence)
        
        # Method 2: Kelly criterion (mathematical optimum)
        kelly_size = self._calculate_kelly_size(confidence) if kelly_fraction else Decimal('0')
        
        # Choose the more conservative of the two
        optimal_size = min(confidence_size, kelly_size) if kelly_size > 0 else confidence_size
        
        # Enforce hard limit
        optimal_size = min(optimal_size, self.config['max_position_btc'])
        
        logger.debug(f"Position sizing | Confidence: {confidence:.1f}% | "
                     f"Confidence size: {confidence_size:.3f}BTC | "
                     f"Kelly size: {kelly_size:.3f}BTC | "
                     f"Optimal: {optimal_size:.3f}BTC")
        
        return optimal_size
    
    def _calculate_by_confidence(self, confidence: float) -> Decimal:
        """Linear interpolation between confidence tiers"""
        
        tiers = sorted(self.config['max_position_by_confidence'].items())
        
        # Find bracket
        for i in range(len(tiers) - 1):
            lower_conf, lower_size = tiers[i]
            upper_conf, upper_size = tiers[i + 1]
            
            if lower_conf <= confidence <= upper_conf:
                # Linear interpolation
                ratio = (confidence - lower_conf) / (upper_conf - lower_conf)
                size = lower_size + ratio * (upper_size - lower_size)
                return size.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Below lowest tier
        return Decimal('0.00')
    
    def _calculate_kelly_size(self, win_rate: float) -> Decimal:
        """
        Calculate Kelly Criterion position size
        
        Formula: f* = (bp - q) / b
        where: b = odds received (1:1 for simple markets)
               p = win probability
               q = loss probability (1-p)
        
        We use fractional Kelly (25%) for safety
        """
        
        # Convert win rate to decimal
        p = win_rate / 100
        q = 1 - p
        b = 1.0  # 1:1 odds assumption for prediction markets
        
        # Full Kelly fraction
        if b == 0 or p == 0:
            return Decimal('0')
        
        kelly_fraction = (b * p - q) / b
        
        # Only positive Kelly is worth betting
        if kelly_fraction <= 0:
            return Decimal('0')
        
        # Apply fractional Kelly (more conservative)
        actual_fraction = kelly_fraction * self.config.get('kelly_fraction', 0.25)
        
        # Assume $1000 capital base for calculation
        assumed_capital = Decimal('1000')
        kelly_position = assumed_capital * actual_fraction
        
        # Convert to BTC equivalent (assume $45k/BTC as reference)
        btc_reference_price = Decimal('45000')
        btc_size = kelly_position / btc_reference_price
        
        # Cap at max
        btc_size = min(btc_size, self.config['max_kelly_position'])
        
        return btc_size.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # ======================================================================
    # CIRCUIT BREAKERS
    # ======================================================================
    
    def _check_circuit_breakers(self) -> tuple[bool, str]:
        """Check all time-based circuit breaker conditions"""
        
        now = datetime.now()
        
        # Hourly loss limit
        if self._check_hourly_loss_limit(now):
            return False, f"Hourly loss exceeded ({self.state['hourly_pnl']:.3f}BTC)"
        
        # Daily loss limit  
        if self._check_daily_loss_limit(now):
            return False, f"Daily loss exceeded ({self.state['today_pnl']:.3f}BTC)"
        
        # Consecutive losses
        if self._check_consecutive_losses():
            return False, f"Consecutive losses ({self.state['consecutive_losses']})"
        
        # Trading hours limit
        if self._check_daily_hours_limit(now):
            return False, f"Trading hours exceeded ({self.state['hours_traded']}h)"
        
        return True, ""
    
    def _check_hourly_loss_limit(self, now: datetime) -> bool:
        """Reset hourly PnL tracking"""
        last_hour = now.replace(minute=0, second=0, microsecond=0)
        
        # Track hourly resets implicitly through PnL updates
        if abs(self.state['hourly_pnl']) >= self.config['max_loss_per_hour']:
            return True
        
        return False
    
    def _check_daily_loss_limit(self, now: datetime) -> bool:
        """Reset daily PnL at midnight"""
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if abs(self.state['today_pnl']) >= self.config['max_loss_per_day']:
            return True
        
        return False
    
    def _check_consecutive_losses(self) -> bool:
        """Check if consecutive losses exceed limit"""
        if self.state['consecutive_losses'] >= self.config['max_consecutive_losses']:
            return True
        return False
    
    def _check_daily_hours_limit(self, now: datetime) -> bool:
        """Track cumulative trading hours"""
        return self.state['hours_traded'] >= self.config['trading_hours_limit']
    
    # ======================================================================
    # DRAWDOWN MANAGEMENT
    # ======================================================================
    
    def _check_max_drawdown(self) -> tuple[bool, str]:
        """Monitor drawdown against configured limits"""
        
        if self.state['peak_balance'] is None:
            return True, ""
        
        # Current balance must be set
        if self.state['current_balance'] is None:
            return True, ""
        
        # Calculate drawdown from peak
        drawdown_pct = (self.state['peak_balance'] - self.state['current_balance']) / self.state['peak_balance']
        
        # Check session drawdown
        if drawdown_pct > self.config['max_session_drawdown_pct']:
            return False, f"Session DD: {drawdown_pct*100:.1f}% > limit {self.config['max_session_drawdown_pct']*100:.0f}%"
        
        # Check total drawdown
        if drawdown_pct > self.config['max_total_drawdown_pct']:
            return False, f"Total DD: {drawdown_pct*100:.1f}% > limit {self.config['max_total_drawdown_pct']*100:.0f}%"
        
        # Daily drawdown (separate metric)
        daily_dd = (self.state['daily_high_water'] - self.state['current_balance']) / self.state['daily_high_water']
        if daily_dd > self.config['max_daily_drawdown_pct']:
            return False, f"Daily DD: {daily_dd*100:.1f}% > limit {self.config['max_daily_drawdown_pct']*100:.0f}%"
        
        return True, ""
    
    # ======================================================================
    # POSITION TRACKING & P&L UPDATES
    # ======================================================================
    
    def update_position_info(self, 
                             balance: Optional[Decimal],
                             positions_open: int = 0):
        """
        Update runtime state with current balance and open positions
        
        Call this periodically during operation
        """
        
        now = datetime.now()
        
        # Initialize balance if not set
        if self.state['current_balance'] is None:
            self.state['current_balance'] = balance
        
        # Update peak balance
        if balance and (self.state['peak_balance'] is None or balance > self.state['peak_balance']):
            self.state['peak_balance'] = balance
        
        # Track daily high water mark
        if balance and (self.state['daily_high_water'] is None or balance > self.state['daily_high_water']):
            self.state['daily_high_water'] = balance
        
        # Set daily start balance
        if self.state['daily_start_balance'] is None:
            self.state['daily_start_balance'] = balance
        
        self.state['positions_open'] = positions_open
        
        logger.debug(f"Balance updated | Current: {balance:.2f} | Peak: {self.state['peak_balance']:.2f}")
        
        # Persist state
        self._save_state()
    
    def record_trade_outcome(self, pnl_btc: Decimal, outcome: str):
        """
        Record the result of a completed trade
        
        Args:
            pnl_btc: PnL in BTC (+ profit, - loss)
            outcome: 'WIN' or 'LOSS'
        """
        
        now = datetime.now()
        
        # Update PnL tracking
        self.state['today_pnl'] += pnl_btc
        self.state['hourly_pnl'] += pnl_btc
        
        # Track balance changes
        if self.state['current_balance'] is not None:
            self.state['current_balance'] += pnl_btc
        
        # Reset hourly tracker on new hour
        if now.minute < 5 and now.second < 30:  # Start of new hour
            self.state['hourly_pnl'] = Decimal('0')
        
        # Update counters
        self.state['total_trades'] += 1
        self.state['trades_today'] += 1
        
        # Handle consecutive losses
        if outcome == 'LOSS':
            self.state['consecutive_losses'] += 1
            self.state['last_loss_time'] = now
        elif outcome == 'WIN':
            self.state['consecutive_losses'] = 0
        
        # Log result
        logger.info(f"Trade outcome | Outcome: {outcome} | PnL: {pnl_btc:+.4f}BTC | "
                    f"Consecutive losses: {self.state['consecutive_losses']} | "
                    f"Today PnL: {self.state['today_pnl']:+.4f}BTC")
        
        # Persist immediately
        self._save_state()
    
    def get_trading_metrics(self) -> Dict[str, Any]:
        """Return comprehensive risk metrics dashboard"""
        
        now = datetime.now()
        
        # Calculate uptime
        uptime_minutes = (now - self.state['start_time']).total_seconds() / 60
        
        # Calculate current drawdown
        current_dd = Decimal('0')
        if self.state['peak_balance'] and self.state['current_balance']:
            current_dd = (self.state['peak_balance'] - self.state['current_balance']) / self.state['peak_balance']
        
        # Calculate daily drawdown
        daily_dd = Decimal('0')
        if self.state['daily_high_water'] and self.state['current_balance']:
            daily_dd = (self.state['daily_high_water'] - self.state['current_balance']) / self.state['daily_high_water']
        
        return {
            'session_id': self.state['session_id'],
            'uptime_minutes': round(uptime_minutes),
            'current_balance': self.state['current_balance'],
            'peak_balance': self.state['peak_balance'],
            'total_pnl_btc': self.state['today_pnl'],
            'daily_pnl_btc': self.state['today_pnl'],
            'hourly_pnl_btc': self.state['hourly_pnl'],
            'consecutive_losses': self.state['consecutive_losses'],
            'total_trades': self.state['total_trades'],
            'trades_today': self.state['trades_today'],
            'current_dd_pct': round(current_dd * 100, 2),
            'daily_dd_pct': round(daily_dd * 100, 2),
            'positions_open': self.state['positions_open'],
            'hours_traded': self.state['hours_traded'],
        }
    
    # ======================================================================
    # EMERGENCY FUNCTIONS
    # ======================================================================
    
    def emergency_stop(self, reason: str = "Manual emergency stop"):
        """
        Trigger immediate trading halt
        
        Logs emergency event and persists it
        """
        logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
        self.state['emergency_stopped'] = True
        self.state['emergency_time'] = datetime.now()
        self.state['emergency_reason'] = reason
        self._save_state()
    
    def resume_trading(self):
        """Resume trading after emergency stop"""
        self.state['emergency_stopped'] = False
        self.state['resumed_time'] = datetime.now()
        logger.warning("Trading resumed after emergency stop")
        self._save_state()
    
    # ======================================================================
    # STATE PERSISTENCE
    # ======================================================================
    
    def _save_state(self):
        """Save current state to disk for crash recovery"""
        try:
            with open(self.persistence_file, 'w') as f:
                json.dump({
                    'state': self.state,
                    'config_overrides': {k: v for k, v in self.config.items() 
                                        if k not in self.defaults},
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def _load_state(self):
        """Load persisted state from disk on startup"""
        if not os.path.exists(self.persistence_file):
            logger.info("No saved state found | Starting fresh session")
            return
        
        try:
            with open(self.persistence_file, 'r') as f:
                data = json.load(f)
            
            # Merge loaded state
            saved_state = data.get('state', {})
            self.state.update(saved_state)
            
            logger.info(f"State restored | Session: {saved_state.get('session_id')} | "
                       f"Trades: {saved_state.get('total_trades', 0)} | "
                       f"PnL: {saved_state.get('today_pnl', Decimal('0'))}")
            
        except Exception as e:
            logger.warning(f"Failed to load state, starting fresh: {e}")
    
    # ======================================================================
    # UTILITY METHODS
    # ======================================================================
    
    def get_recommendation(self) -> Dict[str, Any]:
        """
        Get actionable recommendations based on current state
        """
        
        recommendations = []
        warnings = []
        
        # Check drawdown status
        dd_pct = self.get_trading_metrics()['current_dd_pct']
        if dd_pct > 3:
            warnings.append(f"⚠️ Large drawdown detected: {dd_pct:.1f}%")
        
        # Check consecutive losses
        consec_losses = self.state['consecutive_losses']
        if consec_losses >= 2:
            warnings.append(f"⚠️ {consec_losses} consecutive losses - consider reducing position size")
        
        # Check hourly losses
        if abs(self.state['hourly_pnl']) > Decimal('0.25'):
            warnings.append(f"⚠️ Hourly loss: {self.state['hourly_pnl']:.3f}BTC")
        
        # Positive signals
        trades_today = self.state['trades_today']
        if trades_today == 0:
            recommendations.append("🕐 No trades yet today - monitor market conditions")
        elif trades_today >= 5:
            recommendations.append("✅ Good trade frequency - maintain discipline")
        
        return {
            'recommendations': recommendations,
            'warnings': warnings,
            'metrics': self.get_trading_metrics(),
        }
    
    def reset_session(self):
        """Reset daily tracking (useful for next day manually)"""
        self.state['today_pnl'] = Decimal('0')
        self.state['hourly_pnl'] = Decimal('0')
        self.state['consecutive_losses'] = 0
        self.state['trades_today'] = 0
        self.state['daily_start_balance'] = None
        self.state['daily_high_water'] = None
        self._save_state()
        logger.info("Daily session reset")


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

if __name__ == "__main__":
    # Quick test/demo
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Risk Manager Module - Quick Test")
    print("=" * 60)
    
    # Create instance with custom config
    risk_mgr = RiskManager(config={
        'max_daily_drawdown_pct': 0.05,
        'max_position_btc': Decimal('5.00'),
    })
    
    # Test position sizing
    print("\n--- Position Sizing Examples ---")
    for conf in [50, 60, 75, 90]:
        size = risk_mgr.calculate_position_size(conf)
        print(f"Confidence {conf:3.0f}% → {size:.2f} BTC")
    
    # Simulate trade validation
    print("\n--- Trade Validation ---")
    allowed, reason = risk_mgr.check_trade(
        current_price=Decimal('45000'),
        entry_price=Decimal('45050'),
        confidence=75.5,
        proposed_size=Decimal('3.5'),
        direction='LONG'
    )
    print(f"Allowed: {allowed} | Reason: {reason}")
    
    # Simulate trade outcomes
    print("\n--- P&L Tracking ---")
    risk_mgr.record_trade_outcome(Decimal('0.01'), 'WIN')
    risk_mgr.record_trade_outcome(Decimal('-0.02'), 'LOSS')
    
    metrics = risk_mgr.get_trading_metrics()
    print(f"Current PnL: {metrics['total_pnl_btc']:+.4f} BTC")
    print(f"Total trades: {metrics['total_trades']}")
    
    # Get recommendations
    print("\n--- Recommendations ---")
    recs = risk_mgr.get_recommendation()
    for w in recs['warnings']:
        print(w)
    for r in recs['recommendations']:
        print(r)
    
    print("\n✓ Risk Manager module working correctly!")

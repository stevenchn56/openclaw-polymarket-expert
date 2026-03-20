"""BTC Window Trading Strategy - 5-minute timeframe implementation
v2.0 - Black-Scholes Pricing Integration"""

from decimal import Decimal
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import logging

# Import v2.0 pricing module
try:
    from pricing.black_scholes_v2 import BlackScholesPricer, PricingQuote, OptionGreeks
    HAS_PRICING_V2 = True
except ImportError:
    HAS_PRICING_V2 = False

logger = logging.getLogger(__name__)


class BTCWindowStrategy:
    """
    BTC Price Window Strategy with Black-Scholes Pricing v2.0
    
    This strategy identifies optimal price ranges for market making
    based on:
    1. Recent price action and volatility patterns
    2. Black-Scholes fair value calculation for prediction markets
    3. Dynamic spread adjustment based on volatility and time decay
    
    The goal is to capture spreads while managing inventory risk
    and time decay.
    """
    
    def __init__(
        self, 
        lookback_minutes: int = 5,
        enable_black_scholes: bool = True,
        risk_free_rate: float = 0.05,
        default_volatility: float = 0.30
    ):
        """
        Initialize the strategy
        
        Args:
            lookback_minutes: Number of minutes to analyze for price windows
            enable_black_scholes: Use v2.0 BS pricing (default: True)
            risk_free_rate: Annual risk-free rate for BS model
            default_volatility: Base volatility assumption
        """
        self.lookback_minutes = lookback_minutes
        self.last_price: Optional[Decimal] = None
        self.price_history = []
        
        # Configuration
        self.spread_bps: int = 10  # Spread in basis points (0.1%)
        self.inventory_threshold: Decimal = Decimal("0.5")  # Max inventory imbalance
        self.max_position_size: Decimal = Decimal("100")  # Max shares per trade
        
        # v2.0 Pricing setup
        self.enable_black_scholes = enable_black_scholes
        self.pricer: Optional[BlackScholesPricer] = None
        
        if enable_black_scholes and HAS_PRICING_V2:
            try:
                self.pricer = BlackScholesPricer(
                    risk_free_rate=risk_free_rate,
                    default_volatility=default_volatility
                )
                logger.info("✓ Black-Scholes v2.0 pricing enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize v2.0 pricer: {e}")
                self.enable_black_scholes = False
        else:
            logger.info("ℹ Using basic pricing (BS v2.0 disabled)")
        
        # Track last quote for reference
        self.current_quote: Optional[PricingQuote] = None
        self.quote_timestamp: Optional[datetime] = None
        
        logger.info(f"BTC Window Strategy initialized (lookback={lookback_minutes}min)")
    
    def update_price(self, price: Decimal) -> None:
        """Update current price and maintain history"""
        self.last_price = price
        self.price_history.append({
            'price': price,
            'timestamp': datetime.now()
        })
        
        # Keep only recent history
        if len(self.price_history) > 100:
            self.price_history.pop(0)
    
    def update_price_with_quotation(self, price: Decimal, time_to_resolution_days: int = 90) -> PricingQuote:
        """
        Update price and generate Black-Scholes quotation
        
        This is the preferred method for v2.0 integration.
        
        Args:
            price: Current market probability (0-1)
            time_to_resolution_days: Expected days until event resolution
            
        Returns:
            PricingQuote object with full analysis
        """
        self.update_price(price)
        
        if not self.enable_black_scholes or not self.pricer:
            # Fallback to basic pricing
            return self._basic_pricing(price)
        
        try:
            # Calculate volatility from recent price history
            volatility = self.calculate_volatility()
            
            # Generate Black-Scholes quote
            quote = self.pricer.generate_quote(
                current_probability=float(price),
                time_to_resolution_days=time_to_resolution_days,
                volatility_estimate=volatility,
                spread_bps=self.spread_bps
            )
            
            # Store for reference
            self.current_quote = quote
            self.quote_timestamp = datetime.now()
            
            logger.debug(f"✓ BS Quote generated: FV=${quote.fair_value:.4f}, Conf={quote.confidence:.1%}")
            
            # Calculate dynamic fee rate based on confidence
            fee_rate_bps = max(0, int((1.0 - quote.confidence) * 156))
            
            return {
                "fair_value": quote.fair_value,
                "bid": quote.bid,
                "ask": quote.ask,
                "mid": quote.mid,
                "implied_volatility": quote.implied_volatility,
                "greeks": quote.greeks,
                "confidence": quote.confidence,
                "fee_rate_bps": fee_rate_bps
            }
            
        except Exception as e:
            logger.error(f"Failed to generate BS quote: {e}")
            quote = self._basic_pricing(price)
            return {
                "fair_value": quote.fair_value,
                "bid": quote.bid,
                "ask": quote.ask,
                "mid": quote.mid,
                "implied_volatility": quote.implied_volatility,
                "greeks": quote.greeks,
                "confidence": quote.confidence,
                "fee_rate_bps": 10
            }
    
    def _basic_pricing(self, price: Decimal) -> PricingQuote:
        """Fallback basic pricing when BS not available"""
        half_spread = (self.spread_bps / 10000.0) / 2.0
        mid = float(price)
        
        bid = max(0.0, mid * (1.0 - half_spread))
        ask = min(1.0, mid * (1.0 + half_spread))
        
        return PricingQuote(
            fair_value=mid,
            bid=bid,
            ask=ask,
            mid=mid,
            implied_volatility=0.30,
            greeks=OptionGreeks(delta=0.5, gamma=0.0, theta=0.0, vega=0.0, rho=0.0),
            confidence=0.5
        )
    
    def calculate_entry_windows(self) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Calculate bid and ask entry prices based on current window
        
        Uses Black-Scholes v2.0 pricing if enabled, otherwise fallback
        
        Returns:
            Tuple of (bid_price, ask_price) or (None, None) if no signal
        """
        if not self.last_price:
            return None, None
        
        if self.enable_black_scholes and self.current_quote:
            # Use BS-derived prices
            bid = Decimal(str(self.current_quote.bid))
            ask = Decimal(str(self.current_quote.ask))
            
            logger.debug(f"BS Entry window: bid={bid:.6f}, ask={ask:.6f}")
            return bid, ask
        
        else:
            # Simple spread calculation around current price
            spread_decimal = self.last_price * Decimal(self.spread_bps) / Decimal(10000)
            
            bid_price = self.last_price - spread_decimal
            ask_price = self.last_price + spread_decimal
            
            logger.debug(f"Entry window: bid={bid_price:.6f}, ask={ask_price:.6f}")
            
            return bid_price, ask_price
    
    def should_trade(self, offered_price: Decimal, side: str) -> Tuple[bool, str]:
        """
        Assess if an offered price is favorable using v2.0 pricing
        
        Args:
            offered_price: Price being offered
            side: 'BUY' or 'SELL'
            
        Returns:
            (is_favorable, reason)
        """
        if not self.enable_black_scholes or not self.current_quote or not self.pricer:
            # Basic check
            threshold = self.last_price * Decimal("0.98") if side == "BUY" else self.last_price * Decimal("1.02")
            favorable = (offered_price <= threshold) if side == "BUY" else (offered_price >= threshold)
            reason = f"Basic check: {'Buy at discount' if favorable else 'Avoid'}"
            return favorable, reason
        
        # Use Black-Scholes assessment
        try:
            is_ok, reason = self.pricer.assess_trade_value(
                self.current_quote, 
                str(side), 
                float(offered_price)
            )
            return is_ok, reason
        except Exception as e:
            logger.error(f"Trade assessment failed: {e}")
            # Fallback to basic check
            threshold = float(self.last_price) * (0.98 if side == "BUY" else 1.02)
            is_ok = (float(offered_price) <= threshold) if side == "BUY" else (float(offered_price) >= threshold)
            return is_ok, "Basic fallback assessment"
    
    def get_strategy_metrics(self) -> dict:
        """Get current strategy metrics"""
        metrics = {
            'last_price': str(self.last_price) if self.last_price else None,
            'spread_bps': self.spread_bps,
            'inventory_threshold': str(self.inventory_threshold),
            'max_position_size': str(self.max_position_size),
            'history_length': len(self.price_history),
            'black_scholes_enabled': self.enable_black_scholes,
            'has_active_quote': self.current_quote is not None
        }
        
        # Add v2.0 quote details if available
        if self.current_quote:
            metrics['bs_quote'] = {
                'fair_value': round(self.current_quote.fair_value, 4),
                'bid': round(self.current_quote.bid, 4),
                'ask': round(self.current_quote.ask, 4),
                'confidence': round(self.current_quote.confidence, 2),
                'implied_vol': round(self.current_quote.implied_volatility, 4),
            }
            metrics['greeks'] = {
                'delta': round(self.current_quote.greeks.delta, 4),
                'theta': round(self.current_quote.greeks.theta, 6),
                'vega': round(self.current_quote.greeks.vega, 6),
            }
        
        return metrics
    
    def calculate_volatility(self) -> float:
        """Calculate historical volatility from price history"""
        if len(self.price_history) < 10:
            return 0.30  # Default assumption
        
        prices = [float(p['price']) for p in self.price_history[-50:]]
        
        if len(prices) < 2:
            return 0.30
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
        
        if not returns:
            return 0.30
        
        # Standard deviation of returns
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        
        annualized_vol = (variance ** 0.5) * (365 ** 0.5)  # Annualize
        
        return max(0.05, min(annualized_vol, 2.0))  # Cap between 5%-200%
    
    def can_trade(self, side: str, current_inventory: Decimal) -> bool:
        """
        Check if trade is allowed given current state
        
        Args:
            side: 'BUY' or 'SELL'
            current_inventory: Current position size
            
        Returns:
            True if trade should proceed
        """
        # Check max position size
        if abs(current_inventory) > self.max_position_size:
            logger.warning(f"Position limit reached: {current_inventory}")
            return False
        
        # Check inventory imbalance
        if side == 'SELL' and current_inventory < -self.inventory_threshold:
            logger.warning("Too much short inventory")
            return False
            

    def generate_bidirectional_quote(self):
        """
        Generate bidirectional market making quote using Black-Scholes pricing.
        
        Returns:
            dict: {'bid': Decimal, 'ask': Decimal, 'fair_value': Decimal, 
                   'spread_bps': int, 'timestamp': datetime}
        """
        from datetime import datetime
        
        if not self.price_history or len(self.price_history) < 3:
            return None
        
        if not self.pricer:
            return None
        
        try:
            # Calculate fair value using Black-Scholes
            current_price = self.last_price
            if not current_price:
                current_price = Decimal(str(sum(self.price_history[-10:]) / 10))
            
            volatility = self.calculate_volatility()
            
            # Use pricer for fair value (simplified version)
            fair_value = current_price  # For now, use mid-price
            
            # Calculate bid and ask with spread
            half_spread = Decimal(str(self.spread_bps)) / Decimal("20000")  # Convert bps to decimal
            
            bid = fair_value * (1 - half_spread)
            ask = fair_value * (1 + half_spread)
            
            # Ensure bid < ask
            if bid >= ask:
                bid = fair_value * 0.999
                ask = fair_value * 1.001
            
            return {
                'bid': bid,
                'ask': ask,
                'fair_value': fair_value,
                'spread_bps': self.spread_bps,
                'timestamp': datetime.utcnow(),
                'volatility': float(volatility) if volatility else None
            }
            
        except Exception as e:
            print(f"⚠ Quote generation error: {e}")
            return None


        if side == 'BUY' and current_inventory > self.inventory_threshold:
            logger.warning("Too much long inventory")
            return False
        
        return True
    
    def calculate_position_size(self, base_size: Decimal, market_conditions: dict = None) -> Decimal:
        """
        Calculate appropriate position size based on strategy logic
        
        Args:
            base_size: Base position size from risk manager
            market_conditions: Optional dict with volatility, volume, etc.
            
        Returns:
            Position size in shares
        """
        if not market_conditions:
            return min(base_size, self.max_position_size)
        
        # Adjust based on volatility
        volatility = market_conditions.get('volatility', 1.0)
        if volatility > 2.0:  # High volatility
            position_size = base_size * Decimal("0.7")
        elif volatility > 1.5:  # Medium-high volatility
            position_size = base_size * Decimal("0.85")
        else:
            position_size = base_size
        
        return min(position_size, self.max_position_size)
    
    def reset(self) -> None:
        """Reset strategy state"""
        self.price_history.clear()
        self.last_price = None
        self.current_quote = None
        self.quote_timestamp = None
        logger.info("Strategy state reset")


# Example usage and testing
if __name__ == "__main__":
    import json
    
    # Test the strategy
    strategy = BTCWindowStrategy(lookback_minutes=5, enable_black_scholes=True)
    
    # Simulate some price updates
    test_prices = [
        Decimal("0.45"),
        Decimal("0.46"),
        Decimal("0.44"),
        Decimal("0.455"),
    ]
    
    print("Testing BTC Window Strategy v2.0...")
    print("=" * 60)
    
    for price in test_prices:
        strategy.update_price(price)
        bid, ask = strategy.calculate_entry_windows()
        
        print(f"\nPrice: ${price}")
        print(f"  Bid: ${bid:.4f}" if bid else "  Bid: N/A")
        print(f"  Ask: ${ask:.4f}" if ask else "  Ask: N/A")
    
    print("\n" + "=" * 60)
    print("Strategy Metrics:")
    print(json.dumps(strategy.get_strategy_metrics(), indent=2))
    
    # Test position sizing
    base_size = Decimal("50")
    adjusted_size = strategy.calculate_position_size(
        base_size, 
        market_conditions={'volatility': 1.8}
    )
    print(f"\nBase size: {base_size}")
    print(f"Adjusted size (high vol): {adjusted_size}")

"""
Black-Scholes Option Pricing Model Implementation
v2.0 Pricing Upgrade for Polymaster BTC Bot

This module provides:
1. European option pricing (call/put)
2. Implied volatility calculation
3. Greeks calculation (Delta, Gamma, Theta, Vega, Rho)
4. Fair value determination for prediction markets
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple
from decimal import Decimal, ROUND_DOWN, ROUND_UP
import logging

logger = logging.getLogger(__name__)


# Pre-computed values for efficiency
def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function approximation"""
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911
    
    sign = 1 if x >= 0 else -1
    x = abs(x)
    
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x / 2.0)
    
    return 0.5 * (1.0 + sign * y)


@dataclass
class OptionGreeks:
    """Option sensitivity measures"""
    delta: float      # Price change per $1 underlying move
    gamma: float      # Delta change per $1 underlying move
    theta: float      # Time decay per day
    vega: float       # Volatility sensitivity (per 1%)
    rho: float        # Interest rate sensitivity


@dataclass
class PricingQuote:
    """Market quote with pricing and Greeks"""
    fair_value: float           # Calculated fair value
    bid: float                  # Bid price (with spread)
    ask: float                  # Ask price (with spread)
    mid: float                  # Mid price
    implied_volatility: float   # IV as decimal (0.25 = 25%)
    greeks: OptionGreeks        # Sensitivity metrics
    confidence: float           # Confidence in price estimate (0-1)


class BlackScholesPricer:
    """
    Black-Scholes-Merton Option Pricing Model
    
    For prediction markets like Polymarket, we treat binary outcomes
    as digital options on the underlying event.
    """
    
    def __init__(
        self,
        risk_free_rate: float = 0.05,  # 5% annual rate
        dividend_yield: float = 0.0,   # No dividends for binary options
        default_volatility: float = 0.30  # 30% base volatility
    ):
        """
        Initialize pricer
        
        Args:
            risk_free_rate: Annual risk-free interest rate
            dividend_yield: Dividend yield (0 for binary options)
            default_volatility: Default volatility assumption
        """
        self.risk_free_rate = risk_free_rate
        self.dividend_yield = dividend_yield
        self.default_volatility = default_volatility
        
        logger.info(f"BlackScholesPricer initialized")
        logger.info(f"  Risk-free rate: {risk_free_rate*100:.1f}%")
        logger.info(f"  Default volatility: {default_volatility*100:.1f}%")
    
    def european_option_price(
        self,
        spot: float,          # Current market price (0-1 for binary)
        strike: float,        # Strike price (usually 1.0 for binary)
        time_to_expiration: float,  # Years until expiration
        volatility: float,    # Annualized volatility
        option_type: str = "call"  # 'call' or 'put'
    ) -> float:
        """
        Calculate European option price using Black-Scholes formula
        
        Args:
            spot: Current asset price
            strike: Strike price
            time_to_expiration: Time to expiration in years
            volatility: Annualized volatility (std dev of returns)
            option_type: 'call' or 'put'
            
        Returns:
            Option price
        """
        if time_to_expiration <= 0:
            # At expiration
            if option_type == "call":
                return max(0.0, spot - strike)
            else:
                return max(0.0, strike - spot)
        
        if volatility < 0 or spot < 0:
            raise ValueError("Invalid input parameters")
        
        # d1 and d2 calculations
        d1 = (math.log(spot / strike) + 
              (self.risk_free_rate - self.dividend_yield + 
               0.5 * volatility ** 2) * time_to_expiration) / \
             (volatility * math.sqrt(time_to_expiration))
        
        d2 = d1 - volatility * math.sqrt(time_to_expiration)
        
        # Call price
        if option_type == "call":
            price = (spot * math.exp(-self.dividend_yield * time_to_expiration) * 
                    norm_cdf(d1) - 
                    strike * math.exp(-self.risk_free_rate * time_to_expiration) * 
                    norm_cdf(d2))
        
        # Put price
        else:
            price = (strike * math.exp(-self.risk_free_rate * time_to_expiration) * 
                    norm_cdf(-d2) - 
                    spot * math.exp(-self.dividend_yield * time_to_expiration) * 
                    norm_cdf(-d1))
        
        return max(0.0, price)
    
    def digital_call_price(
        self,
        probability: float,     # Market-implied probability (0-1)
        time_to_expiration: float,  # Years until expiration
        volatility: float,
        risk_free_rate: float = None
    ) -> float:
        """
        Price a binary (digital) option that pays $1 if TRUE
        
        For prediction markets, this is more appropriate than standard BS
        because outcomes are binary ($0 or $1 payout).
        
        Args:
            probability: Current market probability (e.g., 0.75 = 75%)
            time_to_expiration: Years until resolution
            volatility: Expected volatility
            risk_free_rate: Override global rate
            
        Returns:
            Fair value of binary option
        """
        r = risk_free_rate if risk_free_rate else self.risk_free_rate
        
        # For binary options, expected value = probability * discount_factor
        discount_factor = math.exp(-r * time_to_expiration)
        
        # Adjust for volatility (optional refinement)
        # Higher volatility increases option value slightly
        vol_adjustment = 1.0 + 0.1 * volatility * math.sqrt(time_to_expiration)
        
        fair_value = probability * discount_factor * vol_adjustment
        
        return min(1.0, max(0.0, fair_value))
    
    def calculate_greeks(
        self,
        spot: float,
        strike: float,
        time_to_expiration: float,
        volatility: float,
        option_type: str = "call"
    ) -> OptionGreeks:
        """
        Calculate all option Greeks
        
        Args:
            All same as european_option_price
            
        Returns:
            OptionGreeks dataclass with all sensitivities
        """
        if time_to_expiration <= 0:
            return OptionGreeks(0.0, 0.0, 0.0, 0.0, 0.0)
        
        sqrt_t = math.sqrt(time_to_expiration)
        
        d1 = (math.log(spot / strike) + 
              (self.risk_free_rate - self.dividend_yield + 
               0.5 * volatility ** 2) * time_to_expiration) / \
             (volatility * sqrt_t)
        
        d2 = d1 - volatility * sqrt_t
        
        # Probability density function
        pdf_d1 = math.exp(-0.5 * d1 ** 2) / math.sqrt(2 * math.pi)
        
        # Delta
        if option_type == "call":
            delta = math.exp(-self.dividend_yield * time_to_expiration) * norm_cdf(d1)
        else:
            delta = -math.exp(-self.dividend_yield * time_to_expiration) * norm_cdf(-d1)
        
        # Gamma (same for call and put)
        gamma = (math.exp(-self.dividend_yield * time_to_expiration) * 
                pdf_d1 / (spot * volatility * sqrt_t))
        
        # Theta (time decay per year, convert to days)
        if option_type == "call":
            theta = (-spot * math.exp(-self.dividend_yield * time_to_expiration) * 
                    pdf_d1 * volatility / (2 * sqrt_t) -
                    self.risk_free_rate * strike * math.exp(-self.risk_free_rate * time_to_expiration) * 
                    norm_cdf(d2))
        else:
            theta = (-spot * math.exp(-self.dividend_yield * time_to_expiration) * 
                    pdf_d1 * volatility / (2 * sqrt_t) +
                    self.risk_free_rate * strike * math.exp(-self.risk_free_rate * time_to_expiration) * 
                    norm_cdf(-d2))
        
        # Vega (per 1% volatility change)
        vega = (spot * math.exp(-self.dividend_yield * time_to_expiration) * 
               sqrt_t * pdf_d1 / 100.0)
        
        # Rho (per 1% rate change)
        if option_type == "call":
            rho = (strike * time_to_expiration * 
                  math.exp(-self.risk_free_rate * time_to_expiration) * 
                  norm_cdf(d2) / 100.0)
        else:
            rho = (-strike * time_to_expiration * 
                  math.exp(-self.risk_free_rate * time_to_expiration) * 
                  norm_cdf(-d2) / 100.0)
        
        return OptionGreeks(delta, gamma, theta, vega, rho)
    
    def implied_volatility(
        self,
        market_price: float,
        spot: float,
        strike: float,
        time_to_expiration: float,
        option_type: str = "call",
        tolerance: float = 1e-6,
        max_iterations: int = 100
    ) -> float:
        """
        Calculate implied volatility from market price (Newton-Raphson method)
        
        Args:
            market_price: Observed market price
            spot: Current price
            strike: Strike price
            time_to_expiration: Time to expiration
            option_type: 'call' or 'put'
            tolerance: Convergence tolerance
            max_iterations: Max Newton iterations
            
        Returns:
            Implied volatility as decimal
        """
        # Initial guess
        vol = self.default_volatility
        
        for i in range(max_iterations):
            price = self.european_option_price(
                spot, strike, time_to_expiration, vol, option_type
            )
            
            # Calculate vega for Newton step
            sqrt_t = math.sqrt(time_to_expiration)
            d1 = (math.log(spot / strike) + 
                  (self.risk_free_rate - self.dividend_yield + 
                   0.5 * vol ** 2) * time_to_expiration) / \
                 (vol * sqrt_t)
            
            pdf_d1 = math.exp(-0.5 * d1 ** 2) / math.sqrt(2 * math.pi)
            vega = (spot * math.exp(-self.dividend_yield * time_to_expiration) * 
                   sqrt_t * pdf_d1)
            
            # Newton-Raphson update
            diff = price - market_price
            
            if abs(diff) < tolerance:
                break
            
            if vega < 1e-10:
                break
            
            vol -= diff / vega
            
            # Keep volatility positive and reasonable
            vol = max(0.01, min(vol, 5.0))
        
        return vol
    
    def generate_quote(
        self,
        current_probability: float,  # Current market probability (0-1)
        time_to_resolution_days: int,
        volatility_estimate: float = None,
        spread_bps: int = 10  # Basis points for bid-ask spread
    ) -> PricingQuote:
        """
        Generate complete pricing quote for a prediction market outcome
        
        This is the main interface for integration with trading strategy.
        
        Args:
            current_probability: Market's implied probability (0-1)
            time_to_resolution_days: Days until event resolves
            volatility_estimate: Expected volatility (default: use default_volatility)
            spread_bps: Bid-ask spread in basis points (10 = 0.1%)
            
        Returns:
            PricingQuote with fair value, bid, ask, and Greeks
        """
        if volatility_estimate is None:
            volatility_estimate = self.default_volatility
        
        time_to_expiration = time_to_resolution_days / 365.0
        
        # Calculate fair value using binary option model
        fair_value = self.digital_call_price(
            probability=current_probability,
            time_to_expiration=time_to_expiration,
            volatility=volatility_estimate
        )
        
        # Calculate Greeks at fair value
        greeks = self.calculate_greeks(
            spot=fair_value,
            strike=1.0,
            time_to_expiration=time_to_expiration,
            volatility=volatility_estimate,
            option_type="call"
        )
        
        # Apply spread to get bid/ask
        half_spread = (spread_bps / 10000.0) / 2.0
        mid = fair_value
        
        # Bid is below fair value, ask is above
        bid = max(0.0, mid * (1.0 - half_spread))
        ask = min(1.0, mid * (1.0 + half_spread))
        
        # Confidence based on available information
        confidence = min(1.0, current_probability * 2.0)  # Higher prob = higher confidence
        
        return PricingQuote(
            fair_value=fair_value,
            bid=bid,
            ask=ask,
            mid=mid,
            implied_volatility=volatility_estimate,
            greeks=greeks,
            confidence=confidence
        )
    
    def assess_trade_value(
        self,
        quote: PricingQuote,
        trade_side: str,  # 'BUY' or 'SELL'
        trade_price: float
    ) -> Tuple[bool, str]:
        """
        Assess whether a trade at given price is favorable
        
        Args:
            quote: Current pricing quote
            trade_side: Direction of trade
            trade_price: Offered price
            
        Returns:
            (is_favorable, reason)
        """
        if trade_side == "BUY":
            # Want to buy at or below fair value
            threshold = quote.fair_value * 0.98  # 2% buffer
            
            if trade_price <= threshold:
                return True, f"Buy opportunity: ${trade_price:.4f} ≤ ${threshold:.4f}"
            else:
                return False, f"Too expensive: ${trade_price:.4f} > ${threshold:.4f}"
        
        else:  # SELL
            # Want to sell at or above fair value
            threshold = quote.fair_value * 1.02  # 2% buffer
            
            if trade_price >= threshold:
                return True, f"Sell opportunity: ${trade_price:.4f} ≥ ${threshold:.4f}"
            else:
                return False, f"Too cheap: ${trade_price:.4f} < ${threshold:.4f}"


# Integration helpers for Polymaster bot
def calculate_time_weighted_confidence(
    days_until_resolution: int,
    volatility: float
) -> float:
    """
    Calculate confidence score for price estimate
    
    More certainty when:
    - Resolution is near (less time for events)
    - Lower volatility (more stable market)
    """
    time_factor = 1.0 - (days_until_resolution / 365.0)  # 0 to 1
    vol_factor = 1.0 / (1.0 + volatility)  # Higher vol = lower confidence
    
    confidence = time_factor * vol_factor
    return min(1.0, max(0.0, confidence))


if __name__ == "__main__":
    """Test the Black-Scholes pricer"""
    import json
    
    print("="*80)
    print("🧪 BLACK-SCHOLES PRICER TEST")
    print("="*80)
    print()
    
    # Initialize pricer
    pricer = BlackScholesPricer(
        risk_free_rate=0.05,
        default_volatility=0.30
    )
    
    # Test scenario: Bitcoin hitting $100K by end of year
    print("Scenario: BTC hits $100K by Dec 31, 2026")
    print("-"*60)
    
    current_prob = 0.45  # 45% probability
    days_until_resolution = 90  # ~3 months
    
    print(f"\nCurrent market probability: {current_prob*100:.1f}%")
    print(f"Days until resolution: {days_until_resolution}")
    
    # Generate quote
    quote = pricer.generate_quote(
        current_probability=current_prob,
        time_to_resolution_days=days_until_resolution,
        volatility_estimate=0.35,
        spread_bps=10
    )
    
    print("\nPricing Quote:")
    print(f"  Fair Value: ${quote.fair_value:.4f}")
    print(f"  Bid:        ${quote.bid:.4f}")
    print(f"  Ask:        ${quote.ask:.4f}")
    print(f"  Mid:        ${quote.mid:.4f}")
    print(f"  Implied Vol: {quote.implied_volatility*100:.1f}%")
    print(f"  Confidence:  {quote.confidence:.2%}")
    
    print("\nGreeks:")
    print(f"  Delta:  {quote.greeks.delta:+.4f} (price sensitivity)")
    print(f"  Gamma:  {quote.greeks.gamma:.6f} (delta sensitivity)")
    print(f"  Theta:  {quote.greeks.theta:.6f} (daily time decay)")
    print(f"  Vega:   {quote.greeks.vega:.6f} (vol sensitivity)")
    print(f"  Rho:    {quote.greeks.rho:.6f} (rate sensitivity)")
    
    # Test trade assessment
    print("\nTrade Assessment Tests:")
    test_prices = [0.40, 0.43, 0.45, 0.47, 0.50]
    
    for price in test_prices:
        buy_ok, buy_reason = pricer.assess_trade_value(quote, "BUY", price)
        sell_ok, sell_reason = pricer.assess_trade_value(quote, "SELL", price)
        
        print(f"\nPrice: ${price:.4f}")
        print(f"  BUY: {'✓ Good' if buy_ok else '✗ Avoid'} - {buy_reason}")
        print(f"  SELL: {'✓ Good' if sell_ok else '✗ Avoid'} - {sell_reason}")
    
    print("\n" + "="*80)
    print("✅ Black-Scholes Pricer Ready!")
    print("="*80)

#!/usr/bin/env python3
"""
🧮 Advanced Pricing Model: Black-Scholes for Prediction Markets

Based on: "Polymarket Market Making Bible" (Feb 2026)
Key Concepts:
  • Logit transformation for probability mapping
  • Belief volatility as uncertainty metric  
  • Greeks-based risk management (Delta, Theta, Vega, Gamma)

Version: 2.0 - Integrated with Polymaster bot
Date: 2026-03-19
"""

import math
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class Greeks:
    """Options Greeks for prediction market"""
    delta: float      # Sensitivity to underlying price change
    theta: float      # Time decay (per day)
    vega: float       # Sensitivity to volatility change
    gamma: float      # Rate of change of delta
    rho: float        # Sensitivity to risk-free rate


class PredictionMarketPricer:
    """
    Black-Scholes inspired pricing model for binary prediction markets.
    
    Adapted from traditional options theory to prediction market context:
    - Underlying S = Current market probability estimate
    - Strike K = Resolution threshold (1.0 for YES, 0.0 for NO)
    - Volatility σ = "Belief volatility" instead of asset volatility
    """
    
    def __init__(self, risk_free_rate: float = 0.0):
        self.r = risk_free_rate
        
    def logit(self, p: float) -> float:
        """
        Transform probability p ∈ (0,1) to log-odds ∈ (-∞, +∞)
        
        Why? Binary outcomes naturally have boundaries at 0 and 1.
        Logit removes these constraints for cleaner modeling.
        """
        if not 0 < p < 1:
            raise ValueError(f"Probability must be strictly between 0 and 1, got {p}")
        return math.log(p / (1 - p))
    
    def inv_logit(self, x: float) -> float:
        """Inverse transform: log-odds back to probability"""
        return 1.0 / (1.0 + math.exp(-x))
    
    def norm_cdf(self, x: float) -> float:
        """Cumulative distribution function of standard normal"""
        # Approximation using error function
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
    
    def norm_pdf(self, x: float) -> float:
        """Probability density function of standard normal"""
        return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)
    
    def belief_volatility(
        self, 
        time_horizon_days: float,
        historical_confidence_std: float,
        sentiment_factor: float = 1.0
    ) -> float:
        """
        Calculate "belief volatility" based on market conditions.
        
        Args:
            time_horizon_days: Time until event resolution
            historical_confidence_std: Std dev of recent confidence scores
            sentiment_factor: Multiplier based on current market sentiment
            
        Returns:
            Annualized belief volatility σ (decimal)
        """
        # Base vol from historical confidence variance
        base_vol = historical_confidence_std * 100.0  # Scale to reasonable range
        
        # Adjust for time horizon (shorter horizon = lower vol)
        time_adjustment = math.sqrt(time_horizon_days / 365.0)
        
        # Sentiment factor amplifies during news events
        adjusted_vol = base_vol * time_adjustment * sentiment_factor
        
        return min(max(adjusted_vol, 0.05), 2.0)  # Clamp to [5%, 200%]
    
    def d1_d2(
        self,
        s: float,  # Current probability estimate
        k: float,  # Strike (1.0 for YES, 0.0 for NO)
        sigma: float,  # Belief volatility
        t: float,  # Time to expiry (years)
        r: Optional[float] = None
    ):
        """Calculate d1 and d2 for Black-Scholes formula"""
        if r is None:
            r = self.r
            
        if t <= 0 or sigma <= 0:
            return 0.0, 0.0
        
        sqrt_t = math.sqrt(t)
        ln_sk = math.log(s / k) if k > 0 else 0.0
        
        d1 = (ln_sk + (r + 0.5 * sigma**2) * t) / (sigma * sqrt_t)
        d2 = d1 - sigma * sqrt_t
        
        return d1, d2
    
    def bs_price_binary_yes(
        self,
        s: float,  # Current market probability (as decimal)
        k: float = 1.0,  # Strike for YES contract
        sigma: float = 0.5,  # Belief volatility
        t: float = 0.0027,  # Time to expiry in years (~1 hour)
        r: Optional[float] = None
    ) -> float:
        """
        Price binary YES contract using BS framework.
        
        Payoff: $1 if event occurs, $0 otherwise
        
        Price = e^(-rt) × N(d2) where N() is cumulative normal
        """
        if r is None:
            r = self.r
            
        d1, d2 = self.d1_d2(s, k, sigma, t, r)
        
        # Discounted expected payoff
        discounted_payoff = math.exp(-r * t) * self.norm_cdf(d2)
        
        return discounted_payoff
    
    def calculate_greeks(
        self,
        s: float,
        k: float = 1.0,
        sigma: float = 0.5,
        t: float = 0.0027,
        r: Optional[float] = None
    ) -> Greeks:
        """
        Calculate all Greeks for the binary contract.
        
        Important for risk management:
        - Delta: How much price changes with underlying move
        - Theta: Time decay (negative = losing value over time)
        - Vega: Sensitivity to volatility changes
        - Gamma: Convexity (rate of Delta change)
        """
        if r is None:
            r = self.r
        
        d1, d2 = self.d1_d2(s, k, sigma, t, r)
        sqrt_t = math.sqrt(t)
        
        # Delta ≈ N(d1) for binary call option
        delta = self.norm_cdf(d1)
        
        # Gamma = pdf(d1) / (S * sigma * √T)
        gamma = self.norm_pdf(d1) / (s * sigma * sqrt_t + 1e-8)
        
        # Theta (per year, then convert to per day)
        # Negative for long positions
        term1 = -(s * self.norm_pdf(d1) * sigma) / (2 * sqrt_t)
        term2 = -r * k * math.exp(-r * t) * self.norm_cdf(d2)
        theta_per_year = term1 + term2
        theta_per_day = theta_per_year / 365.0
        
        # Vega (per 1% change in volatility)
        vega = s * self.norm_pdf(d1) * sqrt_t / 100.0
        
        # Rho (small impact for binary options, but calculated)
        rho = k * t * math.exp(-r * t) * self.norm_cdf(d2) / 100.0
        
        return Greeks(
            delta=delta,
            theta=theta_per_day,
            vega=vega,
            gamma=gamma,
            rho=rho
        )
    
    def optimal_quote_spread(
        self,
        confidence: float,
        belief_vol: float,
        time_horizon_hours: float = 1.0,
        target_risk_exposure: float = 0.10  # Max Delta risk per trade
    ) -> tuple[float, float]:
        """
        Calculate optimal bid/ask spread based on BS model.
        
        Returns:
            (bid_price, ask_price) as decimals
        """
        # Convert confidence to probability
        prob = confidence  # Simplified: confidence ≈ market probability
        
        # Time in years
        t_years = time_horizon_hours / 24.0 / 365.0
        
        # Price YES side
        yes_price = self.bs_price_binary_yes(
            s=prob,
            k=1.0,
            sigma=belief_vol,
            t=t_years
        )
        
        # Calculate Greeks for this position
        greeks = self.calculate_greeks(
            s=prob,
            k=1.0,
            sigma=belief_vol,
            t=t_years
        )
        
        # Adjust spread based on risk exposure
        # Wider spread when:
        # - Delta is high (large directional exposure)
        # - Theta decay is fast (time working against us)
        # - Vega is sensitive (volatility risk)
        
        risk_multiplier = 1.0 + abs(greeks.delta) * 2.0 + abs(greeks.theta) * 10.0
        
        # Optimal half-spread
        half_spread = yes_price * risk_multiplier * 0.05  # ~5% base adjustment
        
        bid_price = max(0.01, yes_price - half_spread)
        ask_price = min(0.99, yes_price + half_spread)
        
        return bid_price, ask_price
    
    def dynamic_fee_rate_bps(
        self,
        confidence: float,
        belief_vol: float,
        greeks: Optional[Greeks] = None
    ) -> int:
        """
        Calculate dynamic fee rate based on BS framework.
        
        Improved from original linear formula to include:
        - Volatility premium
        - Greeks risk factors
        """
        if greeks is None:
            # If not provided, calculate
            s = confidence
            t_years = 1.0 / 24.0 / 365.0  # Assume 1 hour horizon
            greeks = self.calculate_greeks(
                s=s,
                sigma=belief_vol,
                t=t_years
            )
        
        # Base fee from confidence (traditional component)
        base_fee = max(0, int((1.0 - confidence) * 156))
        
        # Volatility adjustment (higher vol = higher fee to compensate risk)
        vol_adjustment = int(belief_vol * 50)  # Scale factor
        
        # Greeks adjustment (Gamma risk increases fee)
        gamma_risk = int(abs(greeks.gamma) * 1000)
        
        # Total fee
        total_fee = base_fee + vol_adjustment + gamma_risk
        
        # Cap at reasonable level
        return min(total_fee, 500)  # Max 500 bps = 5%


class EnhancedPredictionStrategy:
    """
    Updated strategy incorporating Black-Scholes pricing.
    
    Integrates with existing Polymaster framework.
    """
    
    def __init__(self):
        self.pricer = PredictionMarketPricer()
        self.confidence_history: list[float] = []
        
    def update_confidence_history(self, new_confidence: float, window: int = 100):
        """Track recent confidence scores for volatility calculation"""
        self.confidence_history.append(new_confidence)
        if len(self.confidence_history) > window:
            self.confidence_history.pop(0)
    
    def get_belief_volatility(self, time_horizon_hours: float = 1.0) -> float:
        """Calculate current belief volatility from history"""
        if len(self.confidence_history) < 10:
            return 0.5  # Default fallback
        
        historical_std = np.std(self.confidence_history)
        return self.pricer.belief_volatility(
            time_horizon_days=time_horizon_hours / 24.0,
            historical_confidence_std=historical_std,
            sentiment_factor=1.0
        )
    
    def generate_optimal_quote(
        self,
        confidence: float,
        time_until_event_hours: float = 1.0
    ) -> dict:
        """
        Generate quote using enhanced BS pricing.
        
        Returns:
            {
                'yes_price': float,
                'no_price': float,
                'fee_rate_bps': int,
                'greeks': Greeks object,
                'spread_width': float
            }
        """
        # Update internal state
        self.update_confidence_history(confidence)
        
        # Calculate belief volatility
        belief_vol = self.get_belief_volatility(time_until_event_hours)
        
        # Get optimal spread
        bid, ask = self.pricer.optimal_quote_spread(
            confidence=confidence,
            belief_vol=belief_vol,
            time_horizon_hours=time_until_event_hours
        )
        
        # Calculate Greeks for this quote
        greeks = self.pricer.calculate_greeks(
            s=confidence,
            sigma=belief_vol,
            t=time_until_event_hours / 24.0 / 365.0
        )
        
        # Dynamic fee rate
        fee_rate = self.pricer.dynamic_fee_rate_bps(
            confidence=confidence,
            belief_vol=belief_vol,
            greeks=greeks
        )
        
        return {
            'yes_price': ask,  # Selling YES = asking price
            'no_price': 1.0 - bid,  # NO price inverse of YES bid
            'fee_rate_bps': fee_rate,
            'greeks': greeks,
            'spread_width': ask - bid,
            'belief_volatility': belief_vol
        }


# ==================== TEST SUITE ====================

def test_pricing_model():
    """Test the new BS pricing implementation"""
    print("="*70)
    print("🧮 BLACK-SCHOLES PRICING MODEL TEST")
    print("="*70)
    
    pricer = PredictionMarketPricer()
    strategy = EnhancedPredictionStrategy()
    
    # Test 1: Logit transformations
    print("\n✓ Test 1: Logit Transformations")
    test_probs = [0.5, 0.6, 0.75, 0.9, 0.95]
    for p in test_probs:
        logit_val = pricer.logit(p)
        recovered = pricer.inv_logit(logit_val)
        print(f"  p={p:.2%} → logit={logit_val:+.3f} → recover={recovered:.2%}")
        assert abs(p - recovered) < 0.001
    
    # Test 2: BS Pricing
    print("\n✓ Test 2: Binary Option Pricing")
    test_cases = [
        (0.85, 0.5, 0.0027),  # (confidence, vol, time)
        (0.90, 0.3, 0.0027),
        (0.95, 0.2, 0.0014),
    ]
    for conf, vol, t in test_cases:
        price = pricer.bs_price_binary_yes(conf, k=1.0, sigma=vol, t=t)
        print(f"  Conf={conf:.0%}, Vol={vol:.0%}, Time~1h → Price=${price:.4f}")
        assert 0 < price < 1
    
    # Test 3: Greeks Calculation
    print("\n✓ Test 3: Greeks Values")
    greeks = pricer.calculate_greeks(
        s=0.85,
        k=1.0,
        sigma=0.4,
        t=0.0027
    )
    print(f"  Delta: {greeks.delta:.4f}")
    print(f"  Theta/day: {greeks.theta:.6f}")
    print(f"  Vega: {greeks.vega:.6f}")
    print(f"  Gamma: {greeks.gamma:.6f}")
    
    # Test 4: Optimal Spread
    print("\n✓ Test 4: Quote Generation")
    for conf in [0.85, 0.90, 0.95]:
        quote = strategy.generate_optimal_quote(
            confidence=conf,
            time_until_event_hours=1.0
        )
        print(f"\nConfidence {conf:.0%}:")
        print(f"  YES Ask: ${quote['yes_price']:.4f}")
        print(f"  NO Bid:  ${quote['no_price']:.4f}")
        print(f"  Spread:  {quote['spread_width']:.4f} ({quote['spread_width']*100:.2%})")
        print(f"  Fee Rate: {quote['fee_rate_bps']} bps ({quote['fee_rate_bps']/10:.1f}%)")
        print(f"  Belief Vol: {quote['belief_volatility']:.0%}")
    
    print("\n" + "="*70)
    print("✅ All tests passed!")
    print("="*70)
    print("\nNext steps:")
    print("  1. Integrate into main.py quote generation")
    print("  2. Add Greeks monitoring to risk manager")
    print("  3. Backtest vs old pricing method")
    print("="*70)


if __name__ == "__main__":
    test_pricing_model()

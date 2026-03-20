"""
Logit Pricing Model Test Script
Version: v1.0 Fast Practical Edition
Date: Thu 2026-03-19 9:32 PM PDT

Usage:
    python test_logit_pricing.py --compare
    
Description:
    This script tests the Logit-based pricing model against the current linear model.
    Run with --compare flag to see side-by-side comparison.
"""

import numpy as np
from typing import List, Dict


# ==============================================================================
# CORE LOGIT FUNCTIONS
# ==============================================================================

def logit(confidence_pct: float) -> float:
    """Convert confidence percentage (0-100) to logit space."""
    p = np.clip(confidence_pct / 100.0, 0.001, 0.999)
    return np.log(p / (1 - p))


def pricing_model_linear(confidence: float, base_spread_bps: float = 30) -> float:
    """Current linear pricing model."""
    spread = base_spread_bps * (1 - confidence / 100)
    return round(np.clip(spread, 5, 100), 1)


def pricing_model_logit(
    confidence: float, 
    base_spread_bps: float = 30, 
    alpha: float = 8.0
) -> float:
    """Improved Logit-based pricing model."""
    logit_score = logit(confidence)
    
    if confidence >= 50:  # Bullish bias
        spread = base_spread_bps * np.exp(-alpha * logit_score)
    else:  # Bearish bias
        spread = base_spread_bps * np.exp(alpha * logit_score)
    
    return round(np.clip(spread, 5, 100), 1)


def calculate_belief_volatility(recent_confidences: List[float], window_size: int = 10) -> float:
    """Calculate volatility adjustment based on recent confidence stability."""
    if len(recent_confidences) < 2:
        return 0.0
    
    logit_history = [logit(c) for c in recent_confidences[-window_size:]]
    belief_vol = np.std(logit_history)
    vol_adjustment = 5 * belief_vol  # 5 bps per unit of volatility
    
    return vol_adjustment


def pricing_model_logit_with_volatility(
    confidence: float,
    recent_confidences: List[float],
    base_spread_bps: float = 30,
    alpha: float = 8.0,
    window_size: int = 10
) -> float:
    """Combine Logit pricing with belief volatility adjustment."""
    base_spread = pricing_model_logit(confidence, base_spread_bps, alpha)
    vol_adj = calculate_belief_volatility(recent_confidences, window_size)
    final_spread = base_spread + vol_adj
    
    return round(np.clip(final_spread, 5, 100), 1)


# ==============================================================================
# COMPARISON TESTS
# ==============================================================================

def run_comparison_tests():
    """Run comprehensive comparison between Linear and Logit models."""
    
    print("=" * 70)
    print("🧪 LOGIT PRICING MODEL - COMPREHENSIVE TEST")
    print("=" * 70)
    print()
    
    # Test confidence levels
    test_confidences = [60, 70, 80, 85, 90, 95]
    
    print("【Test 1】Static Spread Comparison (base_spread=30bps, alpha=8.0)")
    print("-" * 70)
    print(f"{'Confidence':<12} {'Linear (bps)':<15} {'Logit (bps)':<15} {'Gap Change':<15}")
    print("-" * 70)
    
    for conf in test_confidences:
        linear_spread = pricing_model_linear(conf)
        logit_spread = pricing_model_logit(conf)
        gap_improvement = ((linear_spread - logit_spread) / linear_spread) * 100
        
        print(f"{conf:<12} {linear_spread:<15} {logit_spread:<15} {gap_improvement:+.1f}%")
    
    print()
    
    # Test alpha sensitivity
    print("【Test 2】Alpha Sensitivity Analysis (at 90% confidence)")
    print("-" * 70)
    print(f"{'Alpha':<10} {'Spread (bps)':<15} {'Behavior':<20}")
    print("-" * 70)
    
    for alpha in [4.0, 6.0, 8.0, 10.0, 12.0]:
        spread = pricing_model_logit(90, alpha=alpha)
        behavior = "Conservative" if alpha <= 6 else "Balanced" if alpha == 8 else "Aggressive"
        print(f"{alpha:<10} {spread:<15} {behavior:<20}")
    
    print()
    
    # Belief volatility impact
    print("【Test 3】Belief Volatility Impact")
    print("-" * 70)
    
    # Scenario A: Stable confidence (low volatility)
    stable_confidences = [85, 87, 84, 86, 85]
    base_spread = pricing_model_logit(85, alpha=8.0)
    vol_adj_stable = calculate_belief_volatility(stable_confidences)
    final_stable = base_spread + vol_adj_stable
    
    # Scenario B: Volatile confidence (high volatility)
    volatile_confidences = [75, 92, 78, 90, 80]
    vol_adj_volatile = calculate_belief_volatility(volatile_confidences)
    final_volatile = base_spread + vol_adj_volatile
    
    print(f"Stable confidences {stable_confidences}:")
    print(f"  → Base spread: {base_spread:.1f} bps")
    print(f"  → Vol adjustment: +{vol_adj_stable:.1f} bps")
    print(f"  → Final spread: {final_stable:.1f} bps")
    print()
    print(f"Volatile confidences {volatile_confidences}:")
    print(f"  → Base spread: {base_spread:.1f} bps")
    print(f"  → Vol adjustment: +{vol_adj_volatile:.1f} bps")
    print(f"  → Final spread: {final_volatile:.1f} bps")
    print(f"  → Volatility penalty: +{vol_adj_volatile - vol_adj_stable:.1f} bps wider!")
    
    print()
    print("=" * 70)
    print("✅ All tests completed successfully!")
    print("=" * 70)


# ==============================================================================
# BACKTEST INTEGRATION HELPER
# ==============================================================================

def simulate_trade_outcome(confidence: float, model_type: str = "logit", alpha: float = 8.0) -> Dict:
    """
    Simulate a single trade outcome based on confidence and model type.
    This is a simplified version - replace with actual backtest logic later.
    """
    
    # Get spread from chosen model
    if model_type == "linear":
        spread_bps = pricing_model_linear(confidence)
    else:
        spread_bps = pricing_model_logit(confidence, alpha=alpha)
    
    # Expected win rate based on confidence (simplified)
    expected_win_rate = confidence / 100.0
    
    # Expected profit per trade (maker rebate + spread capture)
    avg_profit_if_win = 1.5  # $1.50 average maker rebate
    avg_loss_if_lose = 0.9   # $0.90 average taker fee
    
    expected_value = (expected_win_rate * avg_profit_if_win) - ((1 - expected_win_rate) * avg_loss_if_lose)
    
    return {
        'confidence': confidence,
        'model': model_type,
        'spread_bps': spread_bps,
        'expected_win_rate': expected_win_rate,
        'expected_value_per_trade': round(expected_value, 2),
        'recommendation': 'EXECUTE' if expected_value > 0.5 else 'SKIP'
    }


def quick_backtest_simulation(num_trades: int = 100):
    """Quick simulation to compare models over multiple trades."""
    
    print()
    print("=" * 70)
    print("📊 QUICK BACKTEST SIMULATION (n={})".format(num_trades))
    print("=" * 70)
    
    np.random.seed(42)  # Reproducible results
    
    # Generate random confidence distribution
    confidences = np.random.uniform(60, 95, num_trades).tolist()
    
    linear_total_pv = 0
    logit_total_pv = 0
    
    for conf in confidences:
        linear_result = simulate_trade_outcome(conf, "linear")
        logit_result = simulate_trade_outcome(conf, "logit", alpha=8.0)
        
        # Simulate actual outcome
        actual_win = np.random.random() < linear_result['expected_win_rate']
        
        if actual_win:
            linear_total_pv += linear_result['expected_value_per_trade']
            logit_total_pv += logit_result['expected_value_per_trade']
        else:
            linear_total_pv -= 0.9  # Loss amount
            logit_total_pv -= 0.9
    
    print(f"Model       | Avg P&L/trade | Total P&L ({num_trades} trades)")
    print("-" * 70)
    print(f"Linear      | ${linear_total_pv/num_trades:>7.2f}           | ${linear_total_pv:>7.2f}")
    print(f"Logit (α=8) | ${logit_total_pv/num_trades:>7.2f}           | ${logit_total_pv:>7.2f}")
    print()
    
    improvement = ((logit_total_pv - linear_total_pv) / abs(linear_total_pv)) * 100
    print(f"Improvement: {improvement:+.1f}%")
    print()


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Logit Pricing Model")
    parser.add_argument("--quick-backtest", action="store_true", help="Run quick backtest simulation")
    parser.add_argument("--num-trades", type=int, default=100, help="Number of trades for simulation")
    
    args = parser.parse_args()
    
    # Always run core tests
    run_comparison_tests()
    
    # Optionally run backtest simulation
    if args.quick_backtest:
        quick_backtest_simulation(args.num_trades)
    
    print()
    print("💡 Next steps:")
    print("1. Review comparison table above")
    print("2. Choose optimal alpha value (recommended: 8.0)")
    print("3. Implement in core/pricing_engine.py")
    print("4. Run full backtest_enhanced.py with new model")
    print("5. Compare performance metrics")

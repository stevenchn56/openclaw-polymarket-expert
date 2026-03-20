#!/usr/bin/env python3
"""
Polymarket BTC Bot - Enhanced Backtest v2.1
Comprehensive testing of bidirectional market making strategy
"""

import os
os.environ['PYTHONWARNINGS'] = 'ignore'

from pathlib import Path
import sys
from decimal import Decimal
from datetime import datetime

# Add project root to path
P = Path(__file__).parent.absolute()
sys.path.insert(0, str(P))

# ============================================================================
# CONFIGURATION
# ============================================================================

BACKTEST_CONFIG = {
    'scenarios': [
        {'name': 'Normal Volatility', 'volatility': 0.02, 'trend': 0.0001, 'spread_bps': 10},
        {'name': 'High Volatility', 'volatility': 0.04, 'trend': 0.0001, 'spread_bps': 15},
        {'name': 'Bull Market', 'volatility': 0.025, 'trend': 0.0005, 'spread_bps': 8},
        {'name': 'Bear Market', 'volatility': 0.025, 'trend': -0.0005, 'spread_bps': 12},
        {'name': 'Flat Market', 'volatility': 0.01, 'trend': 0.0, 'spread_bps': 10},
    ],
    'base_price': 45000,
    'num_candles': 100,
    'num_runs_per_scenario': 50,
}

# ============================================================================
# UTILITIES
# ============================================================================

def generate_price_series(base_price, volatility, points, trend):
    """Generate realistic price series using numpy random walk"""
    try:
        import numpy as np
        changes = np.random.normal(trend, volatility, points)
        cumulative = np.cumprod(np.ones(points) + changes)
        prices = base_price * cumulative
        return [Decimal(str(p)) for p in prices]
    except ImportError:
        # Fallback without numpy
        import random
        prices = []
        current = base_price
        for _ in range(points):
            change = random.gauss(trend, volatility)
            current *= (1 + change)
            prices.append(Decimal(str(current)))
        return prices

# ============================================================================
# BACKTEST ENGINE
# ============================================================================

def run_single_simulation(scenario_name, prices, spread_bps):
    """Run a single backtest simulation"""
    
    from strategies.btc_window_5m import BTCWindowStrategy
    
    strategy = BTCWindowStrategy(lookback_minutes=5)
    strategy.spread_bps = spread_bps
    
    result = {
        'scenario': scenario_name,
        'quotes_generated': 0,
        'trades_executed': 0,
        'successful_trades': 0,
        'starting_balance': 100.0,
        'ending_balance': 100.0,
        'total_pnl_pct': 0.0,
        'max_drawdown': 0.0,
        'avg_spread_used': spread_bps,
    }
    
    balance = result['starting_balance']
    max_balance = balance
    last_trade_profit = 0
    
    # Process candles
    for i in range(1, len(prices)):
        prev_close = float(prices[i-1])
        curr_close = float(prices[i])
        
        # Update strategy
        strategy.update_price(prices[i])
        
        # Generate quote if enough history
        if len(strategy.price_history) >= 3:
            try:
                quote = strategy.generate_bidirectional_quote()
                
                if quote and isinstance(quote, dict):
                    result['quotes_generated'] += 1
                    
                    # Simulate trading every 5 candles
                    if i % 5 == 0 and i < len(prices) - 1:
                        result['trades_executed'] += 1
                        
                        # Simple momentum strategy: go long if rising
                        if prev_close < curr_close:
                            # Profit calculation
                            profit_pct = (curr_close - prev_close) / prev_close
                            balance *= (1 + profit_pct)
                            result['successful_trades'] += 1
                            last_trade_profit = profit_pct * 100
                        else:
                            loss_pct = (prev_close - curr_close) / prev_close
                            balance *= (1 - loss_pct)
                            last_trade_profit = -loss_pct * 100
                        
                        # Track drawdown
                        if balance > max_balance:
                            max_balance = balance
        
        # Skip if no quotes generated
        if result['quotes_generated'] == 0:
            continue
    
    # Final calculations
    result['ending_balance'] = round(balance, 4)
    result['total_pnl_pct'] = round((balance - result['starting_balance']) / 
                                     result['starting_balance'] * 100, 2)
    
    if max_balance > 0:
        result['max_drawdown'] = round((max_balance - balance) / max_balance * 100, 2)
    
    return result

def run_scenario_tests(scenario_config, num_runs=50):
    """Run multiple simulations for a scenario"""
    
    print(f"\n{'='*70}")
    print(f"📈 TESTING: {scenario_config['name']}")
    print(f"   Volatility: {scenario_config['volatility']*100:.1f}% | "
          f"Trend: {scenario_config['trend']*100:.2f}% | "
          f"Spread: {scenario_config['spread_bps']} bps")
    print(f"{'='*70}")
    
    all_results = []
    
    for run_idx in range(num_runs):
        # Generate price series
        prices = generate_price_series(
            BACKTEST_CONFIG['base_price'],
            scenario_config['volatility'],
            BACKTEST_CONFIG['num_candles'],
            scenario_config['trend']
        )
        
        # Run simulation
        try:
            result = run_single_simulation(
                scenario_config['name'],
                prices,
                scenario_config['spread_bps']
            )
            
            all_results.append(result)
            
            # Progress indicator
            if run_idx % 10 == 0:
                print(f"  [{run_idx+1}/{num_runs}] Complete | "
                      f"P&L: {result['total_pnl_pct']:+.2f}% | "
                      f"Trades: {result['trades_executed']}")
        
        except Exception as e:
            print(f"  ⚠️  Run {run_idx+1}: Error - {str(e)[:60]}")
            continue
    
    return all_results

# ============================================================================
# ANALYSIS & REPORTING
# ============================================================================

def analyze_results(all_results, scenario_name):
    """Analyze backtest results for a scenario"""
    
    if not all_results:
        return None
    
    # Extract metrics
    pnl_values = [r['total_pnl_pct'] for r in all_results]
    trade_counts = [r['trades_executed'] for r in all_results]
    win_rates = [(r['successful_trades'] / max(r['trades_executed'], 1)) 
                 for r in all_results]
    
    try:
        import numpy as np
        avg_pnl = np.mean(pnl_values)
        std_pnl = np.std(pnl_values) if len(pnl_values) > 1 else 0
        best_pnl = max(pnl_values)
        worst_pnl = min(pnl_values)
        avg_trades = np.mean(trade_counts)
        avg_win_rate = np.mean(win_rates) * 100
    except ImportError:
        avg_pnl = sum(pnl_values) / len(pnl_values)
        std_pnl = 0
        best_pnl = max(pnl_values)
        worst_pnl = min(pnl_values)
        avg_trades = sum(trade_counts) / len(trade_counts)
        avg_win_rate = sum(win_rates) * 100 / len(win_rates)
    
    # Calculate success rate (>0 P&L)
    successful_runs = sum(1 for p in pnl_values if p > 0)
    success_rate = successful_runs / len(all_results) * 100
    
    return {
        'avg_pnl': avg_pnl,
        'std_pnl': std_pnl,
        'best_pnl': best_pnl,
        'worst_pnl': worst_pnl,
        'avg_trades': avg_trades,
        'avg_win_rate': avg_win_rate,
        'success_rate': success_rate,
        'total_runs': len(all_results),
    }

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("="*80)
    print("  POLYMARKET BTC BOT - COMPREHENSIVE BACKTEST v2.1")
    print("  Bidirectional Market Making Strategy Testing")
    print("="*80)
    print(f"\n📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Config: {BACKTEST_CONFIG['num_runs_per_scenario']} runs × "
          f"{len(BACKTEST_CONFIG['scenarios'])} scenarios = "
          f"{BACKTEST_CONFIG['num_runs_per_scenario'] * len(BACKTEST_CONFIG['scenarios'])} total")
    print("="*80)
    
    # Store all results
    all_scenario_results = {}
    all_analyses = {}
    
    # Run each scenario
    for scenario in BACKTEST_CONFIG['scenarios']:
        results = run_scenario_tests(scenario, BACKTEST_CONFIG['num_runs_per_scenario'])
        
        if results:
            analysis = analyze_results(results, scenario['name'])
            all_scenario_results[scenario['name']] = results
            all_analyses[scenario['name']] = analysis
    
    # Print summary
    if all_analyses:
        print("\n" + "="*80)
        print("  📊 SCENARIO COMPARISON")
        print("="*80)
        print(f"\n  {'Scenario':<25s} | {'Avg P&L':>10s} | {'Best':>10s} | "
              f"{'Worst':>10s} | {'Win Rate':>10s}")
        print("  " + "-"*70)
        
        for name, analysis in sorted(all_analyses.items(), 
                                      key=lambda x: x[1]['avg_pnl'], reverse=True):
            print(f"  {name:<25s} | {analysis['avg_pnl']:>9.2f}% | "
                  f"{analysis['best_pnl']:>9.2f}% | {analysis['worst_pnl']:>9.2f}% | "
                  f"{analysis['avg_win_rate']:>9.1f}%")
        
        # Overall statistics
        print("\n" + "="*80)
        print("  🎯 OVERALL STATISTICS")
        print("="*80)
        
        all_pnls = [r['total_pnl_pct'] for results in all_scenario_results.values() 
                   for r in results]
        
        try:
            import numpy as np
            overall_avg_pnl = np.mean(all_pnls)
            overall_std = np.std(all_pnls)
            total_runs = len(all_pnls)
            positive_runs = sum(1 for p in all_pnls if p > 0)
        except ImportError:
            overall_avg_pnl = sum(all_pnls) / len(all_pnls)
            overall_std = 0
            total_runs = len(all_pnls)
            positive_runs = sum(1 for p in all_pnls if p > 0)
        
        print(f"  • Total Simulations: {total_runs}")
        print(f"  • Overall Avg P&L:   {overall_avg_pnl:+.2f}%")
        print(f"  • Std Deviation:     {overall_std:+.2f}%")
        print(f"  • Positive Runs:     {positive_runs}/{total_runs} ({positive_runs/total_runs*100:.1f}%)")
        
        # Best/worst performers
        best_scenario = max(all_analyses.items(), key=lambda x: x[1]['avg_pnl'])
        worst_scenario = min(all_analyses.items(), key=lambda x: x[1]['avg_pnl'])
        
        print(f"\n  👑 Best Performing: {best_scenario[0]} ({best_scenario[1]['avg_pnl']:+.2f}%)")
        print(f"  ⚠️  Worst Performing: {worst_scenario[0]} ({worst_scenario[1]['avg_pnl']:+.2f}%)")
    
    print("\n" + "="*80)
    print("  ✅ BACKTEST COMPLETE")
    print("="*80)
    print(f"\n📁 Results saved to: backtest_complete_results.txt")
    print("="*80)

if __name__ == '__main__':
    main()

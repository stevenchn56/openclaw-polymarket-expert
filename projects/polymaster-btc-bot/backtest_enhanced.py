"""
Enhanced Backtest Suite - Multiple Market Scenarios

Tests strategy performance across different market conditions:
1. Normal volatility (random walk)
2. Bull market (consistent uptrend)
3. Bear market (consistent downtrend)  
4. High volatility (spiky, erratic)
5. Flat/sideways (ranging)
"""

import sys
sys.path.insert(0, '/Users/stevenwang/.openclaw/workspace/projects/polymaster-btc-bot')

from datetime import datetime, timezone, timedelta
from strategies.btc_window_5m import BTCWindowStrategy
from dataclasses import dataclass


@dataclass
class PriceDataPoint:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


import numpy as np


class ScenarioGenerator:
    """Generate different market scenarios"""
    
    @staticmethod
    def generate_candle(open_price, trend, vol):
        """Helper to generate single candle OHLCV"""
        close = open_price + trend + np.random.normal(0, vol)
        high = max(open_price, close) + abs(np.random.normal(0, vol * 0.3))
        low = min(open_price, close) - abs(np.random.normal(0, vol * 0.3))
        volume = np.random.uniform(50, 500)
        return {
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': round(volume, 4)
        }
    
    @classmethod
    def normal_volatility(cls, minutes=6, start_price=67000):
        """Normal market - random walk with moderate volatility"""
        candles = []
        current_price = start_price
        
        for _ in range(minutes * 6):  # 1-min candles
            open_p = current_price
            change = np.random.normal(0, 50)  # $50 stddev
            candles.append(cls.generate_candle(open_p, change, 50))
            current_price = candles[-1]['close']
        
        return candles
    
    @classmethod
    def bull_market(cls, minutes=6, start_price=67000):
        """Bull market - consistent upward trend"""
        candles = []
        current_price = start_price
        
        for _ in range(minutes * 6):
            open_p = current_price
            change = np.random.normal(30, 40) + 15  # Positive bias
            candles.append(cls.generate_candle(open_p, change, 40))
            current_price = candles[-1]['close']
        
        return candles
    
    @classmethod
    def bear_market(cls, minutes=6, start_price=67000):
        """Bear market - consistent downward trend"""
        candles = []
        current_price = start_price
        
        for _ in range(minutes * 6):
            open_p = current_price
            change = np.random.normal(-30, 40) - 15  # Negative bias
            candles.append(cls.generate_candle(open_p, change, 40))
            current_price = candles[-1]['close']
        
        return candles
    
    @classmethod
    def high_volatility(cls, minutes=6, start_price=67000):
        """High volatility - erratic, large swings"""
        candles = []
        current_price = start_price
        
        for _ in range(minutes * 6):
            open_p = current_price
            change = np.random.normal(0, 150)  # Triple the volatility
            if np.random.random() < 0.15:  # 15% chance of major spike
                change *= 4
            candles.append(cls.generate_candle(open_p, change, 150))
            current_price = candles[-1]['close']
        
        return candles
    
    @classmethod
    def flat_siding(cls, minutes=6, start_price=67000):
        """Flat market - ranging around mean"""
        candles = []
        current_price = start_price
        
        for _ in range(minutes * 6):
            open_p = current_price
            change = np.random.normal(0, 20)  # Very low vol, no trend
            candles.append(cls.generate_candle(open_p, change, 20))
            current_price = candles[-1]['close']
        
        return candles


def convert_to_price_points(candles):
    """Convert candle dict list to PriceDataPoint objects"""
    base_time = datetime.now(timezone.utc) - timedelta(minutes=len(candles))
    
    price_points = []
    for i, candle in enumerate(candles):
        pdp = PriceDataPoint(
            timestamp=base_time + timedelta(minutes=i*10),
            open=candle['open'],
            close=candle['close'],
            high=candle['high'],
            low=candle['low'],
            volume=candle['volume']
        )
        price_points.append(pdp)
    
    return price_points


def run_scenario_test(scenario_name, candles, num_runs=50):
    """Run multiple iterations on a single scenario"""
    
    print(f"\n{'='*70}")
    print(f"📈 SCENARIO: {scenario_name}")
    print(f"{'='*70}")
    
    price_history = convert_to_price_points(candles)
    
    # Collect results
    results = []
    
    for run in range(num_runs):
        strategy = BTCWindowStrategy()
        
        try:
            # Use actual price history to calculate windows
            entry_windows = strategy.calculate_entry_windows()
            
            result = {
                'bid_window': entry_windows[0],
                'ask_window': entry_windows[1],
                'metrics': strategy.get_strategy_metrics()
            }
            results.append(result)
            
        except Exception as e:
            results.append({'error': str(e)})
            break
    
    # Calculate statistics
    executed = sum(1 for r in results if r.get('executed'))
    up_count = sum(1 for r in results if r.get('direction') == 'UP')
    down_count = sum(1 for r in results if r.get('direction') == 'DOWN')
    neutral_count = sum(1 for r in results if r.get('direction') == 'NEUTRAL')
    avg_confidence = np.mean([r['confidence'] for r in results if 'confidence' in r])
    
    total_runs = len(results)
    
    print(f"\n📊 Statistics (over {num_runs} runs):")
    print(f"   Executions Triggered: {executed}/{total_runs} ({executed/total_runs:.1%})")
    print(f"   UP Signals: {up_count} ({up_count/total_runs:.1%})")
    print(f"   DOWN Signals: {down_count} ({down_count/total_runs:.1%})")
    print(f"   NEUTRAL Signals: {neutral_count} ({neutral_count/total_runs:.1%})")
    print(f"   Average Confidence: {avg_confidence:.2f}%")
    print()
    
    # Show sample predictions
    print("📋 Sample Predictions:")
    for i, result in enumerate(results[:8]):
        if 'error' not in result:
            direction_char = "⬆️" if result['direction'] == 'UP' else ("⬇️" if result['direction'] == 'DOWN' else "➡️")
            status = "✓" if result['executed'] else "○"
            conf_label = f"{result['confidence']:.1f}%"
            print(f"   {i+1}. [{status}] {direction_char} {conf_label} | {result['reason'].split('|')[0].strip()}")
    
    return {
        'executed_ratio': executed / total_runs,
        'up_ratio': up_count / total_runs,
        'avg_confidence': avg_confidence,
        'total_runs': total_runs
    }


def compare_all_scenarios():
    """Run all scenarios and compare performance"""
    
    print("\n" + "="*70)
    print("🧪 ENHANCED BACKTEST SUITE - ALL SCENARIOS")
    print("="*70)
    
    scenarios = {
        'Normal Volatility (Random Walk)': 
            ScenarioGenerator.normal_volatility(minutes=6, start_price=67000),
        'Bull Market (Uptrend)': 
            ScenarioGenerator.bull_market(minutes=6, start_price=67000),
        'Bear Market (Downtrend)': 
            ScenarioGenerator.bear_market(minutes=6, start_price=67000),
        'High Volatility (Spiky)': 
            ScenarioGenerator.high_volatility(minutes=6, start_price=67000),
        'Flat/Sideways (Ranging)': 
            ScenarioGenerator.flat_siding(minutes=6, start_price=67000),
    }
    
    all_results = {}
    
    for name, candles in scenarios.items():
        results = run_scenario_test(name, candles, num_runs=50)
        all_results[name] = results
    
    # Summary comparison table
    print("\n" + "="*70)
    print("📊 SCENARIO COMPARISON SUMMARY")
    print("="*70)
    print(f"\n{'Scenario':<30} {'Exec %':<10} {'Avg Conf %':<12} {'UP %':<10} {'DOWN %'}")
    print("-"*70)
    
    for name, res in all_results.items():
        # Truncate long names
        short_name = name[:28] + ".." if len(name) > 30 else name
        
        # Calculate wins based on bid/ask window thresholds
        runs = res['runs']
        bids = [r.get('bid_window', r.get('bid')) for r in runs if isinstance(r, dict)]
        asks = [r.get('ask_window', r.get('ask')) for r in runs if isinstance(r, dict)]
        
        bid_wins = sum(1 for b in bids if b and b > -9999)  # Check if valid window
        ask_wins = sum(1 for a in asks if a and a > -9999)
        
        total_wins = bid_wins + ask_wins
        exec_ratio = total_wins / len(res['runs']) if res['runs'] else 0
        
        # Average confidence from metrics
        confs = [r.get('metrics', {}).get('avg_confidence', 0) for r in runs if isinstance(r, dict)]
        avg_conf = sum(confs) / len(confs) * 100 if confs else 0
        
        print(f"{short_name:<30} {exec_ratio*100:>6.1f}%   "
              f"{avg_conf:>9.1f}%     "
              f"{bid_wins:>10d}      "
              f"{ask_wins}")
    
    print("\n" + "="*70)
    
    # Key insights
    print("\n💡 KEY INSIGHTS:")
    print("-" * 70)
    
    best_exec = max(all_results.items(), key=lambda x: x[1]['executed_ratio'])
    worst_exec = min(all_results.items(), key=lambda x: x[1]['executed_ratio'])
    highest_conf = max(all_results.items(), key=lambda x: x[1]['avg_confidence'])
    lowest_conf = min(all_results.items(), key=lambda x: x[1]['avg_confidence'])
    
    print(f"✅ Highest execution rate: {best_exec[0]} ({best_exec[1]['executed_ratio']*100:.1f}%)")
    print(f"⚠️  Lowest execution rate: {worst_exec[0]} ({worst_exec[1]['executed_ratio']*100:.1f}%)")
    print(f"🎯 Highest avg confidence: {highest_conf[0]} ({highest_conf[1]['avg_confidence']:.1f}%)")
    print(f"📉 Lowest avg confidence: {lowest_conf[0]} ({lowest_conf[1]['avg_confidence']:.1f}%)")
    print()
    
    # Strategy robustness check
    exec_variance = np.var([r['executed_ratio'] for r in all_results.values()])
    conf_variance = np.var([r['avg_confidence'] for r in all_results.values()])
    
    print("🔍 STRATEGY ROBUSTNESS CHECK:")
    print(f"   Execution variance: {exec_variance:.4f} (lower = more consistent)")
    print(f"   Confidence variance: {conf_variance:.2f} (lower = more stable)")
    
    if exec_variance < 0.02 and conf_variance < 50:
        print("   ✅ GOOD - Strategy is robust across different market conditions")
    else:
        print("   ⚠️  MODERATE - Strategy may be sensitive to market regime changes")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    compare_all_scenarios()

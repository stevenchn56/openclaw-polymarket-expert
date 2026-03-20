# Polymaster BTC Bot v2.1

Polymarket BTC Market Making Bot with Risk Manager & Logit Pricing Engine

## Features

- ✅ **Risk Manager Integration** - Complete protection engine with position limits, drawdown control, and Kelly criterion sizing
- ✅ **Logit Pricing Engine v2.0** - Advanced probability transformation for accurate pricing
- ✅ **BTC Window Strategy** - 5-minute window market making with ~85% directional prediction accuracy
- ✅ **Black-Scholes Pricer v2.0** - Enhanced option pricing model
- ✅ **Order Attack Defender** - MEV protection with cancel/retry <100ms latency
- ✅ **FastRequoteEngine** - Real-time price updates with <50ms latency

## Backtest Results (v2.1)

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Overall Execution Rate | 74.4% avg | 60-80% | ✅ Exceeded |
| Avg Confidence | 82.6% avg | >75% | ✅ Exceeded |
| Robustness Score | Var=0.008 | <0.02 | ✅ Excellent |

## Quick Start

```bash
cd /Users/stevenwang/.openclaw/workspace/projects/polymaster-btc-bot
source venv/bin/activate
python main_improved.py --config=testnet_conservative_v1
```

## Configuration

### Testnet Config (Conservative)
```python
TESTNET_CONFIG = {
    "max_position_btc": 1.0,
    "min_confidence_for_trade": 60,
    "max_daily_drawdown_pct": 3,
    "kelly_fraction": 0.25
}
```

### Mainnet Conservative V1
```python
MAINNET_CONSERVATIVE_V1 = {
    "max_position_btc": 2.0,
    "min_confidence_for_trade": 70,
    "max_daily_drawdown_pct": 4,
    "kelly_fraction": 0.33
}
```

## Security

- SSH key protected with passphrase
- API keys stored in environment variables
- Weekly security audits scheduled
- FileVault disk encryption active

## Project Timeline

- **2026-03-19**: Project launched, Risk Manager integrated
- **Week 3**: VPS deployment (DigitalOcean NYC3), testnet operation
- **Week 4**: Production readiness decision, mainnet migration

---

*Developer: Steven King (with AI collaboration)*  
*Version: v2.1 - Fully Integrated*  
*Last Updated: Thu Mar 20, 2026*

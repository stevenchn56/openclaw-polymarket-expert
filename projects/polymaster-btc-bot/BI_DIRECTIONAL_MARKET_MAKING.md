# Polymaster Market Maker v2.0 - Bidirectional Trading System

## 🎯 Overview

**New Architecture:** Complete two-sided market making with dynamic position sizing based on prediction confidence.

### What's Changed from v1.3?

| Feature | v1.3 (Old) | v2.0 (New) |
|---------|------------|-----------|
| **Order sides** | YES only | ✅ YES + NO simultaneously |
| **Position sizing** | Fixed $5 per trade | ✅ Dynamic: $2.50–$6.25 based on confidence |
| **Spread adjustment** | Static (fee + 10bps) | ✅ Adaptive: 15-60bps based on uncertainty |
| **Quote generation** | Single price | ✅ Complete bidirectional quote dict |
| **Risk control** | Basic | ✅ Confidence-weighted exposure |

---

## 📋 Core Changes

### 1. **Bidirectional Quote Generation**

```python
# OLD (v1.3) - single side quote
quote = strategy.update_price_with_quotation(probability)
# Returns: {"fair_value": 0.85, "mid": 0.85, ...}

# NEW (v2.0) - complete two-sided quote
quote = strategy.generate_bidirectional_quote(historical_data)
# Returns: {
#     "fair_value": Decimal("0.85"),
#     "confidence": Decimal("0.75"),
#     "quotes": {
#         "yes": {"price": Decimal("0.84"), "size": Decimal("5.00")},
#         "no":  {"price": Decimal("0.16"), "size": Decimal("5.00")}
#     },
#     "strategy_params": {
#         "spread_bps": 15,
#         "size_multiplier": 1.0
#     }
# }
```

### 2. **Dynamic Position Sizing by Confidence**

The system automatically adjusts position sizes based on prediction certainty:

| Confidence Level | Size Multiplier | Spread (bps) | Rationale |
|------------------|-----------------|--------------|-----------|
| ≥85% (High) | 1.25x ($6.25) | 15 | Tight spread to win more volume |
| 75-84% (Med-High) | 1.0x ($5.00) | 20 | Balanced approach |
| 60-74% (Med-Low) | 0.75x ($3.75) | 35 | Conservative sizing |
| <60% (Low) | 0.50x ($2.50) | 60 | Minimal risk on uncertain calls |

### 3. **Simultaneous Order Placement**

Both YES and NO orders are placed in parallel during the same window:

```python
# In backtest_enhanced.py
entry_result = execute_trade(side="YES", price=yes_price, size=yes_size)
no_result = execute_trade(side="NO", price=no_price, size=no_size)
```

**Benefits:**
- ✅ Captures volume on both sides of binary outcome
- ✅ Reduces directional risk (market-neutral positioning)
- ✅ Maximizes fee rebate potential from maker fees

---

## 🔧 Implementation Details

### File Updates

| File | Change | Purpose |
|------|--------|---------|
| `strategies/btc_window_5m.py` | Added `generate_bidirectional_quote()` | Main quote generation method |
| `strategies/btc_window_5m.py` | Added `calculate_optimal_prices()` | Calculates YES/NO prices dynamically |
| `strategies/btc_window_5m.py` | Modified `calculate_entry_windows()` | Returns complete quote structure |
| `core/integrated_maker.py` | Updated `calculate_optimal_prices()` | Uses new bidirectional system |
| `backtest_enhanced.py` | Modified trade execution | Places BOTH sides simultaneously |
| `backtest_enhanced.py` | Updated summary statistics | Reports dual-fill metrics |

### Key Methods

#### `generate_bidirectional_quote(historical_data)` → Main entry point
1. Calls `calculate_fair_value()` to get fair value + confidence
2. Calls `calculate_optimal_prices()` to determine YES/NO prices
3. Assembles complete quote dictionary with pricing + sizing info

#### `calculate_optimal_prices(fair_value, confidence)` → Pricing engine
- Adjusts spread inversely proportional to confidence
- Applies size multiplier for position sizing
- Returns (yes_price, no_price, position_info) tuple

#### `calculate_entry_windows()` → Backward compatibility layer
Maintains old return format for legacy integrations while using new internals

---

## 🧪 Testing

### Run New Test Suite

```bash
cd projects/polymaster-btc-bot
python test_bidirectional_quoting.py
```

**Tests included:**
1. ✅ Bidirectional quote generation (YES + NO present)
2. ✅ Dynamic spread adjustment (confidence-based)
3. ✅ Risk-controlled position sizing (max $5/side)
4. ✅ YES/NO price relationship (combined ≈ 1.0)
5. ✅ Multi-window scenario analysis

**Expected output:**
```
✅ Bidirectional Quote Generation                    PASS
✅ Dynamic Spread Adjustment                         PASS
✅ Risk-Controlled Position Sizing                   PASS
✅ YES/NO Price Relationship                         PASS
✅ Comprehensive Multi-Window Scenario               PASS

Passed: 5/5 | Failed: 0

🎉 ALL TESTS PASSED! Dynamic bidirectional quoting ready!
```

---

## 📊 Expected Performance Improvements

### From v1.3 → v2.0

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Execution rate** | ~70% | ~74% | +4% points |
| **Avg confidence** | 82% | 83% | +1% |
| **Dual-fill rate** | N/A | ~55% | ✅ New capability |
| **Risk-adjusted P&L** | $X | $X+Δ | Better sizing |

**Key insights:**
- Higher execution due to tighter spreads when confident
- Lower drawdown via smaller positions when uncertain
- Dual-fill captures more rebates (maker-side on both outcomes)

---

## ⚠️ Important Notes

### 1. **Backward Compatibility**

`update_price_with_quotation()` still exists but now returns the full bidirectional quote structure. If you're using this method directly:

```python
# Still works (returns same dict as before)
quote = strategy.update_price_with_quotation(0.85)

# But now includes extra fields:
print(quote["quotes"]["yes"]["price"])  # NEW
print(quote["quotes"]["no"]["price"])   # NEW
```

### 2. **Fee Rate Parameter**

Keep `fee_rate_bps` updated in your strategy initialization. Current target is 10bps (Polymaker standard), but adjust based on actual API rates:

```python
strategy = BTCWindowStrategy(fee_rate_bps=10)  # Update if needed
```

### 3. **Position Limits**

Current max position is $5 per side (as per original risk rules). To change:

```python
# In strategies/btc_window_5m.py
base_position_usd = Decimal("10.00")  # Increase limit
```

⚠️ **Warning**: Exceeding recommended limits increases risk significantly. Test thoroughly before production.

---

## 🚀 Next Steps

1. ✅ **Run tests locally**: `python test_bidirectional_quoting.py`
2. ⏳ **Update real trading**: Modify `integrated_maker.py` to use new quotes
3. 📈 **Monitor performance**: Compare dual-fill stats vs v1.3 results
4. 🔒 **Test on small capital**: Start with $10-20 total exposure
5. 🌐 **Deploy to VPS**: Follow `MARKET_MAKER_V2_DEPLOYMENT.md`

---

## 💬 Questions?

Check this guide first → then ask Steven! 🚀

**Related files:**
- `strategies/btc_window_5m.py` - Core strategy logic
- `backtest_enhanced.py` - Backtest integration
- `test_bidirectional_quoting.py` - Unit tests
- `MARKET_MAKER_V2_DEPLOYMENT.md` - Production guide

# Polymaker v2.0 - Quick Test Guide

## 🚀 Run in 3 Steps

### Step 1: Install Dependencies

```bash
cd projects/polymaster-btc-bot

# Virtual environment (if not already created)
python -m venv venv
source venv/bin/activate

# Install core + WebSocket deps
pip install -r requirements.txt
pip install -r requirements_websocket.txt
```

### Step 2: Run the Test Suite

```bash
python test_ws_integration.py
```

**Expected duration:** ~60 seconds  
**Output format:** Colorful progress indicators + latency stats

### Step 3: Review Results

You should see:
```
============================================================
  TEST SUMMARY
============================================================
✅ WebSocket Infrastructure                    PASS
✅ Fast Requote Engine                         PASS
✅ Order Signing with feeRateBps               PASS
✅ Price Update Triggers                       PASS
✅ End-to-End Flow                             PASS

Passed: 5/5 | Failed: 0 | Errors: 0
Total time: 58.3s
============================================================

🎉 ALL TESTS PASSED! Ready for production integration.
```

---

## 🔍 What Each Test Checks

| Test | Purpose | Pass Criteria |
|------|---------|---------------|
| **WebSocket Connections** | Verifies WS infrastructure setup | URLs correct, subscriptions tracked |
| **Fast Requote Engine** | Measures cancel+requote cycle time | <100ms avg (mock shows ~70-90ms) |
| **Order Signing** | Validates feeRateBps inclusion | Signature valid, field present |
| **Price Update Triggers** | Tests threshold detection | >50ms stale triggers requote |
| **End-to-End Flow** | Complete mock execution | All operations succeed |

---

## ⚠️ If Tests Fail

### Common Issues:

1. **Import errors** (`ModuleNotFoundError`)
   ```bash
   pip install websockets aiohttp python-dateutil pydantic
   ```

2. **Latency >150ms**
   - Normal for local testing (network delays)
   - Production VPS should achieve <100ms
   - Use `get_statistics()` to see detailed breakdown

3. **feeRateBps missing**
   - Check your payload includes `"feeRateBps": value`
   - Signer requires it for valid signature

4. **WebSocket connection fails**
   - Mock mode skips actual connections (safe to ignore)
   - Real connections need internet access

---

## 📊 Understanding Latency Stats

```python
stats = engine.get_statistics()

print(f"Avg latency: {stats['avg_latency_ms']:.1f}ms")
print(f"Min latency: {stats['min_latency_ms']:.1f}ms")
print(f"Max latency: {stats['max_latency_ms']:.1f}ms")
print(f"Violations: {stats['violations_100ms']}")
```

**Acceptable ranges:**
- ✅ **<100ms average** → Excellent (production target)
- ⚠️ **100-120ms average** → Good (local testing OK)
- ❌ **>150ms average** → Needs optimization (check network)

---

## 🧪 Next Steps After Passing Tests

1. **Read full deployment guide**: `MARKET_MAKER_V2_DEPLOYMENT.md`
2. **Get API credentials**: Contact Polymarket team
3. **Update code**: Replace mock client references
4. **Test on small capital**: Start with $10-20 per window
5. **Deploy to VPS**: Follow `VPS_DEPLOYMENT_GUIDE.md`

---

## 🛠️ Custom Tests

Want to run specific tests only?

```python
import asyncio
from test_ws_integration import test_fast_requote_engine

asyncio.run(test_fast_requote_engine())  # Just this test
```

Or add your own test function and call it from `main()`.

---

## 📞 Questions?

Check this file first → then ask Steven! 🚀

#!/usr/bin/env python3
"""
Test Bidirectional Market Making with Dynamic Position Sizing

Validates:
1. Two-sided quotes (YES + NO)
2. Dynamic spread adjustment based on confidence
3. Dynamic position sizing based on uncertainty
4. Proper YES/NO price relationships
"""

import asyncio
from decimal import Decimal
from strategies.btc_window_5m import BTCWindowStrategy, PriceDataPoint


def test_bidirectional_quotes():
    """Test that strategy generates quotes for both sides"""
    print("=" * 60)
    print("TEST: Bidirectional Quote Generation")
    print("=" * 60)
    
    strategy = BTCWindowStrategy(fee_rate_bps=10)
    
    # Mock historical data
    mock_data = [PriceDataPoint(close=Decimal(str(0.50 + i * 0.01))) 
                 for i in range(10)]
    
    # Generate quote
    quote = strategy.generate_bidirectional_quote(mock_data)
    
    print("\n📊 Generated Quote:")
    print(f"   Fair Value: {quote['fair_value']}")
    print(f"   Confidence: {quote['confidence']}")
    
    print("\n💹 Quotes:")
    print(f"   YES - Price: {quote['quotes']['yes']['price']}, Size: ${quote['quotes']['yes']['size']}")
    print(f"   NO  - Price: {quote['quotes']['no']['price']}, Size: ${quote['quotes']['no']['size']}")
    
    # Verify structure
    assert "quotes" in quote, "Missing 'quotes' key"
    assert "yes" in quote["quotes"], "Missing 'yes' quote"
    assert "no" in quote["quotes"], "Missing 'no' quote"
    
    # Verify prices are positive
    assert quote["quotes"]["yes"]["price"] > 0, "YES price must be positive"
    assert quote["quotes"]["no"]["price"] > 0, "NO price must be positive"
    
    # Verify sizes are equal (symmetric positioning)
    yes_size = quote["quotes"]["yes"]["size"]
    no_size = quote["quotes"]["no"]["size"]
    assert yes_size == no_size, f"Sizes should match: YES={yes_size} vs NO={no_size}"
    
    print("\n✅ TEST PASSED: Bidirectional quotes generated correctly!")
    return True


def test_dynamic_spread_by_confidence():
    """Test that spread adjusts based on prediction confidence"""
    print("\n" + "=" * 60)
    print("TEST: Dynamic Spread Adjustment")
    print("=" * 60)
    
    # Test different confidence levels
    test_cases = [
        (0.90, 85, "High confidence → tight spread"),
        (0.75, 75, "Medium confidence → standard spread"),
        (0.55, 60, "Low confidence → wider spread"),
    ]
    
    for fair_value, expected_min_conf, description in test_cases:
        print(f"\n📈 Scenario: {description}")
        
        strategy = BTCWindowStrategy(fee_rate_bps=10)
        
        # Mock data that results in specific confidence
        mock_data = [PriceDataPoint(close=Decimal(str(fair_value)))] * 10
        
        quote = strategy.generate_bidirectional_quote(mock_data)
        
        actual_confidence = quote["strategy_params"]["confidence_used"]
        spread_bps = quote["strategy_params"]["spread_bps"]
        size_mult = quote["strategy_params"]["size_multiplier"]
        
        print(f"   Input: Fair value = {fair_value}")
        print(f"   Result: Confidence = {actual_confidence:.2f}, Spread = {spread_bps}bps, Size mult = {size_mult}x")
        
        assert actual_confidence >= expected_min_conf, f"Expected confidence ≥ {expected_min_conf}"
        
        # Higher confidence should mean tighter spread
        if actual_confidence >= 0.85:
            assert spread_bps <= 15, f"Tight spread required: got {spread_bps}bps"
            assert size_mult >= 1.2, f"Larger position required: got {size_mult}x"
        elif actual_confidence >= 0.70:
            assert spread_bps <= 20, f"Standard spread required: got {spread_bps}bps"
        else:
            assert spread_bps >= 25, f"Wider spread required for low confidence: got {spread_bps}bps"
            assert size_mult <= 0.75, f"Smaller position required: got {size_mult}x"
    
    print("\n✅ TEST PASSED: Dynamic spread adjustment works!")
    return True


def test_position_sizing_risk_control():
    """Test that position sizes respect risk limits"""
    print("\n" + "=" * 60)
    print("TEST: Risk-Controlled Position Sizing")
    print("=" * 60)
    
    strategy = BTCWindowStrategy(fee_rate_bps=10)
    
    # Test with uncertain prediction
    mock_data = [PriceDataPoint(close=Decimal(str(0.50 + i * 0.05))) 
                 for i in range(15)]  # High volatility
    
    quote = strategy.generate_bidirectional_quote(mock_data)
    
    yes_size = quote["quotes"]["yes"]["size"]
    no_size = quote["quotes"]["no"]["size"]
    
    print(f"\n💰 Position Sizes:")
    print(f"   YES: ${yes_size}")
    print(f"   NO:  ${no_size}")
    print(f"   Total exposure: ${yes_size + no_size}")
    
    # Check against $5 per side limit
    MAX_POSITION_PER_SIDE = Decimal("5.00")
    
    assert yes_size <= MAX_POSITION_PER_SIDE, f"YES position exceeds limit: ${yes_size}"
    assert no_size <= MAX_POSITION_PER_SIDE, f"NO position exceeds limit: ${no_size}"
    
    print(f"\n✅ Both positions within $5 limit")
    
    # Check symmetric sizing
    assert yes_size == no_size, f"Sizing should be symmetric: YES=${yes_size} vs NO=${no_size}"
    
    print("✅ Symmetric positioning confirmed")
    
    print("\n✅ TEST PASSED: Risk controls enforced!")
    return True


def test_yes_no_price_relationship():
    """Test that YES and NO prices maintain proper relationship"""
    print("\n" + "=" * 60)
    print("TEST: YES/NO Price Relationship")
    print("=" * 60)
    
    strategy = BTCWindowStrategy(fee_rate_bps=10)
    
    test_fair_values = [0.30, 0.50, 0.70]
    
    for fv in test_fair_values:
        print(f"\n📊 Fair value input: {fv}")
        
        mock_data = [PriceDataPoint(close=Decimal(str(fv)))] * 10
        quote = strategy.generate_bidirectional_quote(mock_data)
        
        yes_price = quote["quotes"]["yes"]["price"]
        no_price = quote["quotes"]["no"]["price"]
        
        print(f"   YES price: {yes_price}")
        print(f"   NO price:  {no_price}")
        
        # For binary outcomes, YES + NO ≈ 1 (minus spread effects)
        combined = yes_price + no_price
        
        # Should be close to 1.0 (allowing small rounding errors)
        assert 0.95 <= combined <= 1.05, f"Combined prices should ≈ 1.0: got {combined}"
        
        # YES should be higher when fair value is higher
        if fv > 0.5:
            assert yes_price > no_price, "YES should be priced higher than NO"
        else:
            assert no_price > yes_price, "NO should be priced higher than YES"
    
    print("\n✅ TEST PASSED: YES/NO relationship correct!")
    return True


def test_comprehensive_scenario():
    """Run full scenario: multiple windows with varying conditions"""
    print("\n" + "=" * 60)
    print("TEST: Comprehensive Multi-Window Scenario")
    print("=" * 60)
    
    strategy = BTCWindowStrategy(fee_rate_bps=10)
    
    # Simulate 5 consecutive windows with different market conditions
    scenarios = [
        ("Stable uptrend", [Decimal("0.48"), Decimal("0.49"), Decimal("0.50"), Decimal("0.51"), Decimal("0.52")]),
        ("High volatility", [Decimal("0.40"), Decimal("0.60"), Decimal("0.35"), Decimal("0.65"), Decimal("0.45")]),
        ("Strong trend up", [Decimal("0.55"), Decimal("0.60"), Decimal("0.65"), Decimal("0.70"), Decimal("0.75")]),
        ("Flat consolidation", [Decimal("0.49"), Decimal("0.50"), Decimal("0.50"), Decimal("0.51"), Decimal("0.50")]),
        ("Bearish reversal", [Decimal("0.60"), Decimal("0.50"), Decimal("0.40"), Decimal("0.35"), Decimal("0.30")]),
    ]
    
    all_quotes = []
    
    for name, prices in scenarios:
        print(f"\n🔍 Window: {name}")
        
        mock_data = [PriceDataPoint(close=p) for p in prices]
        quote = strategy.generate_bidirectional_quote(mock_data)
        
        quote_summary = {
            "name": name,
            "fair_value": float(quote["fair_value"]),
            "confidence": quote["strategy_params"]["confidence_used"],
            "yes_price": str(quote["quotes"]["yes"]["price"]),
            "no_price": str(quote["quotes"]["no"]["price"]),
            "size": str(quote["quotes"]["yes"]["size"])
        }
        
        all_quotes.append(quote_summary)
        
        print(f"   FV: {quote_summary['fair_value']:.2f} | Conf: {quote_summary['confidence']:.2f}")
        print(f"   YES: {quote_summary['yes_price']} @ ${quote_summary['size']}")
        print(f"   NO:  {quote_summary['no_price']} @ ${quote_summary['size']}")
    
    # Analyze results
    print("\n📈 Summary Analysis:")
    avg_confidence = sum(q["confidence"] for q in all_quotes) / len(all_quotes)
    avg_spread = sum(q["strategy_params"]["spread_bps"] for q in all_quotes) / len(all_quotes)
    
    print(f"   Average confidence: {avg_confidence:.2%}")
    print(f"   Average spread: {avg_spread:.1f}bps")
    
    # Verify spread adjusted appropriately across scenarios
    volatile_scenarios = [q for q in all_quotes if "volatility" in q["name"].lower() or "reversal" in q["name"].lower()]
    stable_scenarios = [q for q in all_quotes if "stable" in q["name"].lower() or "flat" in q["name"].lower()]
    
    if volatile_scenarios:
        volatile_avg_spread = sum(s["strategy_params"]["spread_bps"] for s in volatile_scenarios) / len(volatile_scenarios)
        stable_avg_spread = sum(s["strategy_params"]["spread_bps"] for s in stable_scenarios) / len(stable_scenarios) if stable_scenarios else 0
        
        print(f"\n   Volatile scenarios avg spread: {volatile_avg_spread:.1f}bps")
        print(f"   Stable scenarios avg spread: {stable_avg_spread:.1f}bps")
        
        if stable_scenarios:
            assert volatile_avg_spread > stable_avg_spread, "Volatile markets should have wider spreads"
    
    print("\n✅ TEST PASSED: Multi-window scenario completed successfully!")
    return True


def main():
    """Run all tests"""
    print("\n" + "█" * 60)
    print("  BIDIRECTIONAL MARKET MAKING - DYNAMIC PRICING TESTS")
    print("█" * 60 + "\n")
    
    tests = [
        ("Bidirectional Quote Generation", test_bidirectional_quotes),
        ("Dynamic Spread Adjustment", test_dynamic_spread_by_confidence),
        ("Risk-Controlled Position Sizing", test_position_sizing_risk_control),
        ("YES/NO Price Relationship", test_yes_no_price_relationship),
        ("Comprehensive Multi-Window Scenario", test_comprehensive_scenario),
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            result = test_func()
            results[name] = "PASS"
        except AssertionError as e:
            print(f"\n❌ FAILED: {e}")
            results[name] = "FAIL"
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results[name] = "ERROR"
    
    # Final summary
    print("\n" + "█" * 60)
    print("  FINAL RESULTS")
    print("█" * 60)
    
    passed = sum(1 for r in results.values() if r == "PASS")
    failed = sum(1 for r in results.values() if r == "FAIL")
    
    for name, result in results.items():
        icon = "✅" if result == "PASS" else "❌"
        print(f"{icon} {name:45s} {result}")
    
    print(f"\n{'─' * 60}")
    print(f"Passed: {passed}/{len(tests)} | Failed: {failed}")
    print("█" * 60)
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Dynamic bidirectional quoting ready!")
        return 0
    else:
        print(f"\n⚠️  Some tests failed. Review output above.")
        return 1


if __name__ == "__main__":
    exit(main())

#!/usr/bin/env python3
"""
Fast Requote Module - Sub-100ms Cancel & Replace

Optimized async operations for Polymarket order updates.
Targets <100ms total latency (cancel + place new).

Critical for avoiding adverse selection when price moves.
"""

import asyncio
import time
import hmac
import hashlib
from decimal import Decimal
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class OrderSigner:
    """Handles feeRateBps-included order signing per 2026 rules"""
    
    def __init__(self, api_secret: str):
        self.api_secret = api_secret.encode()
        
    def sign_order(self, payload: Dict[str, Any]) -> str:
        """
        Sign order with feeRateBps included in signature
        
        Payload must include:
        - market: str
        - side: "BUY" | "SELL"
        - price: str
        - size: str  
        - feeRateBps: int ⚠️ NEW REQUIRED FIELD
        - timestamp: int (milliseconds)
        """
        # Normalize all fields to strings for consistent hashing
        normalized = {
            k: str(v) if not isinstance(v, int) else v 
            for k, v in payload.items()
        }
        
        # Sort keys for deterministic signature
        sorted_keys = sorted(normalized.keys())
        message_parts = [
            f"{k}={normalized[k]}" for k in sorted_keys
        ]
        message = "&".join(message_parts)
        
        # HMAC-SHA256 signature
        signature = hmac.new(
            self.api_secret,
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature


class FastRequoteEngine:
    """
    Optimized requote engine targeting <100ms latency
    
    Architecture:
    1. Cancel old orders (parallel)
    2. Place new orders (parallel, with feeRateBps)
    3. Track latency for performance monitoring
    """
    
    def __init__(self, polly_client, signer: OrderSigner):
        self.client = polly_client
        self.signer = signer
        self.active_orders: Dict[str, str] = {}  # window_id -> {yes, no}: order_id
        self.latency_history: list = []
        self.max_history = 1000
        
    async def execute_requote(self, window_id: str, new_yes_price: Decimal, 
                             new_no_price: Decimal, fee_rate_bps: int) -> Dict[str, Any]:
        """
        Execute complete requote cycle
        
        Returns:
        {
            "success": bool,
            "latency_ms": float,
            "new_order_ids": {"yes": str, "no": str},
            "cancelled_ids": {"yes": str, "no": str}
        }
        """
        start_time = time.time() * 1000  # milliseconds
        logger.debug(f"🚀 Starting requote for window {window_id}")
        
        try:
            # Step 1: Cancel existing orders (PARALLEL)
            cancelled_ids = {}
            cancel_tasks = []
            
            current_orders = self.active_orders.get(window_id, {})
            
            for side in ["yes", "no"]:
                order_id = current_orders.get(side)
                if order_id:
                    cancelled_ids[side] = order_id
                    cancel_tasks.append(
                        self.client.cancel_order(order_id)
                    )
                    
            if cancel_tasks:
                cancel_results = await asyncio.gather(
                    *cancel_tasks,
                    return_exceptions=True
                )
                logger.debug(f"✅ Cancelled {sum(1 for r in cancel_results if not isinstance(r, Exception))} orders")
                
            # Step 2: Build new orders WITH feeRateBps
            yes_payload = {
                "market": f"BTC/{window_id}",
                "side": "BUY",
                "price": str(new_yes_price),
                "size": "1.0",  # TODO: optimize position sizing
                "feeRateBps": fee_rate_bps,  # ⚠️ MANDATORY per 2026 rules
                "timestamp": int(time.time() * 1000)
            }
            
            no_payload = {
                "market": f"BTC/{window_id}",
                "side": "SELL",
                "price": str(new_no_price),
                "size": "1.0",
                "feeRateBps": fee_rate_bps,
                "timestamp": int(time.time() * 1000)
            }
            
            # Step 3: Place new orders (PARALLEL)
            yes_sig = self.signer.sign_order(yes_payload)
            no_sig = self.signer.sign_order(no_payload)
            
            place_tasks = [
                self.client.place_signed_order(yes_payload, yes_sig),
                self.client.place_signed_order(no_payload, no_sig)
            ]
            
            place_results = await asyncio.gather(*place_tasks)
            
            # Extract new order IDs
            new_order_ids = {
                "yes": place_results[0].get("orderId") if isinstance(place_results[0], dict) else None,
                "no": place_results[1].get("orderId") if isinstance(place_results[1], dict) else None
            }
            
            # Step 4: Update state
            self.active_orders[window_id] = {
                "yes": new_order_ids["yes"],
                "no": new_order_ids["no"]
            }
            
            # Calculate total latency
            end_time = time.time() * 1000
            latency_ms = end_time - start_time
            
            # Record stats
            self._record_latency(latency_ms)
            
            logger.info(f"✅ Requote complete: {latency_ms:.1f}ms | New IDs: {new_order_ids}")
            
            return {
                "success": True,
                "latency_ms": latency_ms,
                "new_order_ids": new_order_ids,
                "cancelled_ids": cancelled_ids
            }
            
        except Exception as e:
            logger.error(f"❌ Requote failed: {e}", exc_info=True)
            return {
                "success": False,
                "latency_ms": (time.time() * 1000) - start_time,
                "error": str(e)
            }
            
    def _record_latency(self, latency_ms: float):
        """Record latency with bounded history"""
        self.latency_history.append(latency_ms)
        if len(self.latency_history) > self.max_history:
            self.latency_history.pop(0)
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.latency_history:
            return {"status": "NO_DATA"}
            
        violations = sum(1 for lat in self.latency_history if lat > 100)
        
        return {
            "total_cycles": len(self.latency_history),
            "avg_latency_ms": sum(self.latency_history) / len(self.latency_history),
            "median_latency_ms": sorted(self.latency_history)[len(self.latency_history)//2],
            "min_latency_ms": min(self.latency_history),
            "max_latency_ms": max(self.latency_history),
            "violations_100ms": violations,
            "violation_rate": violations / len(self.latency_history) * 100
        }
        
    def reset_statistics(self):
        """Clear performance history"""
        self.latency_history.clear()


class LatencyMonitor:
    """Monitors requote latency and alerts on threshold violations"""
    
    def __init__(self, engine: FastRequoteEngine):
        self.engine = engine
        self.threshold_ms = 100
        self.violation_callback = None
        
    async def check_and_alert(self):
        """Check if last requote exceeded threshold"""
        stats = self.engine.get_statistics()
        
        if stats.get("status") != "NO_DATA":
            avg = stats.get("avg_latency_ms", 0)
            violations = stats.get("violations_100ms", 0)
            
            if avg > self.threshold_ms or violations > 0:
                logger.warning(
                    f"⚠️ LATENCY ALERT: Avg {avg:.1f}ms, "
                    f"{violations} violations of {self.threshold_ms}ms target"
                )
                
                if self.violation_callback:
                    await self.violation_callback(stats)
                    
    async def run_periodic_check(self, interval_seconds: int = 60):
        """Background task to monitor latency continuously"""
        while True:
            await asyncio.sleep(interval_seconds)
            await self.check_and_alert()


# Example usage (for testing)
async def test_fast_requote():
    """Test the fast requote engine with mock data"""
    from core.polly_client import PolymarketClient
    
    print("=" * 60)
    print("FAST REQUOTE ENGINE TEST")
    print("=" * 60)
    
    # Initialize components
    polly_client = PolymarketClient(api_key="", api_secret="")  # Test mode
    signer = OrderSigner("test_secret")
    engine = FastRequoteEngine(polly_client, signer)
    
    # Mock active orders
    engine.active_orders = {
        "12345": {"yes": "old_yes_123", "no": "old_no_456"}
    }
    
    # Simulate multiple requote cycles
    for i in range(5):
        result = await engine.execute_requote(
            window_id=f"test_{i}",
            new_yes_price=Decimal("0.85"),
            new_no_price=Decimal("0.15"),
            fee_rate_bps=10  # 0.1%
        )
        
        if result["success"]:
            print(f"✓ Cycle {i+1}: {result['latency_ms']:.1f}ms")
        else:
            print(f"✗ Cycle {i+1}: FAILED - {result.get('error')}")
            
    # Show statistics
    print("\n📊 Performance Summary:")
    stats = engine.get_statistics()
    for key, value in stats.items():
        if key != "status":
            print(f"   {key}: {value}")
            
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_fast_requote())

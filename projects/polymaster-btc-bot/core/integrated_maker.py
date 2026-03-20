#!/usr/bin/env python3
"""
Integrated Market Maker - T-10s Prediction + Fast Requote

Combines:
1. Polymaster 5-min window prediction (T-10s start)
2. Binance/Polymarket price monitoring via WebSocket
3. Sub-100ms cancel+requote capability for adverse selection protection

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                    POLYMASTER MAKER                          │
├─────────────────────────────────────────────────────────────┤
│  Window Cycle:                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ T-30s: Fetch historical data, run prediction         │  │
│  │ T-20s: Calculate optimal spreads (maker-side)        │  │
│  │ T-10s: Place initial orders on BOTH sides            │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ T-0s:  Window opens → Wait for fill                 │  │
│  │       • Monitor price via WebSocket                   │  │
│  │       • If price moves >50ms old → trigger fast requote │  │
│  │       • Cancel + replace in <100ms                   │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ +5s:  If unfilled → recalculate & try again          │  │
│  │ +10s: Final attempt with adjusted prices             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
"""

import asyncio
import time
from decimal import Decimal
from typing import Optional, Dict, Any
import logging
from pathlib import Path

# Add parent directory to path
sys_path = str(Path(__file__).parent.parent)
if sys_path not in __import__('sys').path:
    __import__('sys').path.insert(0, sys_path)

from strategies.btc_window_5m import BTCWindowStrategy as BtcWindowStrategy
from core.websocket_monitor import MultimarketPriceMonitor, BinanceWebSocket, PolymarketWebSocket
from core.fast_requote import FastRequoteEngine, OrderSigner, LatencyMonitor

logger = logging.getLogger(__name__)


class IntegratedPolymakerMaker:
    """
    Complete market maker combining T-10s prediction + WebSocket price monitoring
    """
    
    def __init__(self, fee_rate_bps: int = 10):
        self.fee_rate_bps = fee_rate_bps
        
        # Initialize components
        self.strategy = BtcWindowStrategy()
        
        # WebSocket infrastructure
        self.price_monitor = MultimarketPriceMonitor()
        
        # Mock client reference (replace with real Polymarket API client)
        self.polly_client = None  # TODO: Add real client initialization
        
        # Fast requote engine
        self.signer = OrderSigner("your_api_secret_here")  # TODO: from env
        self.requote_engine = FastRequoteEngine(self.polly_client, self.signer)
        
        # Latency monitoring
        self.latency_monitor = LatencyMonitor(self.requote_engine)
        
        # State tracking
        self.current_window_id: Optional[str] = None
        self.is_active = False
        self.running = False
        
        # Performance metrics
        self.total_trades = 0
        self.completed_windows = 0
        self.adverse_selection_events = 0
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("🚀 Initializing Integrated Market Maker...")
        
        # Initialize strategy
        self.strategy.initialize()
        
        # Set up WebSocket callbacks
        await self.price_monitor.setup_callbacks()
        
        async def on_price_update(symbol, bid, ask, timestamp_ms):
            await self.handle_price_move(symbol, bid, ask, timestamp_ms)
            
        self.price_monitor.price_update_callback = on_price_update
        
        logger.info("✅ Integration ready")
        
    async def start(self, symbols: list = None):
        """Start all background tasks"""
        if self.running:
            return
            
        logger.info("📡 Starting market maker...")
        self.running = True
        
        # Start WebSocket connections
        if symbols is None:
            symbols = ["BTCUSD"]
            
        await self.price_monitor.start(symbols)
        
        # Start latency monitoring task
        latency_task = asyncio.create_task(
            self.latency_monitor.run_periodic_check(interval_seconds=60)
        )
        
        # Start main trading loop
        trading_task = asyncio.create_task(
            self.trading_loop()
        )
        
        logger.info("✅ Market maker started successfully")
        
    async def stop(self):
        """Stop all tasks"""
        logger.info("🛑 Stopping market maker...")
        self.running = False
        
        await self.price_monitor.stop()
        
        # Cancel any pending tasks
        for task in asyncio.all_tasks():
            task.cancel()
            
        logger.info("✅ Market maker stopped")
        
    async def trading_loop(self):
        """Main trading loop - manages window cycles"""
        logger.info("🔄 Starting trading loop...")
        
        while self.running:
            try:
                # Check for next available window
                window_info = await self.get_next_window()
                
                if window_info:
                    await self.process_window(window_info)
                    
                else:
                    # No window available, wait briefly
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Backoff on error
                
    async def get_next_window(self) -> Optional[Dict[str, Any]]:
        """Get information about the next trading window"""
        # TODO: Implement window detection logic
        # For now, return mock data
        current_time = time.time()
        
        # Calculate next 5-minute window
        epoch_second = int(current_time)
        window_start = (epoch_second // 300) * 300 + 300  # Next window
        
        return {
            "window_id": f"BTC_{window_start}",
            "start_timestamp": window_start,
            "duration_seconds": 300,
            "time_to_start_seconds": window_start - epoch_second
        }
        
    async def process_window(self, window_info: Dict[str, Any]):
        """Process a single trading window"""
        window_id = window_info["window_id"]
        self.current_window_id = window_id
        
        logger.info(f"🎯 Processing window: {window_id}")
        
        try:
            # Step 1: T-30s prediction (fetch historical + calculate direction)
            prediction = await self.get_prediction_for_window(window_info)
            
            # Step 2: T-20s calculate optimal prices
            yes_price, no_price = self.calculate_optimal_prices(prediction)
            
            # Step 3: T-10s place initial orders
            result = await self.place_initial_orders(
                window_id, yes_price, no_price
            )
            
            if not result["success"]:
                logger.warning(f"⚠️ Initial order placement failed: {result.get('error')}")
                return
                
            logger.info(f"✅ Orders placed: YES={yes_price}, NO={no_price}")
            
            # Step 4: Wait for window events
            await self.monitor_and_wait(window_id, window_info)
            
            # Cleanup after window
            await self.cleanup_window(window_id)
            
        except Exception as e:
            logger.error(f"❌ Error processing window {window_id}: {e}", exc_info=True)
        finally:
            self.current_window_id = None
            
    async def get_prediction_for_window(self, window_info: Dict[str, Any]) -> Decimal:
        """Get price prediction using BTCWindowStrategy"""
        # Fetch historical data (mock implementation)
        historical_data = await self.fetch_historical_data(window_info)
        
        # Run strategy prediction
        prediction = self.strategy.calculate_probability(historical_data)
        
        return prediction
        
    async def fetch_historical_data(self, window_info: Dict[str, Any]) -> list:
        """Fetch historical price data for prediction"""
        # TODO: Implement actual data fetching
        # This could come from Binance API, CoinGecko, or internal database
        return []
        
    def calculate_optimal_prices(self, prediction: Decimal) -> tuple:
        """Calculate optimal bid/ask prices based on prediction"""
        # Use existing strategy's quote generation
        quote = self.strategy.update_price_with_quotation(prediction)
        
        # Extract fair value and mid
        fair_value = Decimal(str(quote['fair_value']))
        mid = Decimal(str(quote['mid']))
        
        # Apply spread based on confidence
        confidence = Decimal(str(quote['confidence']))
        spread_bps = self.fee_rate_bps + int((1 - confidence) * 500)  # Wider spread if uncertain
        
        # Calculate bid/ask
        half_spread = Decimal(str(spread_bps)) / Decimal('20000')  # Convert bps to price offset
        
        yes_price = mid - half_spread
        no_price = mid + half_spread
        
        return yes_price, no_price
        
    async def place_initial_orders(self, window_id: str, yes_price: Decimal, 
                                  no_price: Decimal) -> Dict[str, Any]:
        """Place initial maker orders for the window"""
        # Use FastRequoteEngine to place orders (with feeRateBps)
        result = await self.requote_engine.execute_requote(
            window_id=window_id,
            new_yes_price=yes_price,
            new_no_price=no_price,
            fee_rate_bps=self.fee_rate_bps
        )
        
        return result
        
    async def handle_price_move(self, symbol: str, bid: Decimal, ask: Decimal, 
                               timestamp_ms: int):
        """Called when WebSocket detects significant price move"""
        if not self.current_window_id or not self.requote_engine.active_orders.get(self.current_window_id):
            return
            
        # Price moved significantly - trigger fast requote
        logger.info(f"💹 Price moved: {symbol} @ {bid}-{ask}")
        
        self.adverse_selection_events += 1
        
        # Recalculate prices based on new market conditions
        yes_price, no_price = self.adjust_prices_for_new_market(bid, ask)
        
        # Execute fast requote (<100ms target)
        await self.requote_engine.execute_requote(
            window_id=self.current_window_id,
            new_yes_price=yes_price,
            new_no_price=no_price,
            fee_rate_bps=self.fee_rate_bps
        )
        
    def adjust_prices_for_new_market(self, new_bid: Decimal, new_ask: Decimal) -> tuple:
        """Adjust bid/ask based on new market conditions"""
        # Simple mid-price adjustment
        mid = (new_bid + new_ask) / 2
        
        # Apply small spread around new mid
        half_spread = Decimal("0.001")  # 0.1% spread
        
        return mid - half_spread, mid + half_spread
        
    async def monitor_and_wait(self, window_id: str, window_info: Dict[str, Any]):
        """Wait for window completion, monitoring for price movements"""
        duration = window_info.get("duration_seconds", 300)
        
        logger.info(f"⏳ Monitoring window for {duration}s...")
        
        # Wait for window close or fills
        timeout = min(duration, 10)  # Give it 10 seconds max
        cancelled = False
        
        try:
            await asyncio.wait_for(
                self.check_order_fills(window_id),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.info(f"⏱️ Window timeout - attempting final requote")
            cancelled = True
            
        # If unfilled, one last requote attempt
        if not cancelled:
            current_prices = self.price_monitor.get_combined_price("BTCUSD")
            if current_prices:
                yes_adj, no_adj = self.adjust_prices_for_new_market(
                    current_prices.get('bid', Decimal("0.8")),
                    current_prices.get('ask', Decimal("0.2"))
                )
                await self.requote_engine.execute_requote(
                    window_id=window_id,
                    new_yes_price=yes_adj,
                    new_no_price=no_adj,
                    fee_rate_bps=self.fee_rate_bps
                )
                
    async def check_order_fills(self, window_id: str):
        """Check if either side of the pair has filled"""
        # TODO: Implement fill checking via Polymarket API
        # Poll orders every 1 second
        pass
        
    async def cleanup_window(self, window_id: str):
        """Clean up after window completes"""
        logger.info(f"🧹 Cleaning up window: {window_id}")
        
        # Cancel any remaining active orders
        active = self.requote_engine.active_orders.get(window_id, {})
        for side, order_id in active.items():
            if order_id:
                try:
                    await self.polly_client.cancel_order(order_id)
                except:
                    pass
                    
        # Update metrics
        self.completed_windows += 1
        
    def get_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive status report"""
        latency_stats = self.requote_engine.get_statistics()
        
        return {
            "running": self.running,
            "current_window": self.current_window_id,
            "metrics": {
                "total_trades": self.total_trades,
                "completed_windows": self.completed_windows,
                "adverse_selection_events": self.adverse_selection_events
            },
            "latency_performance": latency_stats
        }


async def test_integration():
    """Test the integrated market maker"""
    print("=" * 60)
    print("INTEGRATED MARKET MAKER TEST")
    print("=" * 60)
    
    maker = IntegratedPolymakerMaker(fee_rate_bps=10)
    
    try:
        # Initialize
        await maker.initialize()
        print("✅ Initialization complete")
        
        # Get status
        status = maker.get_status_summary()
        print(f"Status: {status}")
        
        print("\nNote: Full testing requires:")
        print("1. Real Polymarket API credentials")
        print("2. Live BTC market data feed")
        print("3. Active trading window available")
        
    finally:
        await maker.stop()


if __name__ == "__main__":
    import asyncio
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(test_integration())

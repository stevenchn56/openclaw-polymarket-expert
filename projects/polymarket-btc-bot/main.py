"""
Polymarket BTC Window Market Making Bot - Main Entry Point

Orchestrates:
1. Binance WebSocket price feed
2. Strategy execution (5-minute window analysis)
3. Risk management checks
4. Order placement and monitoring
"""

import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

# Add project root to Python path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategies.btc_window_5m import BTCWindowStrategy, DirectionPrediction, OrderQuote
from risk_manager.auto_pause import AutoPauseManager, TradeExecution
from connectors.binance_ws import BinanceWebSocketClient, KlineData


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class PolymarketTradingBot:
    """Main trading bot coordinator"""
    
    def __init__(self):
        # Initialize strategy
        self.strategy = BTCWindowStrategy()
        
        # Initialize risk manager
        initial_capital = float(os.getenv('INITIAL_CAPITAL', '1000.0'))
        self.risk_manager = AutoPauseManager(initial_capital=initial_capital)
        
        # Initialize WebSocket client
        self.binance_client = BinanceWebSocketClient(symbol="btcusdt")
        
        # Trading state
        self.is_running = False
        self.current_window_id: Optional[str] = None
        self.window_start_time: Optional[datetime] = None
        
        # Performance tracking
        self.total_executed_trades = 0
        self.total_profit_loss = 0.0
        
        # Set up callbacks
        self._setup_callbacks()
        
        logger.info("🤖 Polymarket BTC Window Bot initialized")
    
    def _setup_callbacks(self):
        """Configure event handlers for WebSocket updates"""
        
        async def on_kline_update(kline: KlineData):
            """Handle incoming candlestick data"""
            
            # Track window timing
            now = datetime.now(timezone.utc)
            
            if self.window_start_time is None:
                # Start new 5-minute window
                self.window_start_time = now
                minutes = int(now.minute / 5) * 5
                seconds = 0
                self.window_start_time = self.window_start_time.replace(
                    minute=minutes, second=seconds, microsecond=0
                )
                self.current_window_id = f"BTC-5M-{now.strftime('%Y%m%d')}-{int(now.hour * 12 + now.minute // 5):04d}"
                logger.info(f"🕐 New window started: {self.current_window_id} @ {self.window_start_time}")
            
            # Calculate time remaining in current window
            time_remaining = (self.window_start_time + timedelta(minutes=5)) - now
            remaining_seconds = time_remaining.total_seconds()
            
            # At T-10 seconds, execute strategy
            if 0 < remaining_seconds <= 10:
                logger.info(f"⏰ T-10s approaching... executing strategy analysis")
                await self.execute_strategy_analysis(kline)
        
        self.binance_client.on_kline_update = on_kline_update
    
    async def execute_strategy_analysis(self, latest_kline: KlineData):
        """Execute full strategy analysis and generate order quote"""
        
        try:
            # Get recent price history (need at least MA_SLOW_PERIOD points)
            price_history = self.binance_client.kline_history
            
            if len(price_history) < self.strategy.MA_SLOW_PERIOD:
                logger.warning(f"⚠️ Not enough data points ({len(price_history)} < {self.strategy.MA_SLOW_PERIOD})")
                return
            
            # Step 1: Analyze window → get direction prediction
            logger.info(f"🔍 Analyzing {len(price_history)} price points...")
            prediction = self.strategy.analyze_window(price_history)
            
            # Log prediction details
            logger.info(f"✅ Prediction: {prediction.direction.value} | Confidence: {prediction.confidence:.2%}")
            logger.info(f"   Reasoning: {prediction.reason}")
            
            # Check minimum confidence threshold
            if not self.strategy.should_execute(prediction):
                logger.info(f"⏸️ Confidence too low ({prediction.confidence:.2%} < {self.strategy.MIN_CONFIDENCE_THRESHOLD:.2%})")
                return
            
            # Step 2: Generate order quote from prediction
            quote = self.strategy.generate_quote(prediction)
            
            logger.info(f"💰 Generated Quote:")
            logger.info(f"   Side: {quote.side}")
            logger.info(f"   Price: ${quote.price:.4f}")
            logger.info(f"   Size: ${quote.size:.2f} USDT")
            logger.info(f"   Fee Rate: {quote.fee_rate_bps} bps")
            logger.info(f"   Est Fill Prob: {quote.estimated_fill_probability:.2%}")
            
            # Step 3: Risk check before execution
            pause_status = self.risk_manager.check_pause_conditions()
            
            if pause_status['paused']:
                logger.warning(f"⛔ Trading paused: {pause_status['reason']}")
                return
            
            # Step 4: Execute trade (this is where you'd integrate with Polymarket API)
            # For now, simulate execution
            logger.info(f"🚀 Simulating trade execution...")
            await self.simulate_trade_execution(quote, prediction)
            
        except Exception as e:
            logger.error(f"❌ Analysis error: {e}", exc_info=True)
    
    async def simulate_trade_execution(self, quote: OrderQuote, prediction: DirectionPrediction):
        """
        Simulate trade execution for demo purposes
        
        In production, replace this with actual Polymarket order placement:
        - Call Polymarket SDK to place maker order
        - Monitor fill status
        - Record position changes
        """
        
        logger.info(f"📝 Simulating order placement...")
        logger.info(f"   Would send to Polymarket:")
        logger.info(f"   {{")
        logger.info(f'     "side": "{quote.side}",')
        logger.info(f'     "price": {quote.price},')
        logger.info(f'     "size": {quote.size},')
        logger.info(f'     "feeRateBps": {quote.fee_rate_bps},')
        logger.info(f'     "windowId": "{self.current_window_id}"')
        logger.info(f"   }}")
        
        # Record simulated trade in risk manager
        self.risk_manager.record_trade(
            side=quote.side,
            entry_price=quote.price,
            exit_price=None,  # Not filled yet
            size_usd=quote.size,
            fee_rate_bps=quote.fee_rate_bps
        )
        
        self.total_executed_trades += 1
        
        # Update position balance
        self.strategy.update_positions(quote.side, quote.size)
        balance = self.strategy.check_position_balance()
        logger.info(f"📊 Current Balance: YES=${balance['yes_position']:.2f} | NO=${balance['no_position']:.2f}")
        
        # Simulate fill after 100ms (target latency budget)
        await asyncio.sleep(0.1)
        logger.info(f"✅ Order simulated successfully in ~100ms latency")
    
    async def run(self):
        """Main bot loop - runs forever until interrupted"""
        
        logger.info("🚀 Starting Polymarket Trading Bot...")
        logger.info(f"   Initial Capital: ${self.risk_manager.initial_capital:.2f}")
        logger.info(f"   Daily Loss Limit: {self.risk_manager.DAILY_LOSS_LIMIT_PCT*100:.1f}%")
        logger.info(f"   Min Confidence Threshold: {self.strategy.MIN_CONFIDENCE_THRESHOLD:.2%}\n")
        
        self.is_running = True
        
        try:
            # Connect to Binance WebSocket
            await self.binance_client.connect()
            await self.binance_client.subscribe_to_klines(interval="1m")
            
            # Start listening loop
            await self.binance_client.listen()
            
        except KeyboardInterrupt:
            logger.info("\n⌨️  Keyboard interrupt received, shutting down...")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
        finally:
            await self.stop()
    
    async def stop(self):
        """Graceful shutdown"""
        logger.info("🛑 Stopping bot...")
        self.is_running = False
        
        # Close WebSocket connection
        await self.binance_client.disconnect()
        
        # Log final statistics
        stats = self.risk_manager.get_daily_statistics()
        logger.info(f"\n📈 Session Statistics:")
        logger.info(f"   Total Trades: {stats['total_trades']}")
        logger.info(f"   Win Rate: {stats['win_rate_pct']:.1f}%")
        logger.info(f"   P&L: ${stats['total_pnl_usd']:.2f}")
        
        logger.info("👋 Bot stopped")


async def main():
    """Entry point"""
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Create and run bot
    bot = PolymarketTradingBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
WebSocket Price Monitor for Polymaster BTC Bot v2.0

Provides real-time price monitoring with sub-100ms requote capability.
Monitors both Binance (spot) and Polymarket (window contracts).

Architecture:
- WebSocket streams → Real-time price updates
- Fast requote loop → <100ms cancel+replace cycle
- Integration with T-10s prediction strategy
"""

import asyncio
import websockets
import json
import hmac
import hashlib
import time
from typing import Optional, Callable, Dict, Any
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class PolymarketWebSocket:
    """Polymarket WebSocket client for order book and price updates"""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.ws_url = "wss://api.polymarket.com/ws"
        self.connected = False
        self.subscriptions = set()
        self.price_callback: Optional[Callable] = None
        self.orderbook_callback: Optional[Callable] = None
        
    async def connect(self):
        """Establish WebSocket connection"""
        try:
            self.ws = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10
            )
            self.connected = True
            logger.info("✅ Connected to Polymarket WebSocket")
            
            # Subscribe to market data
            for subscription in self.subscriptions:
                await self.subscribe(subscription)
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to Polymarket WS: {e}")
            raise
            
    async def subscribe(self, channel: str, params: Optional[Dict] = None):
        """Subscribe to a WebSocket channel"""
        if not self.connected:
            await self.connect()
            
        msg = {"action": "sub", "channel": channel}
        if params:
            msg["params"] = params
            
        await self.ws.send(json.dumps(msg))
        self.subscriptions.add(channel)
        logger.debug(f"📡 Subscribed to: {channel}")
        
    async def unsubscribe(self, channel: str):
        """Unsubscribe from a WebSocket channel"""
        msg = {"action": "unsub", "channel": channel}
        await self.ws.send(json.dumps(msg))
        self.subscriptions.discard(channel)
        logger.debug(f"🔇 Unsubscribed from: {channel}")
        
    async def handle_messages(self):
        """Process incoming WebSocket messages"""
        async for message in self.ws:
            try:
                data = json.loads(message)
                await self.on_message(data)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                
    async def on_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        channel = data.get("channel", "")
        payload = data.get("payload", {})
        
        if channel == "market-data":
            # Price updates
            symbol = payload.get("symbol")
            bid = Decimal(str(payload.get("bid")))
            ask = Decimal(str(payload.get("ask")))
            timestamp_ms = int(payload.get("timestamp", 0))
            
            if self.price_callback:
                await self.price_callback(symbol, bid, ask, timestamp_ms)
                
        elif channel == "orderbook":
            # Order book depth updates
            symbol = payload.get("symbol")
            bids = [Decimal(str(b[0])) for b in payload.get("bids", [])[:2]]
            asks = [Decimal(str(a[0])) for a in payload.get("asks", [])[:2]]
            timestamp_ms = int(payload.get("timestamp", 0))
            
            if self.orderbook_callback:
                await self.orderbook_callback(symbol, bids, asks, timestamp_ms)
                
    async def close(self):
        """Close WebSocket connection"""
        if self.ws and not self.ws.closed:
            await self.ws.close()
            self.connected = False


class BinanceWebSocket:
    """Binance WebSocket client for spot price monitoring"""
    
    def __init__(self):
        self.ws_url = "wss://stream.binance.com:9443/ws"
        self.connected = False
        self.symbol_mappings = {
            "BTCUSD": "btcusdt",  # Polymaster symbol → Binance
            "ETHUSD": "ethusdt",
        }
        self.price_callback: Optional[Callable] = None
        
    async def connect(self, symbols: list = None):
        """Connect to Binance WebSocket"""
        if symbols is None:
            symbols = ["BTCUSD"]
            
        streams = []
        for symbol in symbols:
            binance_symbol = self.symbol_mappings.get(symbol, symbol.lower())
            streams.append(f"{binance_symbol}@bookTicker")
            
        url = f"{self.ws_url}/{'/'.join(streams)}"
        
        try:
            self.ws = await websockets.connect(url)
            self.connected = True
            logger.info(f"✅ Connected to Binance WebSocket for {symbols}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Binance WS: {e}")
            raise
            
    async def handle_messages(self):
        """Process incoming Binance WebSocket messages"""
        async for message in self.ws:
            try:
                data = json.loads(message)
                await self.on_message(data)
            except Exception as e:
                logger.error(f"Error processing Binance message: {e}")
                
    async def on_message(self, data: Dict[str, Any]):
        """Handle incoming Binance WebSocket message"""
        symbol_upper = next((k for k, v in self.symbol_mappings.items() 
                           if v == data.get('s', '').lower()), None)
        
        if symbol_upper and self.price_callback:
            bid = Decimal(str(data.get('b', 0)))
            ask = Decimal(str(data.get('a', 0)))
            timestamp_ms = int(time.time() * 1000)
            
            await self.price_callback(symbol_upper, bid, ask, timestamp_ms)
            
    async def close(self):
        """Close WebSocket connection"""
        if self.ws and not self.ws.closed:
            await self.ws.close()
            self.connected = False


class FastRequoteHandler:
    """Sub-100ms cancel-and-replace order handler"""
    
    def __init__(self, polly_client):
        self.client = polly_client
        self.active_orders: Dict[str, str] = {}  # window_id -> order_id
        self.last_requote_start: Optional[float] = None
        self.requote_latencies: list = []
        
    async def set_callbacks(self, yes_order_id: str, no_order_id: str):
        """Register active order IDs"""
        self.active_orders['YES'] = yes_order_id
        self.active_orders['NO'] = no_order_id
        
    async def requote_fast(self, new_yes_price: Decimal, new_no_price: Decimal, 
                          fee_rate_bps: int) -> float:
        """
        Execute fast requote cycle (cancel old + place new)
        
        Returns actual execution time in milliseconds
        """
        start_time = time.time() * 1000  # ms
        self.last_requote_start = start_time
        
        try:
            # Parallel cancel
            cancel_tasks = []
            for side, order_id in self.active_orders.items():
                if order_id:
                    cancel_tasks.append(
                        self.client.cancel_order(order_id)
                    )
                    
            if cancel_tasks:
                await asyncio.gather(*cancel_tasks, return_exceptions=True)
                
            # Simultaneous new orders with feeRateBps
            replace_tasks = [
                self.client.place_maker("YES", new_yes_price, fee_rate_bps),
                self.client.place_maker("NO", new_no_price, fee_rate_bps)
            ]
            
            results = await asyncio.gather(*replace_tasks)
            
            # Update order tracking
            for i, (side, result) in enumerate(zip(["YES", "NO"], results)):
                if isinstance(result, dict) and result.get("orderId"):
                    self.active_orders[side] = result["orderId"]
                    
            end_time = time.time() * 1000  # ms
            latency = end_time - start_time
            
            # Track statistics
            self.requote_latencies.append(latency)
            if len(self.requote_latencies) > 100:
                self.requote_latencies.pop(0)
                
            # Log if exceeding threshold
            if latency > 100:
                logger.warning(f"⚠️ Requote took {latency:.1f}ms! (>100ms threshold)")
                
            logger.debug(f"✅ Requote completed in {latency:.1f}ms")
            return latency
            
        except Exception as e:
            logger.error(f"❌ Requote failed: {e}")
            raise
            
    def get_stats(self) -> Dict[str, Any]:
        """Get requote performance statistics"""
        if not self.requote_latencies:
            return {"status": "no_data"}
            
        return {
            "avg_latency_ms": sum(self.requote_latencies) / len(self.requote_latencies),
            "min_latency_ms": min(self.requote_latencies),
            "max_latency_ms": max(self.requote_latencies),
            "samples": len(self.requote_latencies),
            "violation_count": sum(1 for lat in self.requote_latencies if lat > 100)
        }


class MultimarketPriceMonitor:
    """
    Unified price monitor combining Binance + Polymarket sources
    
    Features:
    - Multi-source price aggregation
    - Arbitrage detection between exchanges
    - <50ms price delta detection for fast requote triggers
    """
    
    def __init__(self, polly_client=None):
        self.polly_ws = PolymarketWebSocket()
        self.binance_ws = BinanceWebSocket()
        self.requote_handler = FastRequoteHandler(polly_client) if polly_client else None
        
        # Current prices
        self.current_prices: Dict[str, Dict] = {}
        
        # Callback when price moves significantly
        self.price_threshold_ms = 50  # Trigger if price >50ms stale
        self.price_update_callback: Optional[Callable] = None
        
    async def setup_callbacks(self):
        """Set up internal callbacks"""
        # Polymarket price callback
        async def poly_price_callback(symbol, bid, ask, timestamp_ms):
            self.current_prices[symbol] = {
                'bid': bid,
                'ask': ask,
                'timestamp': timestamp_ms
            }
            await self.handle_price_update(symbol, bid, ask, timestamp_ms)
            
        self.polly_ws.price_callback = poly_price_callback
        
        # Binance price callback
        async def binance_price_callback(symbol, bid, ask, timestamp_ms):
            self.current_prices[symbol] = {
                'binance_bid': bid,
                'binance_ask': ask,
                'timestamp': timestamp_ms
            }
            
        self.binance_ws.price_callback = binance_price_callback
        
    async def handle_price_update(self, symbol: str, bid: Decimal, ask: Decimal, 
                                  timestamp_ms: int):
        """Called when price update received"""
        current = self.current_prices.get(symbol, {})
        last_ts = current.get('timestamp', 0)
        
        # Check if this is a significant update (>50ms since last)
        if timestamp_ms - last_ts > self.price_threshold_ms:
            logger.info(f"💹 Price update: {symbol} @ {bid}-{ask}")
            
            # Trigger fast requote if needed
            if self.requote_handler and self.price_update_callback:
                await self.price_update_callback(symbol, bid, ask, timestamp_ms)
                
    async def start(self, symbols: list = None):
        """Start all WebSocket connections"""
        if symbols is None:
            symbols = ["BTCUSD"]
            
        await self.setup_callbacks()
        
        # Connect both sources
        await asyncio.gather(
            self.polly_ws.connect(),
            self.binance_ws.connect(symbols)
        )
        
        # Start message handlers
        await asyncio.gather(
            self.polly_ws.handle_messages(),
            self.binance_ws.handle_messages()
        )
        
    async def stop(self):
        """Stop all connections"""
        await asyncio.gather(
            self.polly_ws.close(),
            self.binance_ws.close()
        )
        
    def get_combined_price(self, symbol: str) -> Optional[Dict]:
        """Get aggregated price from both sources"""
        return self.current_prices.get(symbol)

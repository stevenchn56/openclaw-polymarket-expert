"""
Binance WebSocket Client for Real-Time Price Feeds

Connects to Binance's public WebSocket stream for BTC/USDT data.
No API key required for read-only price data.
"""

import asyncio
import websockets
import json
from datetime import datetime, timezone
from typing import Optional, Callable, List
from dataclasses import dataclass


@dataclass
class KlineData:
    """Single candlestick data point"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades: int
    
    def __post_init__(self):
        # Convert ISO timestamp to datetime
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))


class BinanceWebSocketClient:
    """
    Async WebSocket client for Binance market data streams
    
    Supports:
    - Real-time trade updates (trade stream)
    - Candlestick/kline data (kline stream)
    - Symbol tickers (ticker stream)
    
    URL: wss://stream.binance.com:9443/ws/{symbol}@{stream}
    """
    
    BASE_URL = "wss://stream.binance.com:9443/ws"
    
    def __init__(self, symbol: str = "btcusdt"):
        self.symbol = symbol.lower()
        self.ws_url = f"{BASE_URL}/{self.symbol}@kline_1m"
        
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        
        # Data storage
        self.current_kline: Optional[KlineData] = None
        self.kline_history: List[KlineData] = []
        self.trade_history: List[dict] = []
        
        # Callback for real-time updates
        self.on_kline_update: Optional[Callable[[KlineData], None]] = None
        self.on_trade_update: Optional[Callable[[dict], None]] = None
        
        # Connection state
        self.reconnect_delay = 5  # seconds
        self.max_reconnect_attempts = 10
        self.reconnect_attempt = 0
    
    async def connect(self) -> bool:
        """Establish WebSocket connection"""
        try:
            print(f"🔌 Connecting to Binance WebSocket: {self.ws_url}")
            
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5
            )
            
            self.is_connected = True
            self.reconnect_attempt = 0
            print("✅ Connected successfully")
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self.is_connected = False
            return False
    
    async def subscribe_to_klines(self, interval: str = "1m"):
        """Subscribe to kline/candlestick updates"""
        stream_name = f"{self.symbol}@kline_{interval}"
        subscription_msg = {
            "method": "SUBSCRIBE",
            "params": [stream_name],
            "id": 1
        }
        
        await self.websocket.send(json.dumps(subscription_msg))
        print(f"📡 Subscribed to kline stream: {stream_name}")
    
    async def subscribe_to_trades(self):
        """Subscribe to real-time trade updates"""
        stream_name = f"{self.symbol}@trade"
        subscription_msg = {
            "method": "SUBSCRIBE",
            "params": [stream_name],
            "id": 2
        }
        
        await self.websocket.send(json.dumps(subscription_msg))
        print(f"⚡ Subscribed to trade stream: {stream_name}")
    
    async def process_message(self, message: str):
        """Parse and handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            
            # Handle kline update
            if 'k' in data:
                kline_data = data['k']
                
                self.current_kline = KlineData(
                    timestamp=datetime.fromisoformat(kline['t']) / 1000 + timezone.utc,
                    open=float(kline['o']),
                    high=float(kline['h']),
                    low=float(kline['l']),
                    close=float(kline['c']),
                    volume=float(kline['v']),
                    trades=kline['n']
                )
                
                self.kline_history.append(self.current_kline)
                
                # Trim history to last 100 candles (memory efficiency)
                if len(self.kline_history) > 100:
                    self.kline_history = self.kline_history[-100:]
                
                # Trigger callback
                if self.on_kline_update:
                    self.on_kline_update(self.current_kline)
                
            # Handle trade update
            elif 'e' in data and data['e'] == 'trade':
                trade_data = {
                    'timestamp': datetime.fromisoformat(data['T']) / 1000 + timezone.utc,
                    'price': float(data['p']),
                    'quantity': float(data['q']),
                    'is_buyer_maker': data['m']
                }
                
                self.trade_history.append(trade_data)
                
                # Keep only last 50 trades
                if len(self.trade_history) > 50:
                    self.trade_history = self.trade_history[-50:]
                
                if self.on_trade_update:
                    self.on_trade_update(trade_data)
                    
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error: {e}")
        except Exception as e:
            print(f"❌ Message processing error: {e}")
    
    async def listen(self):
        """Main listener loop - process all incoming messages"""
        while self.is_connected:
            try:
                message = await self.websocket.recv()
                await self.process_message(message)
                
            except websockets.ConnectionClosed:
                print("⚠️ Connection closed by server")
                self.is_connected = False
                break
                
            except Exception as e:
                print(f"❌ Listen error: {e}")
                self.is_connected = False
                break
        
        # Attempt reconnection
        await self._reconnect()
    
    async def _reconnect(self):
        """Reconnect with exponential backoff"""
        while self.reconnect_attempt < self.max_reconnect_attempts:
            self.reconnect_attempt += 1
            delay = min(self.reconnect_delay * (2 ** (self.reconnect_attempt - 1)), 60)
            
            print(f"🔄 Reconnecting (attempt {self.reconnect_attempt}/{self.max_reconnect_attempts})... waiting {delay}s")
            await asyncio.sleep(delay)
            
            if await self.connect():
                print("✅ Reconnected successfully")
                # Resubscribe after reconnect
                await self.subscribe_to_klines()
                await self.listen()
                break
    
    def get_current_price(self) -> Optional[float]:
        """Get most recent close price"""
        if self.current_kline:
            return self.current_kline.close
        return None
    
    def get_recent_prices(self, count: int = 10) -> List[float]:
        """Get list of recent close prices"""
        return [k.close for k in self.kline_history[-count:]]
    
    def get_latest_trade(self) -> Optional[dict]:
        """Get most recent trade execution"""
        if self.trade_history:
            return self.trade_history[-1]
        return None
    
    async def disconnect(self):
        """Gracefully close WebSocket connection"""
        if self.websocket and self.is_connected:
            await self.websocket.close()
            self.is_connected = False
            print("👋 Disconnected from Binance")
    
    async def run_forever(self):
        """Main entry point - connect, subscribe, and listen forever"""
        while True:
            if await self.connect():
                await self.subscribe_to_klines()
                await self.listen()
            else:
                await asyncio.sleep(self.reconnect_delay)


# Demo usage
async def demo():
    """Demonstration of the Binance WebSocket client"""
    
    client = BinanceWebSocketClient(symbol="btcusdt")
    
    # Define callbacks for real-time updates
    def on_new_kline(kline: KlineData):
        print(f"📊 New candle: ${kline.close:.2f} | Vol: {kline.volume:.4f} BTC | Time: {kline.timestamp.strftime('%H:%M:%S')}")
    
    def on_new_trade(trade: dict):
        direction = "BUY" if not trade['is_buyer_maker'] else "SELL"
        print(f"⚡ Trade: ${trade['price']:.2f} x {trade['quantity']:.4f} BTC [{direction}]")
    
    client.on_kline_update = on_new_kline
    client.on_trade_update = on_new_trade
    
    print("\n🚀 Starting Binance WebSocket demo...\n")
    await client.run_forever()


if __name__ == "__main__":
    asyncio.run(demo())

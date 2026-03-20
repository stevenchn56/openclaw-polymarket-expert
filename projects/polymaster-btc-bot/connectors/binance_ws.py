"""Binance WebSocket connector for real-time BTC price feeds"""

import asyncio
import websockets
import json
from typing import Optional, Callable
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class BinanceWebSocket:
    """
    Binance WebSocket Client
    
    Connects to Binance stream API to receive real-time BTC/USDT
    trade data for price updates.
    """
    
    def __init__(
        self,
        symbol: str = "btcusdt",
        on_price_update: Optional[Callable[[Decimal], None]] = None
    ):
        """
        Initialize Binance WebSocket connector
        
        Args:
            symbol: Trading pair (default: btcusdt)
            on_price_update: Callback function when price updates arrive
        """
        self.symbol = symbol.lower()
        self.on_price_update = on_price_update
        
        # Stream URL from Binance docs
        self.ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@trade"
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        
        # Price history for analysis
        self.last_price: Optional[Decimal] = None
        self.price_history = []
        self.max_history_size = 100
        
        logger.info(f"BinanceWebSocket initialized for {symbol.upper()}/USDT")
    
    async def connect(self) -> None:
        """Establish WebSocket connection"""
        if self.is_running:
            logger.warning("WebSocket already running")
            return
        
        self.is_running = True
        logger.info(f"Connecting to {self.ws_url}...")
        
        try:
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=30,
                ping_timeout=10
            )
            
            self.reconnect_attempts = 0
            logger.info("WebSocket connected successfully!")
            await self._run_connection()
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.is_running = False
            
            if self.reconnect_attempts < self.max_reconnect_attempts:
                self.reconnect_attempts += 1
                logger.info(f"Will reconnect in {self.reconnect_delay}s (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
                await asyncio.sleep(self.reconnect_delay)
                await self.connect()
            else:
                logger.critical("Max reconnection attempts reached")
    
    async def _run_connection(self) -> None:
        """Process incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                if not self.is_running:
                    break
                    
                await self._handle_message(message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.is_running = False
            
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self.is_running = False
        
        # Trigger reconnection
        if self.is_running:
            await self.connect()
    
    async def _handle_message(self, message: str) -> None:
        """
        Process incoming trade message
        
        Args:
            message: Raw JSON message from Binance
        """
        try:
            data = json.loads(message)
            
            # Extract price and quantity
            if 'p' in data and 'q' in data:  # Standard trade format
                price = Decimal(data['p'])
                quantity = Decimal(data['q'])
                timestamp = data.get('T', 0)
                
                # Update last price
                self.last_price = price
                
                # Add to history
                self._add_to_history(price, timestamp)
                
                # Notify callback if provided
                if self.on_price_update:
                    self.on_price_update(price)
                
                # Debug logging every 100 trades
                if len(self.price_history) % 100 == 0:
                    logger.debug(f"Price update: ${price:.2f}, Vol: ${quantity*price:.2f}")
                    
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON: {message[:100]}")
        except Exception as e:
            logger.error(f"Message handling error: {e}")
    
    def _add_to_history(self, price: Decimal, timestamp: int) -> None:
        """Add price to history with size limit"""
        self.price_history.append({
            'price': price,
            'timestamp': timestamp
        })
        
        # Keep only recent prices
        if len(self.price_history) > self.max_history_size:
            self.price_history.pop(0)
    
    async def disconnect(self) -> None:
        """Close WebSocket connection"""
        self.is_running = False
        
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
            logger.info("WebSocket disconnected")
    
    def get_current_price(self) -> Optional[Decimal]:
        """Get the latest known price"""
        return self.last_price
    
    def get_average_price(self, window: int = 10) -> Optional[Decimal]:
        """Calculate average price over recent window"""
        if len(self.price_history) < window:
            return None
        
        recent_prices = [p['price'] for p in self.price_history[-window:]]
        total = sum(recent_prices)
        return total / len(recent_prices)
    
    def get_price_volatility(self) -> float:
        """Calculate price volatility (std dev of returns)"""
        if len(self.price_history) < 10:
            return 0.0
        
        prices = [p['price'] for p in self.price_history[-50:]]
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            ret = float(prices[i] - prices[i-1]) / float(prices[i-1])
            returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Standard deviation
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        
        return variance ** 0.5
    
    def get_statistics(self) -> dict:
        """Get current statistics"""
        return {
            'connected': self.is_running,
            'reconnect_attempts': self.reconnect_attempts,
            'last_price': str(self.last_price) if self.last_price else None,
            'history_size': len(self.price_history),
            'avg_price_10': str(self.get_average_price(10)) if self.get_average_price(10) else None,
            'volatility': f"{self.get_price_volatility():.6f}"
        }


# Example usage with callback
async def main():
    """Test the Binance WebSocket connector"""
    
    def price_callback(price: Decimal):
        """Handle price updates"""
        print(f"[{len(price_history)}] New price: ${price:.2f}")
    
    ws = BinanceWebSocket(
        symbol='btcusdt',
        on_price_update=price_callback
    )
    
    # Start connection
    await ws.connect()
    
    # Let it run for a bit
    await asyncio.sleep(30)
    
    # Get statistics
    print("\nStatistics:")
    print(json.dumps(ws.get_statistics(), indent=2))
    
    # Cleanup
    await ws.disconnect()


if __name__ == "__main__":
    import json
    
    print("Starting Binance WebSocket Test...")
    print("=" * 60)
    
    price_history = []
    
    def on_price_update(price: Decimal):
        price_history.append(price)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"\nError: {e}")
    
    print(f"\nReceived {len(price_history)} price updates")

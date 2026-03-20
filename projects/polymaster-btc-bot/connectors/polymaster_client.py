"""Polymaster API client for order management"""

import os
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class PolymasterClient:
    """
    Polymaster API Client
    
    Handles communication with the Polymaster trading platform.
    Includes order submission, cancellation, and status checking.
    """
    
    def __init__(self, api_key: str, wallet_address: str):
        """
        Initialize the Polymaster client
        
        Args:
            api_key: API key from Polymaster dashboard
            wallet_address: Connected wallet address
        """
        self.api_key = api_key
        self.wallet_address = wallet_address
        self.base_url = "https://polymaster.ai/api/v1"
        
        # Session management
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = RateLimiter()
        
        logger.info(f"PolymasterClient initialized for {wallet_address[:8]}...")
    
    async def initialize(self) -> None:
        """Create HTTP session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("HTTP session created")
    
    async def close(self) -> None:
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("HTTP session closed")
    
    async def submit_order(
        self,
        market_id: str,
        side: str,
        amount: Decimal,
        price: Decimal
    ) -> Dict[str, Any]:
        """
        Submit a new order to Polymaster
        
        Args:
            market_id: Market identifier
            side: 'BUY' or 'SELL'
            amount: Quantity in shares
            price: Price per share
            
        Returns:
            Order submission response
            
        Raises:
            ConnectionError: If API call fails
            ValueError: If parameters are invalid
        """
        if not self.session:
            await self.initialize()
        
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}/orders"
        payload = {
            "market_id": market_id,
            "side": side.upper(),
            "amount": str(amount),
            "price": str(price),
            "wallet_address": self.wallet_address
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"Order submitted successfully: {result}")
                    return result
                else:
                    error_text = await resp.text()
                    logger.error(f"Order failed: {resp.status} - {error_text}")
                    raise ConnectionError(f"API error: {resp.status}")
                    
        except asyncio.TimeoutError:
            logger.error("API request timed out")
            raise ConnectionError("Request timeout")
        except Exception as e:
            logger.error(f"Failed to submit order: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order
        
        Args:
            order_id: Order identifier
            
        Returns:
            True if cancellation successful
        """
        if not self.session:
            await self.initialize()
        
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}/orders/{order_id}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            async with self.session.delete(url, headers=headers) as resp:
                if resp.status in (200, 204):
                    logger.info(f"Order {order_id} cancelled successfully")
                    return True
                else:
                    error_text = await resp.text()
                    logger.warning(f"Cancellation failed: {resp.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Cancel order error: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of an existing order
        
        Args:
            order_id: Order identifier
            
        Returns:
            Order status data or None if not found
        """
        if not self.session:
            await self.initialize()
        
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}/orders/{order_id}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.debug(f"Order status check: {resp.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Get order status error: {e}")
            return None
    
    async def get_market_info(self, market_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific market
        
        Args:
            market_id: Market identifier
            
        Returns:
            Market data or None if not found
        """
        if not self.session:
            await self.initialize()
        
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}/markets/{market_id}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Get market info error: {e}")
            return None


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, requests_per_second: int = 5):
        self.requests_per_second = requests_per_second
        self.last_request_time = 0
    
    async def acquire(self) -> None:
        """Wait until rate limit allows next request"""
        now = asyncio.get_event_loop().time()
        min_interval = 1.0 / self.requests_per_second
        
        if now - self.last_request_time < min_interval:
            wait_time = min_interval - (now - self.last_request_time)
            await asyncio.sleep(wait_time)
        
        self.last_request_time = asyncio.get_event_loop().time()


# Example usage
if __name__ == "__main__":
    async def test_client():
        """Test the Polymaster client"""
        api_key = os.getenv('POLYMARKET_API_KEY', 'test_key')
        wallet_addr = '0xTestAddress1234567890abcdef1234567890'
        
        client = PolymasterClient(api_key, wallet_addr)
        
        try:
            await client.initialize()
            
            # Test order submission (will fail without real credentials)
            print("Testing order submission...")
            result = await client.submit_order(
                market_id="test_market",
                side="BUY",
                amount=Decimal("10"),
                price=Decimal("0.50")
            )
            print(f"Result: {result}")
            
        except Exception as e:
            print(f"Expected error (no real credentials): {type(e).__name__}")
        
        finally:
            await client.close()
    
    asyncio.run(test_client())

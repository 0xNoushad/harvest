"""
Crypto Price Service

Fetches price data for ANY cryptocurrency by name or address.
Supports both CoinGecko (for all cryptos) and Jupiter (for Solana tokens).
"""

import asyncio
import logging
import aiohttp
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    """Price data for a cryptocurrency."""
    name: str
    symbol: str
    price: float
    change_24h: Optional[float] = None
    market_cap: Optional[float] = None
    source: str = "CoinGecko"
    source_url: str = ""
    contract_address: Optional[str] = None
    trade_url: Optional[str] = None
    explorer_url: Optional[str] = None


class PriceService:
    """Service for fetching cryptocurrency prices."""
    
    @staticmethod
    def is_solana_address(address: str) -> bool:
        """
        Check if string looks like a Solana address.
        
        Args:
            address: String to check
        
        Returns:
            True if it looks like a Solana address
        """
        # Solana addresses are base58 encoded, 32-44 characters
        if not address:
            return False
        
        clean = address.strip()
        return (
            len(clean) >= 32 and 
            len(clean) <= 44 and 
            clean.replace(" ", "").isalnum()
        )
    
    @staticmethod
    async def fetch_by_address(address: str) -> Optional[PriceData]:
        """
        Fetch price for a Solana token by contract address.
        
        Args:
            address: Solana token contract address
        
        Returns:
            PriceData if found, None otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://price.jup.ag/v4/price?ids={address}"
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.error(f"Jupiter API returned status {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "data" not in data or address not in data["data"]:
                        logger.warning(f"No price data found for address {address}")
                        return None
                    
                    price_data = data["data"][address]
                    price = price_data.get("price", 0)
                    
                    if price == 0:
                        return None
                    
                    return PriceData(
                        name="Unknown Token",
                        symbol="TOKEN",
                        price=price,
                        source="Jupiter",
                        source_url="https://jup.ag",
                        contract_address=address,
                        trade_url=f"https://jup.ag/swap/SOL-{address}",
                        explorer_url=f"https://solscan.io/token/{address}"
                    )
        
        except asyncio.TimeoutError:
            logger.error("Jupiter API request timed out")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching price by address: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching price by address: {e}")
            return None
    
    @staticmethod
    async def fetch_by_name(query: str) -> Optional[PriceData]:
        """
        Fetch price for any cryptocurrency by name or symbol.
        
        Args:
            query: Token name or symbol (e.g., "bitcoin", "BTC", "solana")
        
        Returns:
            PriceData if found, None otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Search for the token
                search_url = f"https://api.coingecko.com/api/v3/search?query={query}"
                
                async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.error(f"CoinGecko search API returned status {response.status}")
                        return None
                    
                    search_data = await response.json()
                    
                    # Get first matching coin
                    coins = search_data.get("coins", [])
                    if not coins:
                        logger.warning(f"No coins found for query: {query}")
                        return None
                    
                    # Use the first result (most relevant)
                    coin = coins[0]
                    coin_id = coin["id"]
                    coin_name = coin["name"]
                    coin_symbol = coin["symbol"].upper()
                    
                    # Get detailed price data
                    price_url = (
                        f"https://api.coingecko.com/api/v3/simple/price"
                        f"?ids={coin_id}"
                        f"&vs_currencies=usd"
                        f"&include_24hr_change=true"
                        f"&include_market_cap=true"
                    )
                    
                    async with session.get(price_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status != 200:
                            logger.error(f"CoinGecko price API returned status {response.status}")
                            return None
                        
                        price_data = await response.json()
                        
                        if coin_id not in price_data:
                            logger.warning(f"No price data found for coin_id: {coin_id}")
                            return None
                        
                        data = price_data[coin_id]
                        price = data.get("usd", 0)
                        change_24h = data.get("usd_24h_change")
                        market_cap = data.get("usd_market_cap")
                        
                        if price == 0:
                            return None
                        
                        return PriceData(
                            name=coin_name,
                            symbol=coin_symbol,
                            price=price,
                            change_24h=change_24h,
                            market_cap=market_cap,
                            source="CoinGecko",
                            source_url=f"https://www.coingecko.com/en/coins/{coin_id}"
                        )
        
        except asyncio.TimeoutError:
            logger.error("CoinGecko API request timed out")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching price by name: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching price by name: {e}")
            return None
    
    @staticmethod
    async def fetch_price(query: str) -> Optional[PriceData]:
        """
        Fetch price for any cryptocurrency.
        
        Automatically detects if query is a Solana address or token name/symbol.
        
        Args:
            query: Token name, symbol, or Solana contract address
        
        Returns:
            PriceData if found, None otherwise
        """
        # Validate and sanitize input
        from agent.security.security import SecurityValidator
        try:
            query = SecurityValidator.sanitize_string(query.strip(), max_length=100)
        except ValueError as e:
            logger.error(f"Invalid query input: {e}")
            return None
        
        # Check if it's a Solana address
        if PriceService.is_solana_address(query):
            logger.info(f"Detected Solana address: {query}")
            return await PriceService.fetch_by_address(query)
        
        # Otherwise search by name/symbol
        logger.info(f"Searching for token: {query}")
        return await PriceService.fetch_by_name(query)
    
    @staticmethod
    def format_price(price: float) -> str:
        """
        Format price with appropriate decimal places.
        
        Args:
            price: Price in USD
        
        Returns:
            Formatted price string
        """
        if price >= 1:
            return f"${price:,.2f}"
        elif price >= 0.01:
            return f"${price:.4f}"
        elif price >= 0.0001:
            return f"${price:.6f}"
        else:
            return f"${price:.8f}"
    
    @staticmethod
    def format_market_cap(market_cap: float) -> str:
        """
        Format market cap with B/M/K suffixes.
        
        Args:
            market_cap: Market cap in USD
        
        Returns:
            Formatted market cap string
        """
        if market_cap >= 1_000_000_000:
            return f"${market_cap/1_000_000_000:.2f}B"
        elif market_cap >= 1_000_000:
            return f"${market_cap/1_000_000:.2f}M"
        elif market_cap >= 1_000:
            return f"${market_cap/1_000:.2f}K"
        else:
            return f"${market_cap:,.0f}"
    
    @staticmethod
    def format_change(change: float) -> str:
        """
        Format 24h price change with indicator.
        
        Args:
            change: 24h change percentage
        
        Returns:
            Formatted change string with indicator
        """
        indicator = "↑" if change > 0 else "↓"
        return f"{indicator} {change:+.2f}%"
    
    @staticmethod
    def format_message(price_data: PriceData) -> str:
        """
        Format price data into a clean message.
        
        Args:
            price_data: PriceData object
        
        Returns:
            Formatted message string
        """
        # Basic info
        message = f"**{price_data.name}"
        if price_data.symbol != "TOKEN":
            message += f" ({price_data.symbol})"
        message += "**\n\n"
        
        # Price
        message += f"**Current Price:** {PriceService.format_price(price_data.price)}\n"
        
        # 24h change (if available)
        if price_data.change_24h is not None:
            message += f"**24h Change:** {PriceService.format_change(price_data.change_24h)}\n"
        
        # Market cap (if available)
        if price_data.market_cap is not None:
            message += f"**Market Cap:** {PriceService.format_market_cap(price_data.market_cap)}\n"
        
        # Contract address (if Solana token)
        if price_data.contract_address:
            message += f"\n**Contract:**\n`{price_data.contract_address}`\n"
        
        # Links
        message += "\n**Links:**\n"
        
        if price_data.trade_url:
            message += f"• [Trade on Jupiter]({price_data.trade_url})\n"
        
        if price_data.explorer_url:
            message += f"• [View on Solscan]({price_data.explorer_url})\n"
        
        if price_data.source_url:
            message += f"• [View on {price_data.source}]({price_data.source_url})\n"
        
        # Source attribution
        message += f"\n**Source:** {price_data.source} API"
        
        return message


# Example usage
if __name__ == "__main__":
    async def test():
        # Test with token name
        print("Testing with 'bitcoin'...")
        btc = await PriceService.fetch_price("bitcoin")
        if btc:
            print(PriceService.format_message(btc))
        
        print("\n" + "="*50 + "\n")
        
        # Test with Solana address (BONK)
        print("Testing with BONK address...")
        bonk = await PriceService.fetch_price("DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263")
        if bonk:
            print(PriceService.format_message(bonk))
    
    asyncio.run(test())

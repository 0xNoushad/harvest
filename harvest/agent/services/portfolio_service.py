"""
Portfolio Analysis Service

Analyzes any Solana wallet and provides detailed portfolio information:
- Token holdings with current prices
- Total portfolio value
- Wallet activity stats
- Top holdings breakdown
"""

import asyncio
import logging
import aiohttp
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TokenHolding:
    """Represents a token holding in a wallet."""
    symbol: str
    name: str
    amount: float
    decimals: int
    price_usd: float
    value_usd: float
    mint_address: str
    percentage: float = 0.0


@dataclass
class PortfolioData:
    """Complete portfolio analysis data."""
    wallet_address: str
    sol_balance: float
    sol_value_usd: float
    total_value_usd: float
    token_count: int
    holdings: List[TokenHolding]
    top_holdings: List[TokenHolding]
    last_updated: datetime


class PortfolioService:
    """Service for analyzing Solana wallet portfolios."""
    
    # Try to get Helius key from environment, fallback to public RPC
    @staticmethod
    def get_rpc_url() -> str:
        """Get RPC URL with API key if available."""
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        # Try multiple Helius keys
        for i in range(1, 4):
            key = os.getenv(f"HELIUS_API_KEY_{i}") or os.getenv("HELIUS_API_KEY")
            if key:
                return f"https://mainnet.helius-rpc.com/?api-key={key}"
        
        # Fallback to public RPC
        return "https://api.mainnet-beta.solana.com"
    
    @staticmethod
    async def get_sol_balance(wallet_address: str) -> Optional[float]:
        """
        Get SOL balance for a wallet.
        
        Args:
            wallet_address: Solana wallet address
        
        Returns:
            SOL balance or None if error
        """
        # Validate wallet address
        from agent.security.security import SecurityValidator
        try:
            wallet_address = SecurityValidator.validate_wallet_address(wallet_address)
        except ValueError as e:
            logger.error(f"Invalid wallet address: {e}")
            return None
        
        try:
            rpc_url = PortfolioService.get_rpc_url()
            async with aiohttp.ClientSession() as session:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getBalance",
                    "params": [wallet_address]
                }
                
                async with session.post(
                    rpc_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        logger.error(f"RPC returned status {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "result" in data and "value" in data["result"]:
                        # Convert lamports to SOL
                        return data["result"]["value"] / 1_000_000_000
                    
                    return None
        
        except asyncio.TimeoutError:
            logger.error("Timeout fetching SOL balance")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching SOL balance: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching SOL balance: {e}")
            return None
    
    @staticmethod
    async def get_token_accounts(wallet_address: str) -> Optional[List[Dict]]:
        """
        Get all token accounts for a wallet.
        
        Args:
            wallet_address: Solana wallet address
        
        Returns:
            List of token accounts or None if error
        """
        # Validate wallet address
        from agent.security.security import SecurityValidator
        try:
            wallet_address = SecurityValidator.validate_wallet_address(wallet_address)
        except ValueError as e:
            logger.error(f"Invalid wallet address: {e}")
            return None
        
        try:
            rpc_url = PortfolioService.get_rpc_url()
            async with aiohttp.ClientSession() as session:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTokenAccountsByOwner",
                    "params": [
                        wallet_address,
                        {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                        {"encoding": "jsonParsed"}
                    ]
                }
                
                async with session.post(
                    rpc_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status != 200:
                        logger.error(f"RPC returned status {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "result" in data and "value" in data["result"]:
                        return data["result"]["value"]
                    
                    return None
        
        except asyncio.TimeoutError:
            logger.error("Timeout fetching token accounts")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching token accounts: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching token accounts: {e}")
            return None
    
    @staticmethod
    async def get_token_metadata(mint_addresses: List[str]) -> Dict[str, Dict]:
        """
        Get metadata for multiple tokens from Jupiter.
        
        Args:
            mint_addresses: List of token mint addresses
        
        Returns:
            Dict mapping mint address to metadata
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Get token list from Jupiter
                url = "https://token.jup.ag/all"
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.error(f"Jupiter API returned status {response.status}")
                        return {}
                    
                    tokens = await response.json()
                    
                    # Create lookup dict
                    metadata = {}
                    for token in tokens:
                        if token.get("address") in mint_addresses:
                            metadata[token["address"]] = {
                                "symbol": token.get("symbol", "UNKNOWN"),
                                "name": token.get("name", "Unknown Token"),
                                "decimals": token.get("decimals", 9)
                            }
                    
                    return metadata
        
        except asyncio.TimeoutError:
            logger.error("Timeout fetching token metadata")
            return {}
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching token metadata: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error fetching token metadata: {e}")
            return {}
    
    @staticmethod
    async def get_token_prices(mint_addresses: List[str]) -> Dict[str, float]:
        """
        Get current prices for multiple tokens.
        
        Args:
            mint_addresses: List of token mint addresses
        
        Returns:
            Dict mapping mint address to price in USD
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Jupiter price API supports multiple tokens
                ids = ",".join(mint_addresses)
                url = f"https://price.jup.ag/v4/price?ids={ids}"
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.error(f"Jupiter price API returned status {response.status}")
                        return {}
                    
                    data = await response.json()
                    
                    prices = {}
                    if "data" in data:
                        for mint, price_data in data["data"].items():
                            prices[mint] = price_data.get("price", 0)
                    
                    return prices
        
        except asyncio.TimeoutError:
            logger.error("Timeout fetching token prices")
            return {}
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching token prices: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error fetching token prices: {e}")
            return {}
    
    @staticmethod
    async def get_sol_price() -> float:
        """
        Get current SOL price in USD.
        
        Returns:
            SOL price or 0 if error
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.error(f"CoinGecko API returned status {response.status}")
                        return 0
                    
                    data = await response.json()
                    return data.get("solana", {}).get("usd", 0)
        
        except asyncio.TimeoutError:
            logger.error("Timeout fetching SOL price")
            return 0
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching SOL price: {e}")
            return 0
        except Exception as e:
            logger.error(f"Error fetching SOL price: {e}")
            return 0
    
    @staticmethod
    async def analyze_portfolio(wallet_address: str) -> Optional[PortfolioData]:
        """
        Analyze a Solana wallet's complete portfolio.
        
        Args:
            wallet_address: Solana wallet address
        
        Returns:
            PortfolioData with complete analysis or None if error
        """
        # Validate wallet address
        from agent.security.security import SecurityValidator
        try:
            wallet_address = SecurityValidator.validate_wallet_address(wallet_address)
        except ValueError as e:
            logger.error(f"Invalid wallet address: {e}")
            return None
        
        try:
            # Get SOL balance
            sol_balance = await PortfolioService.get_sol_balance(wallet_address)
            if sol_balance is None:
                logger.error("Failed to fetch SOL balance")
                return None
            
            # Get SOL price
            sol_price = await PortfolioService.get_sol_price()
            sol_value = sol_balance * sol_price
            
            # Get token accounts
            token_accounts = await PortfolioService.get_token_accounts(wallet_address)
            if token_accounts is None:
                logger.error("Failed to fetch token accounts")
                return None
            
            # Filter out zero balance tokens
            non_zero_accounts = []
            mint_addresses = []
            
            for account in token_accounts:
                try:
                    parsed = account["account"]["data"]["parsed"]["info"]
                    amount = float(parsed["tokenAmount"]["uiAmount"])
                    
                    if amount > 0:
                        non_zero_accounts.append(account)
                        mint_addresses.append(parsed["mint"])
                except Exception as e:
                    logger.warning(f"Error parsing token account: {e}")
                    continue
            
            # Get metadata and prices for all tokens
            metadata = await PortfolioService.get_token_metadata(mint_addresses)
            prices = await PortfolioService.get_token_prices(mint_addresses)
            
            # Build holdings list
            holdings = []
            total_token_value = 0
            
            for account in non_zero_accounts:
                try:
                    parsed = account["account"]["data"]["parsed"]["info"]
                    mint = parsed["mint"]
                    amount = float(parsed["tokenAmount"]["uiAmount"])
                    decimals = parsed["tokenAmount"]["decimals"]
                    
                    # Get metadata
                    meta = metadata.get(mint, {})
                    symbol = meta.get("symbol", "UNKNOWN")
                    name = meta.get("name", "Unknown Token")
                    
                    # Get price
                    price = prices.get(mint, 0)
                    value = amount * price
                    total_token_value += value
                    
                    holding = TokenHolding(
                        symbol=symbol,
                        name=name,
                        amount=amount,
                        decimals=decimals,
                        price_usd=price,
                        value_usd=value,
                        mint_address=mint
                    )
                    
                    holdings.append(holding)
                
                except Exception as e:
                    logger.warning(f"Error processing token holding: {e}")
                    continue
            
            # Sort by value
            holdings.sort(key=lambda x: x.value_usd, reverse=True)
            
            # Calculate total portfolio value
            total_value = sol_value + total_token_value
            
            # Calculate percentages
            for holding in holdings:
                if total_value > 0:
                    holding.percentage = (holding.value_usd / total_value) * 100
            
            # Get top 5 holdings
            top_holdings = holdings[:5]
            
            return PortfolioData(
                wallet_address=wallet_address,
                sol_balance=sol_balance,
                sol_value_usd=sol_value,
                total_value_usd=total_value,
                token_count=len(holdings),
                holdings=holdings,
                top_holdings=top_holdings,
                last_updated=datetime.now()
            )
        
        except Exception as e:
            logger.error(f"Error analyzing portfolio: {e}")
            return None
    
    @staticmethod
    def format_portfolio_message(portfolio: PortfolioData) -> str:
        """
        Format portfolio data into a clean message.
        
        Args:
            portfolio: PortfolioData object
        
        Returns:
            Formatted message string
        """
        message = f"**Portfolio Analysis**\n\n"
        
        # Wallet info
        message += f"**Wallet:** `{portfolio.wallet_address[:8]}...{portfolio.wallet_address[-8:]}`\n"
        message += f"**Total Value:** ${portfolio.total_value_usd:,.2f}\n"
        message += f"**Tokens Held:** {portfolio.token_count}\n\n"
        
        # SOL balance
        sol_percentage = (portfolio.sol_value_usd / portfolio.total_value_usd * 100) if portfolio.total_value_usd > 0 else 0
        message += f"**SOL Balance:**\n"
        message += f"• Amount: {portfolio.sol_balance:.4f} SOL\n"
        message += f"• Value: ${portfolio.sol_value_usd:,.2f} ({sol_percentage:.1f}%)\n\n"
        
        # Top holdings
        if portfolio.top_holdings:
            message += f"**Top Holdings:**\n"
            for i, holding in enumerate(portfolio.top_holdings, 1):
                message += f"\n{i}. **{holding.symbol}**\n"
                message += f"   • Amount: {holding.amount:,.4f}\n"
                message += f"   • Value: ${holding.value_usd:,.2f} ({holding.percentage:.1f}%)\n"
                message += f"   • Price: ${holding.price_usd:.6f}\n"
        
        # Links
        message += f"\n**Links:**\n"
        message += f"• [View on Solscan](https://solscan.io/account/{portfolio.wallet_address})\n"
        message += f"• [View on Solana Explorer](https://explorer.solana.com/address/{portfolio.wallet_address})\n"
        
        # Source
        message += f"\n**Source:** Helius RPC + Jupiter Price API"
        
        return message
    
    @staticmethod
    def format_summary_message(portfolio: PortfolioData) -> str:
        """
        Format a brief portfolio summary.
        
        Args:
            portfolio: PortfolioData object
        
        Returns:
            Brief summary message
        """
        message = f"**Portfolio Summary**\n\n"
        message += f"**Total Value:** ${portfolio.total_value_usd:,.2f}\n"
        message += f"**SOL:** {portfolio.sol_balance:.4f} (${portfolio.sol_value_usd:,.2f})\n"
        message += f"**Tokens:** {portfolio.token_count} different tokens\n\n"
        
        if portfolio.top_holdings:
            top = portfolio.top_holdings[0]
            message += f"**Largest Holding:** {top.symbol} (${top.value_usd:,.2f})\n"
        
        return message


# Example usage
if __name__ == "__main__":
    async def test():
        # Test with a wallet address
        wallet = "YOUR_WALLET_ADDRESS_HERE"
        
        print(f"Analyzing portfolio for {wallet}...\n")
        
        portfolio = await PortfolioService.analyze_portfolio(wallet)
        
        if portfolio:
            print(PortfolioService.format_portfolio_message(portfolio))
        else:
            print("Failed to analyze portfolio")
    
    asyncio.run(test())

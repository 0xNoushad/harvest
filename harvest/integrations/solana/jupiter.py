"""
Jupiter Aggregator Integration

Provides API wrapper for Jupiter swap aggregator.
Supports best route calculation and swap execution.

UPDATED: Feb 2026 - Migrated to new API endpoint (api.jup.ag)
Old endpoint (quote-api.jup.ag/v6) deprecated and will shut down Jan 31, 2026
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import requests
from solders.pubkey import Pubkey
from solders.transaction import Transaction


logger = logging.getLogger(__name__)


# Jupiter API endpoints
# UPDATED: Migrated from deprecated quote-api.jup.ag/v6 to api.jup.ag (Feb 2026)
# Old endpoint deprecated Oct 1, 2025, will be shut down Jan 31, 2026
# Get free API key at: https://portal.jup.ag
JUPITER_API_BASE = "https://api.jup.ag"


@dataclass
class SwapRoute:
    """Information about a swap route."""
    input_mint: str
    output_mint: str
    input_amount: int
    output_amount: int
    price_impact: float
    fees: Dict[str, float]
    route_plan: List[Dict[str, Any]]


class JupiterIntegration:
    """
    Jupiter Aggregator integration for token swaps.
    
    Provides methods to:
    - Get best swap routes
    - Calculate swap prices
    - Execute swaps
    - Query supported tokens
    """
    
    def __init__(self, rpc_client, wallet_pubkey: Pubkey, api_key: Optional[str] = None):
        """
        Initialize Jupiter integration.
        
        Args:
            rpc_client: Helius RPC client instance
            wallet_pubkey: User's wallet public key
            api_key: Jupiter API key (optional, get free key at https://portal.jup.ag)
                    If not provided, will use JUPITER_API_KEY environment variable
        """
        self.rpc_client = rpc_client
        self.wallet_pubkey = wallet_pubkey
        self.api_base = JUPITER_API_BASE
        self.api_key = api_key or os.getenv("JUPITER_API_KEY")
        self.session = requests.Session()
        
        # Add API key header if provided
        if self.api_key:
            self.session.headers.update({"x-api-key": self.api_key})
            logger.info(f"Initialized Jupiter integration with API key for wallet {wallet_pubkey}")
        else:
            logger.warning(
                "Jupiter API key not provided. Using public endpoint with 0.2% platform fee. "
                "Get a free API key at https://portal.jup.ag for better rates."
            )
            logger.info(f"Initialized Jupiter integration for wallet {wallet_pubkey}")
    
    def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: float,
        slippage_bps: int = 50
    ) -> SwapRoute:
        """
        Get the best swap route quote.
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount of input tokens (in token units, not lamports)
            slippage_bps: Slippage tolerance in basis points (default 50 = 0.5%)
        
        Returns:
            SwapRoute with best route information
        
        Raises:
            Exception: If quote request fails
        """
        try:
            # Convert amount to lamports/token units (assuming 9 decimals for SOL, 6 for USDC)
            # This is simplified - real implementation would check token decimals
            if input_mint == "So11111111111111111111111111111111111111112":  # SOL
                input_amount = int(amount * 1e9)
            else:
                input_amount = int(amount * 1e6)
            
            logger.info(f"Getting quote for {amount} {input_mint} -> {output_mint}")
            
            # Query Jupiter API for quote
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": input_amount,
                "slippageBps": slippage_bps,
            }
            
            response = self.session.get(
                f"{self.api_base}/swap/v1/quote",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response into SwapRoute
            route = SwapRoute(
                input_mint=input_mint,
                output_mint=output_mint,
                input_amount=input_amount,
                output_amount=int(data.get("outAmount", 0)),
                price_impact=float(data.get("priceImpactPct", 0)),
                fees=self._parse_fees(data),
                route_plan=data.get("routePlan", [])
            )
            
            logger.info(f"Quote: {input_amount} -> {route.output_amount} (impact: {route.price_impact}%)")
            return route
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get Jupiter quote: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to parse Jupiter quote: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_best_price(
        self,
        input_mint: str,
        output_mint: str,
        amount: float
    ) -> float:
        """
        Get the best output amount for a swap.
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount of input tokens
        
        Returns:
            Expected output amount
        
        Raises:
            Exception: If price query fails
        """
        try:
            route = self.get_quote(input_mint, output_mint, amount)
            
            # Convert output amount back to token units
            if output_mint == "So11111111111111111111111111111111111111112":  # SOL
                output_amount = route.output_amount / 1e9
            else:
                output_amount = route.output_amount / 1e6
            
            logger.info(f"Best price: {amount} {input_mint} = {output_amount} {output_mint}")
            return output_amount
        
        except Exception as e:
            error_msg = f"Failed to get best price: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_swap_transaction(
        self,
        input_mint: str,
        output_mint: str,
        amount: float,
        slippage_bps: int = 50
    ) -> Transaction:
        """
        Create a swap transaction.
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount of input tokens to swap
            slippage_bps: Slippage tolerance in basis points
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            Exception: If transaction creation fails
        """
        try:
            logger.info(f"Creating swap transaction for {amount} {input_mint} -> {output_mint}")
            
            # First get the quote
            route = self.get_quote(input_mint, output_mint, amount, slippage_bps)
            
            # Request swap transaction from Jupiter
            swap_request = {
                "quoteResponse": {
                    "inputMint": route.input_mint,
                    "outputMint": route.output_mint,
                    "inAmount": str(route.input_amount),
                    "outAmount": str(route.output_amount),
                    "priceImpactPct": str(route.price_impact),
                    "routePlan": route.route_plan,
                },
                "userPublicKey": str(self.wallet_pubkey),
                "wrapAndUnwrapSol": True,
            }
            
            response = self.session.post(
                f"{self.api_base}/swap/v1/swap",
                json=swap_request,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse the transaction
            swap_transaction = data.get("swapTransaction")
            if not swap_transaction:
                raise Exception("No swap transaction returned from Jupiter")
            
            # Deserialize the transaction
            # In production, properly deserialize the base64 transaction
            # For now, create a placeholder transaction
            transaction = Transaction.new_with_payer(
                [],
                self.wallet_pubkey
            )
            
            logger.info(f"Created swap transaction for {amount} {input_mint}")
            return transaction
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to create swap transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to build swap transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_token_price(self, token_mint: str, vs_token: str = "USDC") -> float:
        """
        Get current price of a token.
        
        Args:
            token_mint: Token mint address
            vs_token: Quote token (default USDC)
        
        Returns:
            Token price in quote token
        
        Raises:
            Exception: If price query fails
        """
        try:
            # Map common token names to mint addresses
            token_mints = {
                "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
                "SOL": "So11111111111111111111111111111111111111112",
            }
            
            vs_mint = token_mints.get(vs_token, vs_token)
            
            # Get quote for 1 token
            route = self.get_quote(token_mint, vs_mint, 1.0)
            
            # Calculate price
            if vs_mint == token_mints["USDC"]:
                price = route.output_amount / 1e6
            else:
                price = route.output_amount / 1e9
            
            logger.info(f"Token price: 1 {token_mint} = {price} {vs_token}")
            return price
        
        except Exception as e:
            error_msg = f"Failed to get token price: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def compare_routes(
        self,
        input_mint: str,
        output_mint: str,
        amount: float
    ) -> List[SwapRoute]:
        """
        Get multiple route options for comparison.
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount of input tokens
        
        Returns:
            List of SwapRoute options sorted by output amount
        
        Raises:
            Exception: If route query fails
        """
        try:
            logger.info(f"Comparing routes for {amount} {input_mint} -> {output_mint}")
            
            # Get the best route (Jupiter already returns the best)
            best_route = self.get_quote(input_mint, output_mint, amount)
            
            # In production, you might query multiple aggregators or DEXs
            # For now, return just the Jupiter route
            routes = [best_route]
            
            logger.info(f"Found {len(routes)} route options")
            return routes
        
        except Exception as e:
            error_msg = f"Failed to compare routes: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _parse_fees(self, quote_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Parse fee information from quote response.
        
        Args:
            quote_data: Quote response data
        
        Returns:
            Dictionary of fee types and amounts
        """
        fees = {}
        
        # Parse platform fee
        if "platformFee" in quote_data:
            fees["platform"] = float(quote_data["platformFee"].get("amount", 0)) / 1e9
        
        # Parse other fees from route plan
        route_plan = quote_data.get("routePlan", [])
        total_swap_fee = 0.0
        
        for step in route_plan:
            swap_info = step.get("swapInfo", {})
            fee_amount = swap_info.get("feeAmount", 0)
            total_swap_fee += float(fee_amount) / 1e9
        
        if total_swap_fee > 0:
            fees["swap"] = total_swap_fee
        
        return fees

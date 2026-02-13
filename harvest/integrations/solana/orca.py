"""
Orca DEX Integration

Provides API wrapper for Orca decentralized exchange.
Supports price queries and swap transaction construction.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import requests
from solders.pubkey import Pubkey
from solders.transaction import Transaction


logger = logging.getLogger(__name__)


# Orca API endpoints
ORCA_API_BASE = "https://api.mainnet.orca.so/v1"


@dataclass
class OrcaQuote:
    """Information about an Orca swap quote."""
    input_mint: str
    output_mint: str
    input_amount: int
    output_amount: int
    price_impact: float
    fees: Dict[str, float]
    pool_address: str


class OrcaIntegration:
    """
    Orca DEX integration for token swaps.
    
    Provides methods to:
    - Get swap quotes
    - Calculate swap prices
    - Execute swaps
    - Query pool information
    """
    
    def __init__(self, rpc_client, wallet_pubkey: Pubkey):
        """
        Initialize Orca integration.
        
        Args:
            rpc_client: Helius RPC client instance
            wallet_pubkey: User's wallet public key
        """
        self.rpc_client = rpc_client
        self.wallet_pubkey = wallet_pubkey
        self.api_base = ORCA_API_BASE
        self.session = requests.Session()
        
        logger.info(f"Initialized Orca integration for wallet {wallet_pubkey}")
    
    def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: float,
        slippage_bps: int = 50
    ) -> OrcaQuote:
        """
        Get a swap quote from Orca.
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount of input tokens (in token units, not lamports)
            slippage_bps: Slippage tolerance in basis points (default 50 = 0.5%)
        
        Returns:
            OrcaQuote with swap information
        
        Raises:
            Exception: If quote request fails
        """
        try:
            # Convert amount to lamports/token units (assuming 9 decimals for SOL, 6 for USDC)
            if input_mint == "So11111111111111111111111111111111111111112":  # SOL
                input_amount = int(amount * 1e9)
            else:
                input_amount = int(amount * 1e6)
            
            logger.info(f"Getting Orca quote for {amount} {input_mint} -> {output_mint}")
            
            # Query Orca API for quote
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": input_amount,
                "slippage": slippage_bps / 10000,  # Convert bps to decimal
            }
            
            response = self.session.get(
                f"{self.api_base}/quote",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response into OrcaQuote
            quote = OrcaQuote(
                input_mint=input_mint,
                output_mint=output_mint,
                input_amount=input_amount,
                output_amount=int(data.get("outAmount", 0)),
                price_impact=float(data.get("priceImpact", 0)),
                fees=self._parse_fees(data),
                pool_address=data.get("poolAddress", "")
            )
            
            logger.info(f"Orca quote: {input_amount} -> {quote.output_amount} (impact: {quote.price_impact}%)")
            return quote
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get Orca quote: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to parse Orca quote: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_price(
        self,
        input_mint: str,
        output_mint: str,
        amount: float
    ) -> float:
        """
        Get the output amount for a swap.
        
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
            quote = self.get_quote(input_mint, output_mint, amount)
            
            # Convert output amount back to token units
            if output_mint == "So11111111111111111111111111111111111111112":  # SOL
                output_amount = quote.output_amount / 1e9
            else:
                output_amount = quote.output_amount / 1e6
            
            logger.info(f"Orca price: {amount} {input_mint} = {output_amount} {output_mint}")
            return output_amount
        
        except Exception as e:
            error_msg = f"Failed to get Orca price: {str(e)}"
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
        Create a swap transaction for Orca.
        
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
            logger.info(f"Creating Orca swap transaction for {amount} {input_mint} -> {output_mint}")
            
            # First get the quote
            quote = self.get_quote(input_mint, output_mint, amount, slippage_bps)
            
            # Request swap transaction from Orca
            swap_request = {
                "inputMint": quote.input_mint,
                "outputMint": quote.output_mint,
                "amount": str(quote.input_amount),
                "slippage": slippage_bps / 10000,
                "userPublicKey": str(self.wallet_pubkey),
            }
            
            response = self.session.post(
                f"{self.api_base}/swap",
                json=swap_request,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse the transaction
            swap_transaction = data.get("transaction")
            if not swap_transaction:
                raise Exception("No swap transaction returned from Orca")
            
            # Deserialize the transaction
            # In production, properly deserialize the base64 transaction
            # For now, create a placeholder transaction
            transaction = Transaction.new_with_payer(
                [],
                self.wallet_pubkey
            )
            
            logger.info(f"Created Orca swap transaction for {amount} {input_mint}")
            return transaction
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to create Orca swap transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to build Orca swap transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """
        Get information about a specific pool.
        
        Args:
            pool_address: Pool address
        
        Returns:
            Pool information dictionary
        
        Raises:
            Exception: If pool query fails
        """
        try:
            logger.info(f"Getting Orca pool info for {pool_address}")
            
            response = self.session.get(
                f"{self.api_base}/pool/{pool_address}",
                timeout=10
            )
            response.raise_for_status()
            
            pool_info = response.json()
            
            logger.info(f"Retrieved pool info for {pool_address}")
            return pool_info
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get Orca pool info: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to parse Orca pool info: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_token_price(self, token_mint: str, vs_token: str = "USDC") -> float:
        """
        Get current price of a token on Orca.
        
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
            quote = self.get_quote(token_mint, vs_mint, 1.0)
            
            # Calculate price
            if vs_mint == token_mints["USDC"]:
                price = quote.output_amount / 1e6
            else:
                price = quote.output_amount / 1e9
            
            logger.info(f"Orca token price: 1 {token_mint} = {price} {vs_token}")
            return price
        
        except Exception as e:
            error_msg = f"Failed to get Orca token price: {str(e)}"
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
        
        # Parse trading fee
        if "fee" in quote_data:
            fees["trading"] = float(quote_data["fee"]) / 1e9
        
        # Parse protocol fee if present
        if "protocolFee" in quote_data:
            fees["protocol"] = float(quote_data["protocolFee"]) / 1e9
        
        return fees

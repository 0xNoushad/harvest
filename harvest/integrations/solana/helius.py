"""
Helius RPC Client Integration

Provides a wrapper for the Helius RPC API with authentication handling.
"""

import os
import logging
from typing import Optional, Dict, Any
import requests
from solders.rpc.requests import GetBalance, GetAccountInfo
from solders.rpc.responses import GetBalanceResp, GetAccountInfoResp
from solders.pubkey import Pubkey


logger = logging.getLogger(__name__)


class HeliusClient:
    """
    Helius RPC client wrapper with authentication handling.
    
    Provides enhanced RPC functionality through Helius API including:
    - Standard Solana RPC methods
    - Enhanced transaction history
    - Webhook support
    - NFT metadata
    """
    
    def __init__(self, api_key: Optional[str] = None, network: str = "devnet"):
        """
        Initialize Helius RPC client.
        
        Args:
            api_key: Helius API key (defaults to HELIUS_API_KEY env var)
            network: Network to connect to ("devnet" or "mainnet-beta")
        
        Raises:
            ValueError: If API key is not provided
        """
        self.api_key = api_key or os.getenv("HELIUS_API_KEY")
        if not self.api_key:
            raise ValueError("Helius API key is required. Set HELIUS_API_KEY environment variable.")
        
        self.network = network
        self.base_url = f"https://rpc.helius.xyz/?api-key={self.api_key}"
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
        
        logger.info(f"Initialized Helius client for {network}")
    
    def get_rpc_url(self) -> str:
        """
        Get the full RPC URL with authentication.
        
        Returns:
            Full RPC URL including API key
        """
        return self.base_url
    
    def rpc_call(self, method: str, params: list = None) -> Dict[str, Any]:
        """
        Make a JSON-RPC call to Helius.
        
        Args:
            method: RPC method name
            params: Method parameters
        
        Returns:
            RPC response as dictionary
        
        Raises:
            Exception: If RPC call fails
        """
        if params is None:
            params = []
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        try:
            response = self.session.post(self.base_url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if "error" in result:
                error_msg = result["error"].get("message", "Unknown error")
                logger.error(f"RPC error for {method}: {error_msg}")
                raise Exception(f"RPC call failed: {error_msg}")
            
            return result.get("result", {})
        
        except requests.exceptions.Timeout:
            logger.error(f"RPC call timeout for {method}")
            raise Exception(f"RPC call timeout for {method}")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"RPC call failed for {method}: {str(e)}")
            raise Exception(f"RPC call failed: {str(e)}")
    
    def get_balance(self, pubkey: str) -> float:
        """
        Get SOL balance for a public key.
        
        Args:
            pubkey: Public key as string
        
        Returns:
            Balance in SOL
        """
        try:
            result = self.rpc_call("getBalance", [pubkey])
            lamports = result.get("value", 0)
            return lamports / 1e9  # Convert lamports to SOL
        except Exception as e:
            logger.error(f"Failed to get balance for {pubkey}: {str(e)}")
            raise
    
    def get_token_balance(self, token_account: str) -> float:
        """
        Get SPL token balance for a token account.
        
        Args:
            token_account: Token account public key as string
        
        Returns:
            Token balance
        """
        try:
            result = self.rpc_call("getTokenAccountBalance", [token_account])
            amount = result.get("value", {}).get("uiAmount", 0)
            return float(amount)
        except Exception as e:
            logger.error(f"Failed to get token balance for {token_account}: {str(e)}")
            raise
    
    def get_account_info(self, pubkey: str) -> Optional[Dict[str, Any]]:
        """
        Get account information.
        
        Args:
            pubkey: Public key as string
        
        Returns:
            Account info dictionary or None if account doesn't exist
        """
        try:
            result = self.rpc_call("getAccountInfo", [pubkey, {"encoding": "jsonParsed"}])
            return result.get("value")
        except Exception as e:
            logger.error(f"Failed to get account info for {pubkey}: {str(e)}")
            raise
    
    def get_transaction(self, signature: str) -> Optional[Dict[str, Any]]:
        """
        Get transaction details by signature.
        
        Args:
            signature: Transaction signature
        
        Returns:
            Transaction details or None if not found
        """
        try:
            result = self.rpc_call("getTransaction", [signature, {"encoding": "jsonParsed"}])
            return result
        except Exception as e:
            logger.error(f"Failed to get transaction {signature}: {str(e)}")
            raise
    
    def send_transaction(self, signed_transaction: str) -> str:
        """
        Send a signed transaction.
        
        Args:
            signed_transaction: Base64 encoded signed transaction
        
        Returns:
            Transaction signature
        """
        try:
            result = self.rpc_call("sendTransaction", [signed_transaction])
            return result
        except Exception as e:
            logger.error(f"Failed to send transaction: {str(e)}")
            raise
    
    def get_latest_blockhash(self) -> Dict[str, Any]:
        """
        Get the latest blockhash.
        
        Returns:
            Blockhash information
        """
        try:
            result = self.rpc_call("getLatestBlockhash")
            return result.get("value", {})
        except Exception as e:
            logger.error(f"Failed to get latest blockhash: {str(e)}")
            raise
    
    def simulate_transaction(self, transaction: str) -> Dict[str, Any]:
        """
        Simulate a transaction without sending it.
        
        Args:
            transaction: Base64 encoded transaction
        
        Returns:
            Simulation result
        """
        try:
            result = self.rpc_call("simulateTransaction", [transaction])
            return result.get("value", {})
        except Exception as e:
            logger.error(f"Failed to simulate transaction: {str(e)}")
            raise

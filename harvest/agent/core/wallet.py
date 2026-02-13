"""Wallet management for Harvest - sign & send transactions on Solana."""

import os
import asyncio
import logging
from typing import Callable, TypeVar
from solders.keypair import Keypair

logger = logging.getLogger(__name__)
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts

T = TypeVar('T')


class WalletManager:
    """
    Manages Solana wallet for Harvest agent.
    
    Features:
    - Load wallet from private key
    - Get balance
    - Sign & send transactions
    - Airdrop devnet SOL (for testing)
    - Retry logic with exponential backoff for network failures
    """
    
    def __init__(
        self,
        private_key: str | None = None,
        network: str = "devnet",
        rpc_url: str | None = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ):
        """
        Initialize wallet manager.
        
        Args:
            private_key: Base58 encoded private key (or load from env)
            network: "devnet" or "mainnet-beta"
            rpc_url: Custom RPC URL (or use default)
            max_retries: Maximum number of retry attempts for network operations
            base_delay: Base delay in seconds for exponential backoff
        """
        # Load private key
        if private_key is None:
            private_key = os.getenv("WALLET_PRIVATE_KEY", "")
        
        if not private_key:
            logger.warning("No wallet private key provided - creating ephemeral wallet")
            self.keypair = Keypair()
        else:
            # Parse private key (supports base58 or JSON array format)
            self.keypair = self._load_keypair(private_key)
        
        self.public_key = self.keypair.pubkey()
        self.max_retries = max_retries
        self.base_delay = base_delay
        
        # Set up RPC client
        if rpc_url is None:
            if network == "devnet":
                rpc_url = "https://api.devnet.solana.com"
            elif network == "mainnet-beta":
                helius_key = os.getenv("HELIUS_API_KEY")
                if helius_key:
                    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
                else:
                    rpc_url = "https://api.mainnet-beta.solana.com"
            else:
                raise ValueError(f"Unknown network: {network}")
        
        self.rpc_url = rpc_url
        self.client = AsyncClient(rpc_url)
        self.network = network
        
        logger.info(f"Wallet initialized: {self.public_key}")
        logger.info(f"Network: {network}")
        logger.info(f"RPC: {rpc_url}")
    
    async def _retry_with_backoff(self, func: Callable[[], T], operation_name: str = "operation") -> T:
        """
        Retry an async function with exponential backoff.
        
        Args:
            func: Async function to retry
            operation_name: Name of operation for logging
        
        Returns:
            Result of the function
        
        Raises:
            Exception: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await func()
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(
                        f"{operation_name} failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"{operation_name} failed after {self.max_retries} attempts: {e}"
                    )
        
        raise last_exception
    
    def _load_keypair(self, private_key: str) -> Keypair:
        """Load keypair from private key string."""
        try:
            # Try base58 format first
            return Keypair.from_base58_string(private_key)
        except Exception:
            try:
                # Try JSON array format [1,2,3,...]
                import json
                secret_bytes = bytes(json.loads(private_key))
                return Keypair.from_bytes(secret_bytes)
            except Exception as e:
                raise ValueError(f"Invalid private key format: {e}")
    
    async def get_balance(self) -> float:
        """Get wallet balance in SOL with retry logic."""
        async def _get_balance():
            response = await self.client.get_balance(self.public_key)
            lamports = response.value
            sol = lamports / 1_000_000_000
            return sol
        
        try:
            return await self._retry_with_backoff(_get_balance, "Get balance")
        except Exception as e:
            logger.error(f"Failed to get balance after retries: {e}")
            return 0.0
    
    async def get_token_balance(self, token_mint: str) -> float:
        """
        Get balance for specific SPL token with retry logic.
        
        Args:
            token_mint: Token mint address
        
        Returns:
            Token balance
        """
        async def _get_token_balance():
            from solders.pubkey import Pubkey as SoldersPubkey
            mint_pubkey = SoldersPubkey.from_string(token_mint)
            
            # Get token accounts for this wallet
            response = await self.client.get_token_accounts_by_owner(
                self.public_key,
                {"mint": mint_pubkey}
            )
            
            if not response.value:
                return 0.0
            
            # Parse token account data
            account_info = response.value[0].account
            # Token account data layout: first 64 bytes contain amount
            import struct
            amount = struct.unpack('<Q', account_info.data[:8])[0]
            
            # Get token decimals
            mint_info = await self.client.get_account_info(mint_pubkey)
            decimals = mint_info.value.data[44]  # Decimals at byte 44
            
            return amount / (10 ** decimals)
        
        try:
            return await self._retry_with_backoff(_get_token_balance, f"Get token balance for {token_mint}")
        except Exception as e:
            logger.error(f"Failed to get token balance: {e}")
            return 0.0
    
    async def airdrop(self, amount: float = 1.0) -> bool:
        """
        Request airdrop (devnet only).
        
        Args:
            amount: Amount in SOL
        
        Returns:
            True if successful
        """
        if self.network != "devnet":
            logger.error("Airdrops only available on devnet")
            return False
        
        try:
            lamports = int(amount * 1_000_000_000)
            response = await self.client.request_airdrop(self.public_key, lamports)
            signature = response.value
            
            # Wait for confirmation
            await self.client.confirm_transaction(signature, commitment=Confirmed)
            
            logger.info(f"Airdrop successful: {amount} SOL")
            return True
        except Exception as e:
            logger.error(f"Airdrop failed: {e}")
            return False
    
    async def send_sol(self, to: str | Pubkey, amount: float) -> str | None:
        """
        Send SOL to another address with retry logic.
        
        Args:
            to: Recipient address
            amount: Amount in SOL
        
        Returns:
            Transaction signature or None if failed
        """
        async def _send_sol():
            # Convert to Pubkey if string
            to_pubkey = Pubkey.from_string(to) if isinstance(to, str) else to
            
            # Get recent blockhash
            blockhash_resp = await self.client.get_latest_blockhash()
            recent_blockhash = blockhash_resp.value.blockhash
            
            # Create transfer instruction
            lamports = int(amount * 1_000_000_000)
            transfer_ix = transfer(
                TransferParams(
                    from_pubkey=self.public_key,
                    to_pubkey=to_pubkey,
                    lamports=lamports,
                )
            )
            
            # Create and sign transaction
            tx = Transaction.new_with_payer(
                instructions=[transfer_ix],
                payer=self.public_key,
            )
            tx.sign([self.keypair], recent_blockhash)
            
            # Send transaction
            opts = TxOpts(skip_preflight=False, preflight_commitment=Confirmed)
            response = await self.client.send_transaction(tx, opts=opts)
            signature = str(response.value)
            
            # Wait for confirmation
            await self.client.confirm_transaction(signature, commitment=Confirmed)
            
            logger.info(f"Sent {amount} SOL to {to}")
            logger.info(f"Signature: {signature}")
            
            return signature
        
        try:
            return await self._retry_with_backoff(_send_sol, f"Send {amount} SOL")
        except Exception as e:
            logger.error(f"Failed to send SOL after retries: {e}")
            return None
    
    async def sign_and_send(self, transaction: Transaction) -> str | None:
        """
        Sign and send a transaction with retry logic.
        
        Args:
            transaction: Transaction to sign and send
        
        Returns:
            Transaction signature or None if failed
        """
        async def _sign_and_send():
            # Get recent blockhash
            blockhash_resp = await self.client.get_latest_blockhash()
            recent_blockhash = blockhash_resp.value.blockhash
            
            # Sign transaction
            transaction.sign([self.keypair], recent_blockhash)
            
            # Send transaction
            opts = TxOpts(skip_preflight=False, preflight_commitment=Confirmed)
            response = await self.client.send_transaction(transaction, opts=opts)
            signature = str(response.value)
            
            # Wait for confirmation
            await self.client.confirm_transaction(signature, commitment=Confirmed)
            
            logger.info(f"Transaction confirmed: {signature}")
            return signature
        
        try:
            return await self._retry_with_backoff(_sign_and_send, "Sign and send transaction")
        except Exception as e:
            logger.error(f"Transaction failed after retries: {e}")
            return None
    
    def sign_transaction(self, transaction: Transaction) -> Transaction:
        """
        Sign a transaction without sending it.
        
        Args:
            transaction: Transaction to sign
        
        Returns:
            Signed transaction
        """
        # Note: This is a synchronous method as it doesn't require network access
        # The actual blockhash should be set before calling this
        transaction.sign([self.keypair], transaction.recent_blockhash)
        return transaction
    
    def get_public_key(self) -> str:
        """Return wallet's public key as string."""
        return str(self.public_key)
    
    async def close(self):
        """Close RPC client connection."""
        await self.client.close()
    
    def __str__(self) -> str:
        return f"WalletManager({self.public_key})"


async def main():
    """Test wallet functionality."""
    print("🌾 Testing Harvest Wallet\n")
    
    # Create wallet
    wallet = WalletManager(network="devnet")
    print(f"Wallet: {wallet.public_key}")
    
    # Get balance
    balance = await wallet.get_balance()
    print(f"Balance: {balance} SOL")
    
    # Request airdrop if balance is low
    if balance < 0.1:
        print("\nRequesting airdrop...")
        success = await wallet.airdrop(1.0)
        if success:
            balance = await wallet.get_balance()
            print(f"New balance: {balance} SOL")
    
    # Close connection
    await wallet.close()
    print("\n✅ Wallet test complete")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

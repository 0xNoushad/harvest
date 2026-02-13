"""
MarginFi Protocol Integration

Provides API wrapper for MarginFi lending and borrowing protocol.
Supports account creation, deposits, withdrawals, and lending interactions.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.instruction import Instruction, AccountMeta


logger = logging.getLogger(__name__)


# MarginFi program ID
MARGINFI_PROGRAM_ID = Pubkey.from_string("MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA")


@dataclass
class MarginfiPool:
    """Information about a MarginFi lending pool."""
    address: str
    token_mint: str
    name: str
    supply_apy: float
    borrow_apy: float
    total_deposits: float
    total_borrows: float


class MarginFiIntegration:
    """
    MarginFi Protocol integration for lending and borrowing.
    
    Provides methods to:
    - Initialize user account
    - Deposit tokens for lending
    - Withdraw deposited tokens
    - Query pool information
    - Interact with protocol for airdrop farming
    """
    
    def __init__(self, rpc_client, wallet_pubkey: Pubkey):
        """
        Initialize MarginFi integration.
        
        Args:
            rpc_client: Helius RPC client instance
            wallet_pubkey: User's wallet public key
        """
        self.rpc_client = rpc_client
        self.wallet_pubkey = wallet_pubkey
        self.program_id = MARGINFI_PROGRAM_ID
        
        logger.info(f"Initialized MarginFi integration for wallet {wallet_pubkey}")
    
    def has_account(self) -> bool:
        """
        Check if user has a MarginFi account.
        
        Returns:
            True if account exists, False otherwise
        
        Raises:
            Exception: If account check fails
        """
        try:
            logger.info("Checking for MarginFi account")
            
            # Derive user account PDA
            user_account = self._derive_user_account()
            
            # Check if account exists
            account_info = self.rpc_client.get_account_info(str(user_account))
            exists = account_info is not None
            
            logger.info(f"MarginFi account exists: {exists}")
            return exists
        
        except Exception as e:
            error_msg = f"Failed to check MarginFi account: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_pools(self) -> List[MarginfiPool]:
        """
        Get list of available MarginFi lending pools.
        
        Returns:
            List of MarginfiPool objects
        
        Raises:
            Exception: If pool query fails
        """
        try:
            logger.info("Querying MarginFi pools")
            
            # In production, query on-chain pool accounts
            # For now, return mock data for common pools
            pools = [
                MarginfiPool(
                    address="MPool1111111111111111111111111111111111111",
                    token_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                    name="USDC Pool",
                    supply_apy=8.5,
                    borrow_apy=12.0,
                    total_deposits=10000000.0,
                    total_borrows=7000000.0
                ),
                MarginfiPool(
                    address="MPool2222222222222222222222222222222222222",
                    token_mint="So11111111111111111111111111111111111111112",  # SOL
                    name="SOL Pool",
                    supply_apy=6.2,
                    borrow_apy=9.5,
                    total_deposits=50000.0,
                    total_borrows=30000.0
                ),
                MarginfiPool(
                    address="MPool3333333333333333333333333333333333333",
                    token_mint="Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
                    name="USDT Pool",
                    supply_apy=8.0,
                    borrow_apy=11.5,
                    total_deposits=5000000.0,
                    total_borrows=3500000.0
                ),
            ]
            
            logger.info(f"Found {len(pools)} MarginFi pools")
            return pools
        
        except Exception as e:
            error_msg = f"Failed to get MarginFi pools: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_pool_by_token(self, token_mint: str) -> Optional[MarginfiPool]:
        """
        Get pool information for a specific token.
        
        Args:
            token_mint: Token mint address
        
        Returns:
            MarginfiPool or None if not found
        
        Raises:
            Exception: If pool query fails
        """
        try:
            pools = self.get_pools()
            pool = next((p for p in pools if p.token_mint == token_mint), None)
            
            if pool:
                logger.info(f"Found pool for token {token_mint}: {pool.name}")
            else:
                logger.warning(f"No pool found for token {token_mint}")
            
            return pool
        
        except Exception as e:
            error_msg = f"Failed to get pool by token: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_initialize_account_transaction(self) -> Transaction:
        """
        Create a transaction to initialize a MarginFi user account.
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            Exception: If transaction creation fails
        """
        try:
            logger.info("Creating MarginFi account initialization transaction")
            
            # Derive user account PDA
            user_account = self._derive_user_account()
            
            # Create initialize instruction
            instruction = self._create_initialize_instruction(user_account)
            
            # Get recent blockhash
            blockhash_info = self.rpc_client.get_latest_blockhash()
            recent_blockhash = blockhash_info.get("blockhash")
            
            # Create transaction
            transaction = Transaction.new_with_payer(
                [instruction],
                self.wallet_pubkey
            )
            
            logger.info("Created MarginFi account initialization transaction")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create initialize transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_deposit_transaction(self, token_mint: str, amount: float) -> Transaction:
        """
        Create a transaction to deposit tokens into MarginFi.
        
        Args:
            token_mint: Token mint address
            amount: Amount of tokens to deposit
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            Exception: If transaction creation fails
        """
        try:
            if amount <= 0:
                raise ValueError("Deposit amount must be positive")
            
            logger.info(f"Creating MarginFi deposit transaction for {amount} tokens")
            
            # Get pool for this token
            pool = self.get_pool_by_token(token_mint)
            if not pool:
                raise ValueError(f"No pool found for token {token_mint}")
            
            pool_pubkey = Pubkey.from_string(pool.address)
            
            # Convert amount to token units
            # Assuming 6 decimals for USDC/USDT, 9 for SOL
            if token_mint == "So11111111111111111111111111111111111111112":
                token_amount = int(amount * 1e9)
            else:
                token_amount = int(amount * 1e6)
            
            # Derive user account
            user_account = self._derive_user_account()
            
            # Create deposit instruction
            instruction = self._create_deposit_instruction(
                user_account,
                pool_pubkey,
                token_amount
            )
            
            # Get recent blockhash
            blockhash_info = self.rpc_client.get_latest_blockhash()
            recent_blockhash = blockhash_info.get("blockhash")
            
            # Create transaction
            transaction = Transaction.new_with_payer(
                [instruction],
                self.wallet_pubkey
            )
            
            logger.info(f"Created MarginFi deposit transaction for {amount} tokens")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create deposit transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_withdraw_transaction(self, token_mint: str, amount: float) -> Transaction:
        """
        Create a transaction to withdraw tokens from MarginFi.
        
        Args:
            token_mint: Token mint address
            amount: Amount of tokens to withdraw
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            Exception: If transaction creation fails
        """
        try:
            if amount <= 0:
                raise ValueError("Withdraw amount must be positive")
            
            logger.info(f"Creating MarginFi withdraw transaction for {amount} tokens")
            
            # Get pool for this token
            pool = self.get_pool_by_token(token_mint)
            if not pool:
                raise ValueError(f"No pool found for token {token_mint}")
            
            pool_pubkey = Pubkey.from_string(pool.address)
            
            # Convert amount to token units
            if token_mint == "So11111111111111111111111111111111111111112":
                token_amount = int(amount * 1e9)
            else:
                token_amount = int(amount * 1e6)
            
            # Derive user account
            user_account = self._derive_user_account()
            
            # Create withdraw instruction
            instruction = self._create_withdraw_instruction(
                user_account,
                pool_pubkey,
                token_amount
            )
            
            # Get recent blockhash
            blockhash_info = self.rpc_client.get_latest_blockhash()
            recent_blockhash = blockhash_info.get("blockhash")
            
            # Create transaction
            transaction = Transaction.new_with_payer(
                [instruction],
                self.wallet_pubkey
            )
            
            logger.info(f"Created MarginFi withdraw transaction for {amount} tokens")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create withdraw transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_interaction_transaction(self) -> Transaction:
        """
        Create a small interaction transaction for airdrop farming.
        
        This creates a minimal transaction to interact with MarginFi protocol
        for the purpose of qualifying for potential airdrops.
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            Exception: If transaction creation fails
        """
        try:
            logger.info("Creating MarginFi interaction transaction for airdrop farming")
            
            # For airdrop farming, do a small deposit
            # Use USDC with minimal amount (0.01 USDC)
            usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            amount = 0.01
            
            transaction = self.create_deposit_transaction(usdc_mint, amount)
            
            logger.info("Created MarginFi interaction transaction")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create interaction transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_user_deposits(self) -> Dict[str, float]:
        """
        Get user's deposits across all pools.
        
        Returns:
            Dictionary mapping token mint to deposit amount
        
        Raises:
            Exception: If deposit query fails
        """
        try:
            logger.info("Querying user deposits in MarginFi")
            
            # Derive user account
            user_account = self._derive_user_account()
            
            # Query account data
            account_info = self.rpc_client.get_account_info(str(user_account))
            
            if not account_info:
                logger.info("No MarginFi account found, no deposits")
                return {}
            
            # Parse account data to get deposits
            # This is simplified - real implementation would parse the account data
            deposits = {}
            
            logger.info(f"User deposits: {deposits}")
            return deposits
        
        except Exception as e:
            error_msg = f"Failed to get user deposits: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _derive_user_account(self) -> Pubkey:
        """
        Derive the user account PDA for MarginFi.
        
        Returns:
            User account public key
        """
        # Simplified PDA derivation
        # Real implementation would use proper seeds and bump
        # For now, return a placeholder based on wallet
        
        # In production: Pubkey.find_program_address([b"marginfi_account", bytes(self.wallet_pubkey)], self.program_id)
        return self.wallet_pubkey  # Placeholder
    
    def _create_initialize_instruction(self, user_account: Pubkey) -> Instruction:
        """
        Create an initialize user account instruction.
        
        Args:
            user_account: User account public key
        
        Returns:
            Initialize instruction
        """
        # Simplified instruction structure
        accounts = [
            AccountMeta(pubkey=self.wallet_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=user_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.program_id, is_signer=False, is_writable=False),
        ]
        
        # Simplified instruction data
        data = b"\x00"  # Initialize discriminator
        
        return Instruction(
            program_id=self.program_id,
            accounts=accounts,
            data=data
        )
    
    def _create_deposit_instruction(
        self,
        user_account: Pubkey,
        pool: Pubkey,
        amount: int
    ) -> Instruction:
        """
        Create a deposit instruction.
        
        Args:
            user_account: User account public key
            pool: Pool public key
            amount: Amount to deposit in token units
        
        Returns:
            Deposit instruction
        """
        # Simplified instruction structure
        accounts = [
            AccountMeta(pubkey=self.wallet_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=user_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=pool, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.program_id, is_signer=False, is_writable=False),
        ]
        
        # Simplified instruction data
        data = b"\x01" + amount.to_bytes(8, 'little')  # Deposit discriminator + amount
        
        return Instruction(
            program_id=self.program_id,
            accounts=accounts,
            data=data
        )
    
    def _create_withdraw_instruction(
        self,
        user_account: Pubkey,
        pool: Pubkey,
        amount: int
    ) -> Instruction:
        """
        Create a withdraw instruction.
        
        Args:
            user_account: User account public key
            pool: Pool public key
            amount: Amount to withdraw in token units
        
        Returns:
            Withdraw instruction
        """
        # Simplified instruction structure
        accounts = [
            AccountMeta(pubkey=self.wallet_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=user_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=pool, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.program_id, is_signer=False, is_writable=False),
        ]
        
        # Simplified instruction data
        data = b"\x02" + amount.to_bytes(8, 'little')  # Withdraw discriminator + amount
        
        return Instruction(
            program_id=self.program_id,
            accounts=accounts,
            data=data
        )
